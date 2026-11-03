import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from cryptography.fernet import Fernet

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import firebase_auth
import routers.kyc as kyc
import kyc_storage
import kyc_service
from database import Base, get_db
from models import AdminPermission, User, KYCVerificationProfile, KYCManualReview


@pytest.fixture
def kyc_client(monkeypatch, tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with factory() as db:
        db.add_all([User(id="worker-1", firebase_uid="worker-uid", full_name="Worker", role="worker"),
            AdminPermission(firebase_uid="reviewer", active=True, permissions=["kyc.read", "kyc.review", "kyc.manage", "kyc.audit"], granted_by_uid="root", reason="test")])
        db.commit()
    def db_dep():
        session = factory()
        try: yield session
        finally: session.close()
    claims = {"worker-token": {"uid": "worker-uid"}, "admin-token": {"uid": "reviewer"}}
    monkeypatch.setattr(firebase_auth, "verify_firebase_token", lambda token: claims[token] if token in claims else (_ for _ in ()).throw(HTTPException(401)))
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DIGILOCKER_ENABLED", "true")
    monkeypatch.setenv("DIGILOCKER_PROVIDER_MODE", "mock")
    monkeypatch.setenv("DIGILOCKER_STATE_SECRET", "test-state-secret-" + "x" * 40)
    monkeypatch.setenv("KYC_ALLOWED_DOCUMENT_TYPES", "PAN")
    monkeypatch.setenv("KYC_CONSENT_VERSION", "v1")
    monkeypatch.setenv("KYC_MANUAL_REVIEW_ENABLED", "true")
    monkeypatch.setenv("KYC_DOCUMENT_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("KYC_MANUAL_STORAGE_PATH", str(tmp_path / "private"))
    monkeypatch.setenv("KYC_ANTIVIRUS_MODE", "test_clean")
    app = FastAPI()
    app.include_router(kyc.router); app.include_router(kyc.admin_router)
    app.dependency_overrides[get_db] = db_dep
    with TestClient(app) as client: yield client, factory
    Base.metadata.drop_all(bind=engine); engine.dispose()


def test_digillocker_session_requires_consent_and_approved_type(kyc_client):
    client, _ = kyc_client
    headers = {"Authorization": "Bearer worker-token"}
    assert client.post("/api/v1/worker/verification-sessions", headers=headers,
        json={"requestedDocumentTypes":["PAN"],"consentVersion":"v1","consentGiven":False}).status_code == 422
    assert client.post("/api/v1/worker/verification-sessions", headers=headers,
        json={"requestedDocumentTypes":["AADHAAR"],"consentVersion":"v1","consentGiven":True}).status_code == 422


def test_mock_provider_is_one_time_and_marked_as_test_only(kyc_client):
    client, factory = kyc_client
    headers = {"Authorization": "Bearer worker-token"}
    response = client.post("/api/v1/worker/verification-sessions", headers=headers,
        json={"requestedDocumentTypes":["PAN"],"consentVersion":"v1","consentGiven":True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["authorizationUrl"] is None and payload["testOnlyMockToken"]
    done = client.post(f"/api/v1/worker/verification-sessions/{payload['sessionId']}/mock-complete", headers=headers,
        json={"testOnlyMockToken":payload["testOnlyMockToken"]})
    assert done.status_code == 200 and done.json()["verificationMethod"] == "MOCK_PROVIDER_TEST"
    assert client.post(f"/api/v1/worker/verification-sessions/{payload['sessionId']}/mock-complete", headers=headers,
        json={"testOnlyMockToken":payload["testOnlyMockToken"]}).status_code == 409
    with factory() as db:
        profile = db.query(KYCVerificationProfile).one()
        assert profile.status == "VERIFIED" and profile.verification_method == "MOCK_PROVIDER_TEST"


def test_provider_callback_fails_closed_even_with_successful_redirect(kyc_client):
    client, _ = kyc_client
    response = client.get("/api/v1/verification/digilocker/callback")
    assert response.status_code == 503 and response.json()["detail"]["code"] == "PROVIDER_SPEC_REQUIRED"


def test_manual_document_is_private_and_review_records_method(kyc_client):
    client, factory = kyc_client
    headers = {"Authorization": "Bearer worker-token"}
    response = client.post("/api/v1/worker/verification/manual-reviews", headers=headers,
        data={"document_type":"PAN","consent_version":"v1","consent_given":"true"},
        files={"file":("proof.pdf",b"%PDF-1.4\nbody", "application/pdf")})
    assert response.status_code == 201
    review_id = response.json()["manualReviewId"]
    with factory() as db: profile_id = db.query(KYCVerificationProfile).one().id
    result = client.post(f"/api/v1/admin/kyc/verifications/{profile_id}/review", headers={"Authorization":"Bearer admin-token"},
        json={"action":"APPROVE","reasonCode":"DOC_MATCHED","note":"Reviewer verified the submitted document"})
    assert result.status_code == 200 and result.json()["verificationMethod"] == "MANUAL_DOCUMENT_REVIEW"
    with factory() as db:
        assert db.query(KYCManualReview).filter_by(id=review_id).one().status == "APPROVED"


def test_admin_permission_is_enforced(kyc_client):
    client, _ = kyc_client
    assert client.get("/api/v1/admin/kyc/overview", headers={"Authorization":"Bearer worker-token"}).status_code == 403
    assert client.get("/api/v1/admin/kyc/overview").status_code == 401


def test_production_rejects_mock_provider(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DIGILOCKER_ENABLED", "true")
    monkeypatch.setenv("DIGILOCKER_PROVIDER_MODE", "mock")
    with pytest.raises(HTTPException) as error:
        kyc_service.ensure_provider_enabled()
    assert error.value.status_code == 503
    assert error.value.detail["code"] == "MOCK_PROVIDER_FORBIDDEN"
