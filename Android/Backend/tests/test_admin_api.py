import sys
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import firebase_auth
from cors_config import allowed_origins
from database import Base, get_db
from models import AdminAuditLog, AdminPermission, Application, Job, Shop, User
from routers import admin, auth, firebase, health, jobs


@pytest.fixture
def admin_client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def get_test_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    tokens = {
        "admin-token": {"uid": "admin-uid", "email": "admin@example.test"},
        "reader-token": {"uid": "reader-uid", "email": "reader@example.test"},
        "owner-token": {"uid": "owner-uid", "email": "owner@example.test"},
        "worker-token": {"uid": "worker-uid", "email": "worker@example.test"},
        "phone-token": {"uid": "phone-uid", "phone_number": "+919971439107", "email": "phone@example.test"},
        "invalid-token": None,
    }

    def verify(token):
        if tokens.get(token) is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        return tokens.get(token, {"uid": token, "email": None})

    monkeypatch.setattr(firebase_auth, "verify_firebase_token", verify)
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(auth.router)
    app.include_router(jobs.router)
    app.include_router(firebase.router)
    app.include_router(admin.router)
    app.include_router(health.router)
    app.dependency_overrides[get_db] = get_test_db
    with TestClient(app) as client:
        yield client, factory
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def add_admin(factory, uid="admin-uid", permissions=None, active=True):
    with factory() as db:
        record = AdminPermission(
            firebase_uid=uid,
            email=f"{uid}@example.test",
            permissions=permissions or ["dashboard.read", "users.read", "users.manage", "jobs.read", "jobs.manage"],
            active=active,
            granted_by_uid="operator-uid",
            reason="test fixture",
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record.id


def add_user(factory, uid, role, **values):
    with factory() as db:
        user = User(firebase_uid=uid, role=role, full_name=values.get("name", uid),
                    email=values.get("email"), phone_number=values.get("phone"),
                    is_active=values.get("active", True))
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id


def test_admin_authentication_and_server_side_permission_gate(admin_client):
    client, factory = admin_client
    add_admin(factory)
    assert client.get("/api/v1/admin/dashboard").status_code == 401
    assert client.get("/api/v1/admin/dashboard", headers={"Authorization": "Bearer invalid-token"}).status_code == 401
    assert client.get("/api/v1/admin/dashboard", headers={"Authorization": "Bearer reader-token"}).status_code == 403
    response = client.get("/api/v1/admin/me", headers={"Authorization": "Bearer admin-token"})
    assert response.status_code == 200
    assert response.json()["firebase_uid"] == "admin-uid"
    assert response.json()["permissions"] == ["dashboard.read", "users.read", "users.manage", "jobs.read", "jobs.manage"]


def test_inactive_admin_and_missing_scope_are_forbidden(admin_client):
    client, factory = admin_client
    add_admin(factory, active=False)
    assert client.get("/api/v1/admin/me", headers={"Authorization": "Bearer admin-token"}).status_code == 403
    add_admin(factory, uid="reader-uid", permissions=["dashboard.read"])
    response = client.get("/api/v1/admin/workers", headers={"Authorization": "Bearer reader-token"})
    assert response.status_code == 403


def test_disabled_errno_account_cannot_use_active_admin_grant(admin_client):
    client, factory = admin_client
    add_admin(factory)
    add_user(factory, "admin-uid", "worker", active=False)
    assert client.get("/api/v1/admin/me", headers={"Authorization": "Bearer admin-token"}).status_code == 403


def test_dashboard_aggregates_canonical_tables_and_trends(admin_client):
    client, factory = admin_client
    add_admin(factory)
    owner_id = add_user(factory, "owner-uid", "shop_owner", name="Shop Owner")
    worker_id = add_user(factory, "worker-uid", "worker", name="Worker")
    with factory() as db:
        shop = Shop(owner_id=owner_id, shop_name="Corner Shop")
        db.add(shop)
        db.flush()
        open_job = Job(shop_id=shop.id, title="Open shift", status="open")
        done_job = Job(shop_id=shop.id, title="Completed shift", status="completed")
        db.add_all([open_job, done_job])
        db.flush()
        db.add(Application(job_id=open_job.id, worker_id=worker_id, status="pending"))
        db.commit()
    result = client.get("/api/v1/admin/dashboard", headers={"Authorization": "Bearer admin-token"})
    assert result.status_code == 200
    data = result.json()
    assert data["metrics"] == {
        "total_users": 2, "total_workers": 1, "total_shop_owners": 1,
        "total_shops": 1, "total_jobs": 2, "active_jobs": 1,
        "completed_jobs": 1, "total_applications": 1,
    }
    assert len(data["registrations_by_day"]) == 7
    assert len(data["jobs_by_day"]) == 7
    assert data["recent_jobs"][0]["title"] in {"Open shift", "Completed shift"}


def test_user_lists_search_paginate_details_and_audit_supported_mutations(admin_client):
    client, factory = admin_client
    add_admin(factory)
    owner_id = add_user(factory, "owner-uid", "shop_owner", name="North Shop Owner", email="north@example.test")
    worker_id = add_user(factory, "worker-uid", "worker", name="Worker One")
    with factory() as db:
        shop = Shop(owner_id=owner_id, shop_name="North Shop")
        db.add(shop)
        db.flush()
        job = Job(shop_id=shop.id, title="Morning shift", status="open")
        db.add(job)
        db.flush()
        db.add(Application(job_id=job.id, worker_id=worker_id, status="pending"))
        db.commit()

    headers = {"Authorization": "Bearer admin-token"}
    page = client.get("/api/v1/admin/shop-owners?q=North&limit=1&offset=0", headers=headers)
    assert page.status_code == 200 and page.json()["total"] == 1
    owner_detail = client.get(f"/api/v1/admin/shop-owners/{owner_id}", headers=headers)
    assert owner_detail.status_code == 200
    assert owner_detail.json()["shops"][0]["shop_name"] == "North Shop"
    assert owner_detail.json()["jobs"][0]["title"] == "Morning shift"

    worker_page = client.get("/api/v1/admin/workers?limit=1", headers=headers)
    assert worker_page.status_code == 200 and worker_page.json()["total"] == 1
    worker_detail = client.get(f"/api/v1/admin/workers/{worker_id}", headers=headers)
    assert worker_detail.status_code == 200
    assert worker_detail.json()["applications"][0]["job_title"] == "Morning shift"

    changed = client.patch(f"/api/v1/admin/workers/{worker_id}", headers=headers, json={"is_active": False})
    assert changed.status_code == 200 and changed.json()["is_active"] is False
    with factory() as db:
        event = db.query(AdminAuditLog).filter_by(resource_id=worker_id).one()
        assert event.administrator_uid == "admin-uid"
        assert event.change_metadata["is_active"] == {"from": True, "to": False}
        assert event.created_at is not None


def test_job_admin_list_detail_transitions_and_audit(admin_client):
    client, factory = admin_client
    add_admin(factory)
    owner_id = add_user(factory, "owner-uid", "shop_owner", name="Owner")
    worker_id = add_user(factory, "worker-uid", "worker", name="Worker")
    with factory() as db:
        shop = Shop(owner_id=owner_id, shop_name="Market")
        db.add(shop)
        db.flush()
        job = Job(shop_id=shop.id, title="Stock assistant", status="open")
        db.add(job)
        db.flush()
        db.add(Application(job_id=job.id, worker_id=worker_id, status="pending"))
        db.commit()
        job_id = job.id

    headers = {"Authorization": "Bearer admin-token"}
    listing = client.get("/api/v1/admin/jobs?status_filter=open&q=Stock", headers=headers)
    assert listing.status_code == 200 and listing.json()["total"] == 1
    detail = client.get(f"/api/v1/admin/jobs/{job_id}", headers=headers)
    assert detail.status_code == 200 and detail.json()["applications"][0]["worker_name"] == "Worker"
    changed = client.patch(f"/api/v1/admin/jobs/{job_id}/status", headers=headers, json={"status": "assigned"})
    assert changed.status_code == 200 and changed.json()["status"] == "assigned"
    invalid = client.patch(f"/api/v1/admin/jobs/{job_id}/status", headers=headers, json={"status": "open"})
    assert invalid.status_code == 409
    with factory() as db:
        assert db.query(AdminAuditLog).filter_by(resource_id=job_id).count() == 1


def test_legacy_mobile_job_transition_validation_preserves_owner_scope(admin_client):
    client, factory = admin_client
    owner_id = add_user(factory, "owner-uid", "shop_owner", name="Owner")
    with factory() as db:
        shop = Shop(owner_id=owner_id, shop_name="Owner shop")
        db.add(shop)
        db.flush()
        job = Job(shop_id=shop.id, title="Job", status="completed")
        db.add(job)
        db.commit()
        job_id = job.id
    response = client.patch(
        f"/jobs/{job_id}/status?new_status=open",
        headers={"Authorization": "Bearer owner-token"},
    )
    assert response.status_code == 409


def test_legacy_otp_disabled_and_registration_requires_verified_identity(admin_client):
    client, _ = admin_client
    assert client.post("/auth/send-otp", json={"phone_number": "9971439107"}).status_code == 503
    assert client.post("/auth/verify-otp", json={"phone_number": "9971439107", "otp_code": "123456"}).status_code == 503
    body = {"full_name": "Owner", "phone_number": "9971439107", "role": "shop_owner"}
    assert client.post("/auth/register", json=body).status_code == 401
    assert client.post("/auth/register", headers={"Authorization": "Bearer phone-token"},
                       json={**body, "role": "admin"}).status_code == 422
    created = client.post("/auth/register", headers={"Authorization": "Bearer phone-token"}, json=body)
    assert created.status_code == 200
    assert created.json()["token"] is None
    modified_other = client.post("/auth/register", headers={"Authorization": "Bearer phone-token"},
                                 json={**body, "phone_number": "9999999999"})
    assert modified_other.status_code == 403


def test_health_error_is_sanitized_and_cors_is_allowlisted(admin_client):
    client, _ = admin_client
    from database import get_db

    def broken_db():
        class BrokenSession:
            def execute(self, _query):
                raise RuntimeError("private database diagnostic")
        yield BrokenSession()

    client.app.dependency_overrides[get_db] = broken_db
    response = client.get("/health")
    assert response.status_code == 503
    assert "private database diagnostic" not in response.text
    assert "database_error" not in response.json()

    allowed = client.options("/api/v1/admin/me", headers={
        "Origin": "https://admin.errno.in",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization",
    })
    assert allowed.headers.get("access-control-allow-origin") == "https://admin.errno.in"
    denied = client.options("/api/v1/admin/me", headers={
        "Origin": "https://attacker.example",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization",
    })
    assert denied.headers.get("access-control-allow-origin") is None


def test_firebase_verifier_rejects_revoked_tokens(monkeypatch):
    monkeypatch.setattr(firebase_auth, "firebase_app", lambda: object())
    def revoked(*_args, **_kwargs):
        raise firebase_auth.auth.RevokedIdTokenError("revoked")
    monkeypatch.setattr(firebase_auth.auth, "verify_id_token", revoked)
    with pytest.raises(HTTPException) as error:
        firebase_auth.verify_firebase_token("revoked-token")
    assert error.value.status_code == 401


def test_operator_provisioning_is_bootstrap_gated_idempotent_and_audited(admin_client):
    _, factory = admin_client
    from tools.provision_admin import apply_admin_change

    with factory() as db:
        with pytest.raises(ValueError, match="bootstrap"):
            apply_admin_change(db, action="grant", target_uid="first-admin", target_email="first@example.test",
                               actor_uid="operator", reason="change 1", permissions=["dashboard.read"], bootstrap=False)
        assert apply_admin_change(db, action="grant", target_uid="first-admin", target_email="first@example.test",
                                  actor_uid="first-admin", reason="change 1", permissions=["dashboard.read"], bootstrap=True)
        assert not apply_admin_change(db, action="grant", target_uid="first-admin", target_email="first@example.test",
                                      actor_uid="first-admin", reason="change 1", permissions=["dashboard.read"], bootstrap=False)
        assert apply_admin_change(db, action="grant", target_uid="second-admin", target_email="second@example.test",
                                  actor_uid="first-admin", reason="change 2", permissions=["users.read"], bootstrap=False)
        assert apply_admin_change(db, action="revoke", target_uid="second-admin", target_email="second@example.test",
                                  actor_uid="first-admin", reason="change 3", permissions=[], bootstrap=False)
        target = db.query(AdminPermission).filter_by(firebase_uid="second-admin").one()
        assert target.active is False
        assert db.query(AdminAuditLog).count() == 3
