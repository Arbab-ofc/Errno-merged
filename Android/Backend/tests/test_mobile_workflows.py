import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import firebase_auth
from database import Base, get_db
from models import AdminPermission, Application, Job, Notification, PresenceSession, Shop, User
from routers import admin, auth, firebase, jobs, shops
from pricing_test_utils import insert_job_quote
from services import prebooking_dispatcher


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
    app.state.session_factory = factory
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
    quote_id, service_start_at = insert_job_quote(factory, owner_id, duration_hours=2)
    job_body = {
        "title": "Delivery Partner", "category": "Delivery Partner", "description": "Deliver orders",
        "pay_amount": 249, "duration_type": "2 hours", "scheduled_date": "Tomorrow",
        "location": "Market Road", "is_delivery": True,
        "quote_id": quote_id, "service_start_at": service_start_at,
    }
    assert client.post("/jobs", headers=owner_headers, json={**job_body, "latitude": 28.6139}).status_code == 422
    job_response = client.post("/jobs", headers=owner_headers, json={**job_body, "latitude": 28.6139, "longitude": 77.2090})
    assert job_response.status_code == 200
    job_id = job_response.json()["id"]
    assert job_response.json()["latitude"] == 28.6139 and job_response.json()["longitude"] == 77.209
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
    owner_headers, owner_id = onboard(client, "owner", "shop_owner")
    worker_headers, worker_id = onboard(client, "worker", "worker")
    outsider_headers, _ = onboard(client, "outsider", "worker")
    client.put("/shops/me", headers=owner_headers, json={"shop_name": "Lifecycle Shop"})
    quote_id, service_start_at = insert_job_quote(factory, owner_id)
    job = client.post("/jobs", headers=owner_headers, json={
        "title": "Lifecycle Shift", "quote_id": quote_id, "service_start_at": service_start_at,
    }).json()
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


def test_prebooking_is_hidden_until_exact_four_hour_dispatch(mobile_client, monkeypatch):
    client, factory = mobile_client
    owner_headers, owner_id = onboard(client, "owner", "shop_owner")
    worker_headers, worker_id = onboard(client, "worker", "worker")
    start = datetime.now(timezone.utc) + timedelta(hours=6)
    quote_id, quote_start = insert_job_quote(factory, owner_id, duration_hours=2, service_start_at=start, area_id="market road")
    created = client.post("/jobs", headers=owner_headers, json={
        "title": "Scheduled helper", "category": "General", "duration_type": "2 hours", "location": "Market Road",
        "booking_type": "PRE_BOOKING", "quote_id": quote_id, "service_start_at": quote_start,
    })
    assert created.status_code == 200, created.text
    row = created.json()
    assert row["prebooking_dispatch_status"] == "SCHEDULED"
    assert datetime.fromisoformat(row["dispatch_at"]) == start - timedelta(hours=4)
    assert client.get("/jobs").json() == []
    assert client.get(f"/jobs/{row['id']}").status_code == 404
    assert client.post(f"/jobs/{row['id']}/apply", headers=worker_headers).status_code == 404
    with factory() as db:
        db.add(PresenceSession(user_id=worker_id, session_identifier="prebook-test", expires_at=start + timedelta(hours=1),
                               is_foreground=True, availability_status="available"))
        db.commit()
        assert db.query(Notification).filter_by(recipient_user_id=worker_id).count() == 0

    monkeypatch.setattr(prebooking_dispatcher, "SessionLocal", factory)
    dispatch_time = start - timedelta(hours=4)
    assert not prebooking_dispatcher.dispatch_due_once(now=dispatch_time - timedelta(seconds=1), owner="worker-a")
    assert prebooking_dispatcher.dispatch_due_once(now=dispatch_time, owner="worker-a")
    assert client.get("/jobs").json()[0]["id"] == row["id"]
    application = client.post(f"/jobs/{row['id']}/apply", headers=worker_headers)
    assert application.status_code == 200
    decision = client.patch(f"/jobs/{row['id']}/applications/{application.json()['id']}", headers=owner_headers,
                            json={"decision": "accepted"})
    assert decision.status_code == 200 and decision.json()["status"] == "accepted"
    with factory() as db:
        persisted = db.query(Job).filter_by(id=row["id"]).one()
        assert persisted.prebooking_dispatch_status == "DISPATCHED"
        assert persisted.prebooking_dispatch_worker_count == 1
        invitations = db.query(Notification).filter_by(recipient_user_id=worker_id, event_type="prebooking_worker_request").all()
        assert len(invitations) == 1
        # A second dispatcher pass and idempotent generation cannot duplicate invitation notices.
        assert not prebooking_dispatcher.dispatch_due_once(now=dispatch_time + timedelta(seconds=1), owner="worker-b")
        assert db.query(Notification).filter_by(recipient_user_id=worker_id, event_type="prebooking_worker_request").count() == 1


def test_prebooking_cancel_and_reschedule_invalidate_old_dispatch_generation(mobile_client):
    client, factory = mobile_client
    owner_headers, owner_id = onboard(client, "owner", "shop_owner")
    onboard(client, "worker", "worker")
    first_start = datetime.now(timezone.utc) + timedelta(hours=8)
    quote_id, quote_start = insert_job_quote(factory, owner_id, duration_hours=2, service_start_at=first_start, area_id="market road")
    created = client.post("/jobs", headers=owner_headers, json={
        "title": "Reschedulable helper", "category": "General", "duration_type": "2 hours", "location": "Market Road",
        "booking_type": "PRE_BOOKING", "quote_id": quote_id, "service_start_at": quote_start,
    })
    assert created.status_code == 200, created.text
    job = created.json()
    new_start = first_start + timedelta(days=1)
    new_quote, new_quote_start = insert_job_quote(factory, owner_id, duration_hours=2, service_start_at=new_start, area_id="market road")
    updated = client.patch(f"/jobs/{job['id']}/reschedule", headers=owner_headers,
                           json={"quote_id": new_quote, "service_start_at": new_quote_start})
    assert updated.status_code == 200, updated.text
    assert updated.json()["prebooking_schedule_version"] == job["prebooking_schedule_version"] + 1
    assert datetime.fromisoformat(updated.json()["dispatch_at"]) == new_start - timedelta(hours=4)
    cancelled = client.patch(f"/jobs/{job['id']}/status?new_status=cancelled", headers=owner_headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["prebooking_dispatch_status"] == "CANCELLED"
    assert client.patch(f"/jobs/{job['id']}/reschedule", headers=owner_headers,
                        json={"quote_id": quote_id, "service_start_at": quote_start}).status_code == 409


def test_prebooking_rejects_past_start_and_late_creation_dispatches_now(mobile_client, monkeypatch):
    client, factory = mobile_client
    owner_headers, owner_id = onboard(client, "owner", "shop_owner")
    worker_headers, worker_id = onboard(client, "worker", "worker")
    fixed_now = datetime.now(timezone.utc)
    monkeypatch.setattr(jobs, "utc_now", lambda: fixed_now)
    past = fixed_now - timedelta(minutes=1)
    past_quote, past_start = insert_job_quote(factory, owner_id, duration_hours=2, service_start_at=past, area_id="market road")
    response = client.post("/jobs", headers=owner_headers, json={"title": "Past", "category": "General", "duration_type": "2 hours", "location": "Market Road", "booking_type": "PRE_BOOKING", "quote_id": past_quote, "service_start_at": past_start})
    assert response.status_code == 422

    with factory() as db:
        db.add(PresenceSession(user_id=worker_id, session_identifier="late-prebook", expires_at=fixed_now + timedelta(days=2),
                               is_foreground=True, availability_status="available"))
        db.commit()
    late_start = fixed_now + timedelta(hours=2)
    late_quote, late_service_start = insert_job_quote(factory, owner_id, duration_hours=2, service_start_at=late_start, area_id="market road")
    created = client.post("/jobs", headers=owner_headers, json={"title": "Late", "category": "General", "duration_type": "2 hours", "location": "Market Road", "booking_type": "PRE_BOOKING", "quote_id": late_quote, "service_start_at": late_service_start})
    assert created.status_code == 200, created.text
    assert created.json()["prebooking_dispatch_status"] == "DISPATCHED"
    with factory() as db:
        assert db.query(Notification).filter_by(recipient_user_id=worker_id, event_type="prebooking_worker_request").count() == 1


def test_prebooking_no_eligible_workers_is_not_reported_as_dispatched(mobile_client, monkeypatch):
    client, factory = mobile_client
    owner_headers, owner_id = onboard(client, "owner", "shop_owner")
    start = datetime.now(timezone.utc) + timedelta(hours=6)
    quote_id, quote_start = insert_job_quote(factory, owner_id, duration_hours=2, service_start_at=start, area_id="market road")
    created = client.post("/jobs", headers=owner_headers, json={
        "title": "No match booking", "category": "General", "duration_type": "2 hours", "location": "Market Road",
        "booking_type": "PRE_BOOKING", "quote_id": quote_id, "service_start_at": quote_start,
    })
    assert created.status_code == 200, created.text
    monkeypatch.setattr(prebooking_dispatcher, "SessionLocal", factory)
    assert prebooking_dispatcher.dispatch_due_once(now=start - timedelta(hours=4), owner="no-worker")
    with factory() as db:
        saved = db.query(Job).filter_by(id=created.json()["id"]).one()
        assert saved.prebooking_dispatch_status == "NO_ELIGIBLE_WORKERS"
        assert saved.prebooking_dispatch_worker_count == 0
        assert db.query(Notification).filter_by(event_type="prebooking_worker_request").count() == 0


def test_prebooking_india_midnight_boundary_is_stored_as_utc_instant(mobile_client):
    client, factory = mobile_client
    owner_headers, owner_id = onboard(client, "owner", "shop_owner")
    start = datetime(2030, 1, 1, 0, 30, tzinfo=ZoneInfo("Asia/Kolkata"))
    quote_id, _ = insert_job_quote(factory, owner_id, duration_hours=2, service_start_at=start.astimezone(timezone.utc), area_id="market road")
    quote_start = start.isoformat()
    created = client.post("/jobs", headers=owner_headers, json={
        "title": "Midnight boundary", "category": "General", "duration_type": "2 hours", "location": "Market Road",
        "booking_type": "PRE_BOOKING", "quote_id": quote_id, "service_start_at": quote_start,
    })
    assert created.status_code == 200, created.text
    assert datetime.fromisoformat(created.json()["scheduled_at"]) == start.astimezone(timezone.utc)
    assert datetime.fromisoformat(created.json()["dispatch_at"]) == start.astimezone(timezone.utc) - timedelta(hours=4)


def test_worker_application_history_pagination_and_pending_cancellation(mobile_client):
    client, factory = mobile_client
    owner_headers, owner_id = onboard(client, "owner", "shop_owner")
    worker_headers, _ = onboard(client, "worker", "worker")
    client.put("/shops/me", headers=owner_headers, json={"shop_name": "History Shop"})
    ids = []
    for title in ("History One", "History Two", "History Three"):
        quote_id, service_start_at = insert_job_quote(factory, owner_id)
        job = client.post("/jobs", headers=owner_headers, json={
            "title": title, "quote_id": quote_id, "service_start_at": service_start_at,
        }).json()
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
