import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import firebase_auth
from database import Base, get_db
from routers.firebase import router
from routers.jobs import router as jobs_router
from routers.shops import router as shops_router


@pytest.fixture
def client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def get_test_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app = FastAPI()
    app.include_router(router)
    app.include_router(jobs_router)
    app.include_router(shops_router)
    app.dependency_overrides[get_db] = get_test_db
    def verify(token):
        if token == "invalid-token":
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        return {"uid": "verified-user-uid", "name": "Google User", "email": "google@example.test"}

    monkeypatch.setattr(firebase_auth, "verify_firebase_token", verify)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_missing_token_is_rejected(client):
    response = client.post("/api/v1/auth/firebase")
    assert response.status_code == 401


def test_invalid_token_is_rejected(client):
    response = client.post("/api/v1/auth/firebase", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401


def test_admin_verifier_enforces_firebase_project_claims(monkeypatch):
    expected = {
        "uid": "firebase-uid",
        "aud": "errno-pvt-ltd",
        "iss": "https://securetoken.google.com/errno-pvt-ltd",
    }
    monkeypatch.setattr(firebase_auth, "firebase_app", lambda: object())
    monkeypatch.setattr(firebase_auth.auth, "verify_id_token", lambda token, app, check_revoked: expected)
    assert firebase_auth.verify_firebase_token("opaque-test-token")["uid"] == "firebase-uid"

    monkeypatch.setattr(firebase_auth.auth, "verify_id_token", lambda token, app, check_revoked: {
        **expected,
        "aud": "different-project",
    })
    with pytest.raises(Exception) as error:
        firebase_auth.verify_firebase_token("opaque-test-token")
    assert getattr(error.value, "status_code", None) == 401


def test_admin_verifier_rejects_expired_firebase_tokens(monkeypatch):
    monkeypatch.setattr(firebase_auth, "firebase_app", lambda: object())
    def expired(*_args, **_kwargs):
        raise firebase_auth.auth.ExpiredIdTokenError("expired", None)
    monkeypatch.setattr(firebase_auth.auth, "verify_id_token", expired)
    with pytest.raises(Exception) as error:
        firebase_auth.verify_firebase_token("expired-token")
    assert getattr(error.value, "status_code", None) == 401


def test_login_creates_user_once_and_profile_is_authorized(client):
    first = client.post("/api/v1/auth/firebase", headers={"Authorization": "Bearer signed-token"})
    second = client.post("/api/v1/auth/firebase", headers={"Authorization": "Bearer signed-token"})
    assert first.status_code == second.status_code == 200
    user = first.json()["user"]
    assert user["firebase_uid"] == "verified-user-uid"
    assert user["role"] is None
    assert user["onboarding_completed"] is False
    assert second.json()["user"]["id"] == user["id"]

    me = client.get("/api/v1/users/me", headers={"Authorization": "Bearer signed-token"})
    assert me.status_code == 200
    assert me.json()["id"] == user["id"]


def test_profile_update_allows_one_time_role_selection(client):
    headers = {"Authorization": "Bearer signed-token"}
    client.post("/api/v1/auth/firebase", headers=headers)
    updated = client.patch("/api/v1/users/me", headers=headers, json={"name": "Updated", "role": "worker"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated"
    assert updated.json()["onboarding_completed"] is True
    conflict = client.patch("/api/v1/users/me", headers=headers, json={"role": "shop_owner"})
    assert conflict.status_code == 409


def test_logout_is_compatible_with_stateless_firebase_tokens(client):
    response = client.post("/api/v1/auth/logout", headers={"Authorization": "Bearer signed-token"})
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_worker_cannot_create_shopkeeper_job(client):
    headers = {"Authorization": "Bearer signed-token"}
    client.post("/api/v1/auth/firebase", headers=headers)
    client.patch("/api/v1/users/me", headers=headers, json={"role": "worker"})
    response = client.post("/jobs", headers=headers, json={"title": "Restricted job"})
    assert response.status_code == 403


def test_legacy_jobs_are_not_authorized_by_phone_or_mock_identity(client):
    response = client.post("/jobs", params={"owner_phone": "9971439107"}, json={"title": "Restricted job"})
    assert response.status_code == 401
