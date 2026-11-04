import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import routers.whatsapp_auth as whatsapp_auth
from database import Base, get_db
from models import AdminPermission, BackendAuthSession, User, WhatsAppOTPChallenge
from routers.firebase import router as firebase_router


@pytest.fixture
def auth_client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    def get_test_db():
        db = factory()
        try: yield db
        finally: db.close()
    app = FastAPI()
    app.include_router(whatsapp_auth.router)
    app.include_router(whatsapp_auth.admin_router)
    app.include_router(firebase_router)
    app.dependency_overrides[get_db] = get_test_db
    monkeypatch.setenv("WHATSAPP_OTP_HASH_SECRET", "h" * 48)
    monkeypatch.setenv("WHATSAPP_SESSION_TTL_SECONDS", "86400")
    monkeypatch.setattr(whatsapp_auth, "_gateway", lambda *args, **kwargs: {"accepted": True, "messageId": "wamid.test"})
    with TestClient(app) as client: yield client, factory
    Base.metadata.drop_all(bind=engine); engine.dispose()


def test_challenge_hash_and_session_issue_and_revoke(auth_client):
    client, factory = auth_client
    sent = client.post("/api/v1/auth/whatsapp/send-otp", json={"phone": "+919876543210", "role": "WORKER"})
    assert sent.status_code == 200
    payload = sent.json()
    assert payload["deliveryStatus"] == "accepted" and "otp" not in payload
    with factory() as db:
        challenge = db.query(WhatsAppOTPChallenge).filter_by(id=payload["requestId"]).one()
        assert len(challenge.otp_digest) == 64 and "123456" != challenge.otp_digest
        challenge.otp_digest = whatsapp_auth._otp_digest(payload["requestId"], "+919876543210", "worker", "123456")
        db.commit()
    verified = client.post("/api/v1/auth/whatsapp/verify-otp", json={"phone": "+919876543210", "requestId": payload["requestId"], "otp": "123456", "role": "WORKER"})
    assert verified.status_code == 200, verified.text
    result = verified.json()
    assert result["user"]["role"] == "worker" and result["accessToken"].startswith("errno_")
    profile = client.get("/api/v1/users/me", headers={"Authorization": "Bearer " + result["accessToken"]})
    assert profile.status_code == 200 and profile.json()["id"] == result["user"]["id"]
    with factory() as db:
        assert db.query(User).filter_by(phone_number="+919876543210").count() == 1
        assert db.query(BackendAuthSession).count() == 1
    logout = client.post("/api/v1/auth/whatsapp/logout", headers={"Authorization": "Bearer " + result["accessToken"]})
    assert logout.status_code == 200
    with factory() as db:
        session = db.query(BackendAuthSession).one()
        assert session.revoked_at is not None


def test_wrong_role_expired_and_single_use_challenges_rejected(auth_client):
    client, factory = auth_client
    sent = client.post("/api/v1/auth/whatsapp/send-otp", json={"phone": "+919876543210", "role": "WORKER"}).json()
    with factory() as db:
        challenge = db.query(WhatsAppOTPChallenge).one()
        challenge.otp_digest = whatsapp_auth._otp_digest(sent["requestId"], challenge.phone_number, challenge.role, "123456")
        db.commit()
    wrong_role = client.post("/api/v1/auth/whatsapp/verify-otp", json={"phone": "+919876543210", "requestId": sent["requestId"], "otp": "123456", "role": "SHOPKEEPER"})
    assert wrong_role.status_code == 400
    verified = client.post("/api/v1/auth/whatsapp/verify-otp", json={"phone": "+919876543210", "requestId": sent["requestId"], "otp": "123456", "role": "WORKER"})
    assert verified.status_code == 200
    reused = client.post("/api/v1/auth/whatsapp/verify-otp", json={"phone": "+919876543210", "requestId": sent["requestId"], "otp": "123456", "role": "WORKER"})
    assert reused.status_code == 400


def test_gateway_failure_fails_closed(auth_client, monkeypatch):
    client, _ = auth_client
    def unavailable(*_args, **_kwargs):
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail={"code": "WHATSAPP_GATEWAY_UNAVAILABLE"})
    monkeypatch.setattr(whatsapp_auth, "_gateway", unavailable)
    response = client.post("/api/v1/auth/whatsapp/send-otp", json={"phone": "+919876543210", "role": "WORKER"})
    assert response.status_code == 503


def test_expired_challenge_rejected(auth_client):
    client, factory = auth_client
    sent = client.post("/api/v1/auth/whatsapp/send-otp", json={"phone": "+919876543210", "role": "WORKER"}).json()
    with factory() as db:
        challenge = db.query(WhatsAppOTPChallenge).one()
        challenge.otp_digest = whatsapp_auth._otp_digest(sent["requestId"], challenge.phone_number, challenge.role, "123456")
        challenge.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    response = client.post("/api/v1/auth/whatsapp/verify-otp", json={"phone": "+919876543210", "requestId": sent["requestId"], "otp": "123456", "role": "WORKER"})
    assert response.status_code == 400


def test_attempt_limit_and_resend_cooldown(auth_client):
    client, factory = auth_client
    sent = client.post("/api/v1/auth/whatsapp/send-otp", json={"phone": "+919876543210", "role": "WORKER"}).json()
    with factory() as db:
        challenge = db.query(WhatsAppOTPChallenge).one()
        challenge.otp_digest = whatsapp_auth._otp_digest(sent["requestId"], challenge.phone_number, challenge.role, "123456")
        db.commit()
    cooldown = client.post("/api/v1/auth/whatsapp/resend-otp", json={"phone": "+919876543210", "role": "WORKER", "requestId": sent["requestId"]})
    assert cooldown.status_code == 429
    for _ in range(5):
        rejected = client.post("/api/v1/auth/whatsapp/verify-otp", json={"phone": "+919876543210", "requestId": sent["requestId"], "otp": "999999", "role": "WORKER"})
        assert rejected.status_code == 400
    limited = client.post("/api/v1/auth/whatsapp/verify-otp", json={"phone": "+919876543210", "requestId": sent["requestId"], "otp": "999999", "role": "WORKER"})
    assert limited.status_code == 429


def test_missing_otp_hash_secret_fails_closed(auth_client, monkeypatch):
    client, _ = auth_client
    monkeypatch.delenv("WHATSAPP_OTP_HASH_SECRET")
    response = client.post("/api/v1/auth/whatsapp/send-otp", json={"phone": "+919876543210", "role": "WORKER"})
    assert response.status_code == 503


def test_gateway_admin_rbac_requires_scoped_firebase_admin(auth_client, monkeypatch):
    client, factory = auth_client
    import firebase_auth
    monkeypatch.setattr(firebase_auth, "verify_firebase_token", lambda _token: {"uid": "admin-firebase-uid"})
    monkeypatch.setattr(whatsapp_auth, "_gateway", lambda *_args, **_kwargs: {"status": "CONNECTED"})
    assert client.get("/api/v1/admin/whatsapp/status").status_code == 401
    with factory() as db:
        db.add(AdminPermission(firebase_uid="admin-firebase-uid", permissions=[], active=True,
                               granted_by_uid="operator", reason="test"))
        db.commit()
    headers = {"Authorization": "Bearer valid-firebase-token"}
    assert client.get("/api/v1/admin/whatsapp/status", headers=headers).status_code == 403
    with factory() as db:
        admin = db.query(AdminPermission).one()
        admin.permissions = ["whatsapp.read"]
        db.commit()
    assert client.get("/api/v1/admin/whatsapp/status", headers=headers).status_code == 200
    assert client.get("/api/v1/admin/whatsapp/qr", headers=headers).status_code == 403
