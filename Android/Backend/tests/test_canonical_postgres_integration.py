"""Integration coverage against an already migrated disposable local database.

Set ERRNO_TEST_DATABASE_URL to the dedicated errno_phase22_test database after
applying alembic_canonical.ini. This test rejects non-loopback targets and never
creates or drops schema objects.
"""

import os
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import get_db  # noqa: E402
from routers.firebase import router as firebase_router  # noqa: E402
from routers.jobs import router as jobs_router  # noqa: E402
from routers.shops import router as shops_router  # noqa: E402


@pytest.fixture(scope="module")
def migrated_postgres_client():
    raw_url = os.environ.get("ERRNO_TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("ERRNO_TEST_DATABASE_URL is not configured")
    url = make_url(raw_url)
    if (
        url.get_backend_name() not in ("postgresql", "postgres")
        or url.host not in ("localhost", "127.0.0.1", "::1")
        or url.database != "errno_phase22_test"
    ):
        pytest.fail("Integration test only permits the dedicated loopback errno_phase22_test database")

    engine = create_engine(url, pool_pre_ping=True)
    assert set(inspect(engine).get_table_names(schema="public")) >= {
        "users", "otps", "shops", "jobs", "applications", "alembic_version"
    }, "Apply the canonical migration to the disposable test database first"
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def get_test_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    def verify(token):
        identities = {
            "owner-token": {"uid": "pg-firebase-owner", "name": "PG Owner", "email": "pg-owner@example.test"},
            "worker-token": {"uid": "pg-firebase-worker", "name": "PG Worker", "email": "pg-worker@example.test"},
        }
        from fastapi import HTTPException
        if token not in identities:
            raise HTTPException(status_code=401, detail="Invalid test token")
        return identities[token]

    import firebase_auth
    original_verifier = firebase_auth.verify_firebase_token
    firebase_auth.verify_firebase_token = verify

    app = FastAPI()
    app.include_router(firebase_router)
    app.include_router(jobs_router)
    app.include_router(shops_router)
    app.dependency_overrides[get_db] = get_test_db
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM applications"))
        connection.execute(text("DELETE FROM jobs"))
        connection.execute(text("DELETE FROM shops"))
        connection.execute(text("DELETE FROM otps"))
        connection.execute(text("DELETE FROM users"))
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        firebase_auth.verify_firebase_token = original_verifier
        engine.dispose()


def test_firebase_profile_roles_and_shop_job_application_fks(migrated_postgres_client):
    client = migrated_postgres_client
    owner_headers = {"Authorization": "Bearer owner-token"}
    login = client.post("/api/v1/auth/firebase", headers=owner_headers)
    assert login.status_code == 200
    user_id = login.json()["user"]["id"]
    assert client.get("/api/v1/users/me", headers=owner_headers).json()["id"] == user_id
    assert client.patch("/api/v1/users/me", headers=owner_headers, json={"role": "shop_owner"}).json()["role"] == "shop_owner"

    shop = client.get("/shops/me/ignored", headers=owner_headers)
    assert shop.status_code == 200
    job = client.post("/jobs", headers=owner_headers, json={"title": "Postgres job"})
    assert job.status_code == 200
    assert job.json()["shop_id"] == shop.json()["id"]

    worker_headers = {"Authorization": "Bearer worker-token"}
    worker = client.post("/api/v1/auth/firebase", headers=worker_headers)
    assert worker.status_code == 200
    assert client.patch("/api/v1/users/me", headers=worker_headers, json={"role": "worker"}).status_code == 200
    application = client.post(f"/jobs/{job.json()['id']}/apply", headers=worker_headers)
    assert application.status_code == 200
    assert application.json()["worker_id"] == worker.json()["user"]["id"]
    assert client.post(f"/jobs/{job.json()['id']}/apply", headers=worker_headers).json()["id"] == application.json()["id"]
