import sys
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import firebase_auth
from database import Base, get_db
from models import AdminPermission, Application, Job, Shop, User
from routers import admin, auth, firebase, jobs, shops


@pytest.fixture
def mobile_client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def get_test_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    identities = {
        "owner": {"uid": "owner-uid", "name": "Owner", "email": "owner@test.invalid"},
        "worker": {"uid": "worker-uid", "name": "Worker", "email": "worker@test.invalid"},
        "outsider": {"uid": "outsider-uid", "name": "Outsider", "email": "outsider@test.invalid"},
        "admin": {"uid": "admin-uid", "name": "Admin", "email": "admin@test.invalid"},
    }
    def verify(token):
        if token not in identities:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        return identities[token]
    monkeypatch.setattr(firebase_auth, "verify_firebase_token", verify)

    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(firebase.router)
    app.include_router(shops.router)
    app.include_router(jobs.router)
    app.include_router(admin.router)
    app.dependency_overrides[get_db] = get_test_db
    with TestClient(app) as client:
        yield client, factory
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def onboard(client, token, role):
    headers = {"Authorization": f"Bearer {token}"}
    profile = client.post("/api/v1/auth/firebase", headers=headers)
    assert profile.status_code == 200
    updated = client.patch("/api/v1/users/me", headers=headers, json={"role": role})
    assert updated.status_code == 200
    return headers, updated.json()["id"]


def test_mobile_shop_job_application_persists_and_enforces_owner_scope(mobile_client):
    client, factory = mobile_client
    owner_headers, owner_id = onboard(client, "owner", "shop_owner")
    worker_headers, worker_id = onboard(client, "worker", "worker")
    outsider_headers, _ = onboard(client, "outsider", "worker")

    # A read is side-effect free; shop creation is explicit and bound to verified user ID.
    assert client.get("/shops/me", headers=owner_headers).json() is None
    shop_response = client.put("/shops/me", headers=owner_headers, json={
        "shop_name": "Corner Shop", "address": "Market Road", "category": "Grocery"
    })
    assert shop_response.status_code == 200
    job_response = client.post("/jobs", headers=owner_headers, json={
        "title": "Delivery Partner", "category": "Delivery Partner", "description": "Deliver orders",
        "pay_amount": 249, "duration_type": "2 hours", "scheduled_date": "Tomorrow",
        "location": "Market Road", "is_delivery": True,
    })
    assert job_response.status_code == 200
    job_id = job_response.json()["id"]
    assert client.get("/jobs/mine", headers=owner_headers).json()[0]["id"] == job_id
    assert client.get("/jobs/mine", headers=worker_headers).status_code == 403
    assert client.get("/jobs/applications/me", headers=owner_headers).status_code == 403

    application = client.post(f"/jobs/{job_id}/apply", headers=worker_headers)
    assert application.status_code == 200
    assert application.json()["worker_id"] == worker_id
    history = client.get("/jobs/applications/me", headers=worker_headers)
    assert history.json()["items"][0]["id"] == application.json()["id"]
    assert history.json()["items"][0]["job"]["title"] == "Delivery Partner"
    assert history.json()["items"][0]["job"]["shop"]["shop_name"] == "Corner Shop"
    assert history.json()["items"][0]["created_at"]
    owner_app = client.get("/jobs/applications/owner", headers=owner_headers)
    assert owner_app.status_code == 200
    assert owner_app.json()[0]["worker_name"] == "Worker"
    assert "email" not in owner_app.json()[0] and "phone_number" not in owner_app.json()[0]
    assert client.get(f"/jobs/{job_id}/applications", headers=owner_headers).status_code == 200
    assert client.get(f"/jobs/{job_id}/applications", headers=outsider_headers).status_code == 403

    decision = client.patch(f"/jobs/{job_id}/applications/{application.json()['id']}", headers=owner_headers,
                            json={"decision": "accepted"})
    assert decision.status_code == 200 and decision.json()["status"] == "accepted"
    assert client.get("/jobs/worker/mine", headers=worker_headers).json()[0]["id"] == job_id
    assert client.get("/jobs", params={"status_filter": "assigned"}).json()[0]["assigned_worker_id"] == worker_id
    with factory() as db:
        assert db.query(User).count() == 3
        assert db.query(Shop).count() == 1
        assert db.query(Job).count() == 1
        assert db.query(Application).count() == 1


def test_job_lifecycle_authorization_timestamps_and_idempotency(mobile_client):
    client, factory = mobile_client
    owner_headers, _ = onboard(client, "owner", "shop_owner")
    worker_headers, worker_id = onboard(client, "worker", "worker")
    outsider_headers, _ = onboard(client, "outsider", "worker")
    client.put("/shops/me", headers=owner_headers, json={"shop_name": "Lifecycle Shop"})
    job = client.post("/jobs", headers=owner_headers, json={"title": "Lifecycle Shift"}).json()
    application = client.post(f"/jobs/{job['id']}/apply", headers=worker_headers).json()
    accepted = client.patch(f"/jobs/{job['id']}/applications/{application['id']}",
                            headers=owner_headers, json={"decision": "accepted"})
    assert accepted.status_code == 200

    assert client.post(f"/jobs/{job['id']}/start", headers=outsider_headers).status_code == 403
    started = client.post(f"/jobs/{job['id']}/start", headers=worker_headers)
    assert started.status_code == 200
    assert started.json()["status"] == "in_progress"
    assert started.json()["started_at"]
    assert client.post(f"/jobs/{job['id']}/start", headers=worker_headers).status_code == 409
    assert client.post(f"/jobs/{job['id']}/complete", headers=worker_headers).status_code == 403
    assert client.patch(f"/jobs/{job['id']}/status?new_status=cancelled", headers=owner_headers).status_code == 409

    completed = client.post(f"/jobs/{job['id']}/complete", headers=owner_headers)
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["completed_at"]
    assert client.post(f"/jobs/{job['id']}/complete", headers=owner_headers).status_code == 409
    with factory() as db:
        db.add(AdminPermission(firebase_uid="admin-uid", email="admin@test.invalid", permissions=["jobs.read"],
                              granted_by_uid="test-operator", reason="isolated test"))
        db.commit()
        persisted = db.query(Job).filter(Job.id == job["id"]).one()
        assert persisted.assigned_worker_id == worker_id
        assert persisted.started_at is not None and persisted.completed_at is not None
    admin_jobs = client.get("/api/v1/admin/jobs?status_filter=completed", headers={"Authorization": "Bearer admin"})
    assert admin_jobs.status_code == 200
    assert admin_jobs.json()["items"][0]["id"] == job["id"]
    assert admin_jobs.json()["items"][0]["status"] == "completed"
    assert admin_jobs.json()["items"][0]["started_at"] and admin_jobs.json()["items"][0]["completed_at"]


def test_worker_application_history_pagination_and_pending_cancellation(mobile_client):
    client, _ = mobile_client
    owner_headers, _ = onboard(client, "owner", "shop_owner")
    worker_headers, _ = onboard(client, "worker", "worker")
    client.put("/shops/me", headers=owner_headers, json={"shop_name": "History Shop"})
    ids = []
    for title in ("History One", "History Two", "History Three"):
        job = client.post("/jobs", headers=owner_headers, json={"title": title}).json()
        ids.append(job["id"])
        assert client.post(f"/jobs/{job['id']}/apply", headers=worker_headers).status_code == 200

    first = client.get("/jobs/applications/me?limit=2&offset=0", headers=worker_headers).json()
    second = client.get("/jobs/applications/me?limit=2&offset=2", headers=worker_headers).json()
    assert first["total"] == 3 and first["has_more"] and len(first["items"]) == 2
    assert not second["has_more"] and len(second["items"]) == 1
    application = second["items"][0]
    cancelled = client.delete(f"/jobs/{application['job_id']}/applications/me", headers=worker_headers)
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    assert client.delete(f"/jobs/{application['job_id']}/applications/me", headers=worker_headers).status_code == 409
    latest = client.get("/jobs/applications/me?limit=5", headers=worker_headers).json()
    assert {item["status"] for item in latest["items"]} == {"pending", "cancelled"}


def test_mobile_role_and_job_input_validation(mobile_client):
    client, _ = mobile_client
    worker_headers, _ = onboard(client, "worker", "worker")
    assert client.put("/shops/me", headers=worker_headers, json={"shop_name": "Not allowed"}).status_code == 403
    assert client.post("/jobs", headers=worker_headers, json={"title": "Bad", "pay_amount": -1}).status_code == 422
    assert client.post("/jobs", headers={"Authorization": "Bearer outsider"}, json={"title": "No token"}).status_code == 404


def test_legacy_otp_never_accepts_a_fixed_code(mobile_client):
    client, _ = mobile_client
    assert client.post("/auth/send-otp", json={"phone_number": "9971439107"}).status_code == 503
    assert client.post("/auth/verify-otp", json={"phone_number": "9971439107", "otp_code": "123456"}).status_code == 503
