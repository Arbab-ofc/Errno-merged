"""Integration coverage against an already migrated disposable local database.

Set ERRNO_TEST_DATABASE_URL to the dedicated errno_phase22_test database after
applying alembic_canonical.ini. This test rejects non-loopback targets and never
creates or drops schema objects.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
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
from routers.pricing import router as pricing_router  # noqa: E402
from models import DurationPricing, PricingSettings  # noqa: E402


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
    assert "pricing_rule_snapshot" in {column["name"] for column in inspect(engine).get_columns("pricing_quotes", schema="public")}
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
    app.include_router(pricing_router)
    app.dependency_overrides[get_db] = get_test_db
    with engine.begin() as connection:
        assert connection.execute(text("select version_num from public.alembic_version")).scalar_one() == "eb72a31c4890"
        connection.execute(text("DELETE FROM pricing_quotes"))
        connection.execute(text("DELETE FROM applications"))
        connection.execute(text("DELETE FROM jobs"))
        connection.execute(text("DELETE FROM shops"))
        connection.execute(text("DELETE FROM otps"))
        connection.execute(text("DELETE FROM users"))
    try:
        with TestClient(app) as client:
            yield client, factory
    finally:
        app.dependency_overrides.clear()
        firebase_auth.verify_firebase_token = original_verifier
        engine.dispose()


def test_firebase_profile_roles_and_shop_job_application_fks(migrated_postgres_client):
    client, factory = migrated_postgres_client
    owner_headers = {"Authorization": "Bearer owner-token"}
    login = client.post("/api/v1/auth/firebase", headers=owner_headers)
    assert login.status_code == 200
    user_id = login.json()["user"]["id"]
    assert client.get("/api/v1/users/me", headers=owner_headers).json()["id"] == user_id
    assert client.patch("/api/v1/users/me", headers=owner_headers, json={"role": "shop_owner"}).json()["role"] == "shop_owner"

    assert client.get("/shops/me", headers=owner_headers).json() is None
    shop = client.put("/shops/me", headers=owner_headers, json={"shop_name": "Postgres Shop"})
    assert shop.status_code == 200
    with factory() as db:
        settings=db.query(PricingSettings).filter_by(id="singleton").one()
        settings.commission_rate=0.08; settings.quote_ttl_seconds=300
        settings.rounding_policy="half_up"; settings.default_timezone="Asia/Kolkata"
        settings.surge_enabled=False; settings.time_pricing_enabled=False; settings.demand_pricing_enabled=False
        duration=db.query(DurationPricing).filter_by(duration_hours=8).one()
        duration.base_price=100; duration.maximum_price=830; duration.enabled=True
        duration.approval_status="approved"; duration.effective_from=datetime.now(timezone.utc)-timedelta(days=1)
        duration.effective_until=None
        db.commit()
    service_start="2030-01-01T10:00:00+05:30"
    quote=client.post("/api/v1/pricing/quotes",headers=owner_headers,json={
        "duration_hours":8,"service_start_at":service_start,"area_id":None,
    })
    assert quote.status_code==200
    job = client.post("/jobs", headers=owner_headers, json={"title": "Postgres job",
        "quote_id":quote.json()["quote_id"],"service_start_at":service_start})
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
    accepted=client.patch(f"/jobs/{job.json()['id']}/applications/{application.json()['id']}",headers=owner_headers,json={"decision":"accepted"})
    assert accepted.status_code==200 and accepted.json()["status"]=="accepted"
    started=client.post(f"/jobs/{job.json()['id']}/start",headers=worker_headers)
    assert started.status_code==200 and started.json()["status"]=="in_progress"
    completed=client.post(f"/jobs/{job.json()['id']}/complete",headers=owner_headers)
    assert completed.status_code==200 and completed.json()["status"]=="completed"


def test_postgres_quote_cannot_be_consumed_twice_concurrently(migrated_postgres_client):
    client,factory=migrated_postgres_client
    owner_headers={"Authorization":"Bearer owner-token"}
    with factory() as db:
        from models import User, PricingSettings, DurationPricing
        owner=db.query(User).filter_by(firebase_uid="pg-firebase-owner").one()
        settings=db.query(PricingSettings).filter_by(id="singleton").one()
        settings.commission_rate=0.08; settings.quote_ttl_seconds=300
        settings.rounding_policy="half_up"; settings.default_timezone="Asia/Kolkata"
        settings.surge_enabled=False; settings.time_pricing_enabled=False; settings.demand_pricing_enabled=False
        duration=db.query(DurationPricing).filter_by(duration_hours=1).one()
        duration.base_price=120; duration.maximum_price=160; duration.enabled=True
        duration.approval_status="approved"; duration.effective_from=datetime.now(timezone.utc)-timedelta(days=1)
        duration.effective_until=None
        db.commit()
    service="2030-01-01T06:30:00+00:00"
    quote_response=client.post("/api/v1/pricing/quotes",headers=owner_headers,json={"duration_hours":1,"service_start_at":service})
    assert quote_response.status_code==200,quote_response.text
    request={"title":"Concurrent quote race","quote_id":quote_response.json()["quote_id"],
             "service_start_at":service,"duration_type":"1 hour"}
    def consume(_):
        return client.post("/jobs",headers=owner_headers,json=request).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses=list(pool.map(consume,range(2)))
    assert sorted(statuses)==[200,409]
    with factory() as db:
        from models import Job, PricingQuote
        assert db.query(Job).filter_by(title="Concurrent quote race").count()==1
        quote_row=db.query(PricingQuote).filter_by(id=request["quote_id"]).one()
        assert quote_row.status=="consumed" and quote_row.job_id is not None
