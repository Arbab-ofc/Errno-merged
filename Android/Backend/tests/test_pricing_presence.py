from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
from pathlib import Path
import sys

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import firebase_auth
from database import Base, get_db
from models import (
    AdminPermission, AreaPricingRule, DemandPricingRule, DurationPricing,
    Job, PresenceSession, PricingQuote, PricingSettings, PricingSettingsDraft, TimePricingRule, User,
)
from routers.jobs import router as jobs_router
from routers.pricing import router as pricing_router

SERVICE_START = "2030-01-01T06:30:00+00:00"

@pytest.fixture
def pricing_client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    now = datetime.now(timezone.utc)
    with factory() as db:
        db.add_all([
            User(id="owner-id", firebase_uid="owner-uid", full_name="Owner", role="shop_owner"),
            User(id="worker-id", firebase_uid="worker-uid", full_name="Worker", role="worker"),
            User(id="stale-worker-id", firebase_uid="stale-worker-uid", full_name="Stale", role="worker"),
            User(id="recruiter-id", firebase_uid="recruiter-uid", full_name="Recruiter", role="shopkeeper"),
            AdminPermission(firebase_uid="pricing-admin", permissions=["pricing.read", "pricing.write", "pricing.activate", "presence.read"],
                            active=True, granted_by_uid="test", reason="isolated test"),
            AdminPermission(firebase_uid="limited-admin", permissions=["dashboard.read"],
                            active=True, granted_by_uid="test", reason="isolated test"),
            PricingSettings(id="singleton", surge_enabled=True, time_pricing_enabled=True,
                demand_pricing_enabled=True, combined_multiplier_cap=Decimal("2.0"),
                commission_rate=Decimal("0.08"), quote_ttl_seconds=300,
                rounding_policy="half_up", default_timezone="Asia/Kolkata",
                heartbeat_interval_seconds=60, presence_ttl_seconds=180, version=4),
            DurationPricing(id="duration-1", duration_hours=1, base_price=Decimal("120.00"),
                maximum_price=Decimal("160.00"), enabled=True, approval_status="approved",
                effective_from=now-timedelta(days=1), version=5),
            TimePricingRule(id="time-1", name="Test band", start_time=time(0), end_time=time(23, 59),
                timezone="Asia/Kolkata", multiplier=Decimal("1.0"), enabled=True,
                effective_from=now-timedelta(days=1), version=6),
            DemandPricingRule(id="demand-1", name="Test zero supply", demand_level="zero_supply",
                minimum_demand_ratio=None, maximum_demand_ratio=None,
                availability_thresholds={"zero_available_workers": True}, multiplier=Decimal("1.0"),
                enabled=True, effective_from=now-timedelta(days=1), version=7),
        ])
        db.commit()

    def get_test_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    tokens = {
        "owner-token": {"uid": "owner-uid"}, "worker-token": {"uid": "worker-uid"},
        "stale-worker-token": {"uid": "stale-worker-uid"}, "recruiter-token": {"uid": "recruiter-uid"},
        "admin-token": {"uid": "pricing-admin"}, "limited-admin-token": {"uid": "limited-admin"},
    }
    def verify(token):
        if token not in tokens:
            raise HTTPException(status_code=401, detail="Invalid test token")
        return tokens[token]
    monkeypatch.setattr(firebase_auth, "verify_firebase_token", verify)

    app = FastAPI()
    app.include_router(jobs_router)
    app.include_router(pricing_router)
    app.dependency_overrides[get_db] = get_test_db
    with TestClient(app) as client:
        yield client, factory
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def quote(client, *, time_multiplier="1", demand_multiplier="1", area_id=None):
    _, factory = client
    with factory() as db:
        t = db.query(TimePricingRule).filter_by(id="time-1").one()
        d = db.query(DemandPricingRule).filter_by(id="demand-1").one()
        t.multiplier = Decimal(time_multiplier)
        d.multiplier = Decimal(demand_multiplier)
        db.commit()
    response = client[0].post("/api/v1/pricing/quotes", headers={"Authorization": "Bearer owner-token"}, json={
        "duration_hours": 1, "service_start_at": SERVICE_START, "area_id": area_id,
    })
    assert response.status_code == 200, response.text
    return response.json()


def test_pricing_reference_scenarios_and_balanced_commission(pricing_client):
    a = quote(pricing_client)
    assert Decimal(str(a["raw_price"])) == Decimal("120.000000")
    assert Decimal(str(a["final_service_charge"])) == Decimal("120")
    b = quote(pricing_client, time_multiplier="1.25")
    assert Decimal(str(b["final_service_charge"])) == Decimal("150")
    c = quote(pricing_client, time_multiplier="1.25", demand_multiplier="1.20")
    assert Decimal(str(c["raw_price"])) == Decimal("180.000000")
    assert Decimal(str(c["final_service_charge"])) == Decimal("160")
    assert Decimal(str(c["commission_amount"])) == Decimal("12.80")
    assert Decimal(str(c["worker_payout_amount"])) == Decimal("147.20")
    assert Decimal(str(c["commission_amount"])) + Decimal(str(c["worker_payout_amount"])) == Decimal(str(c["final_service_charge"]))
    e = quote(pricing_client, time_multiplier="0.50", demand_multiplier="0.50")
    assert Decimal(str(e["final_service_charge"])) == Decimal("120")
    assert c["pricing_rule_snapshot"]["time_rule"]["version"] == 6
    assert c["pricing_rule_snapshot"]["demand_rule"]["version"] == 7
    assert "minimum_price" not in c


def test_area_override_and_global_fallback(pricing_client):
    _, factory = pricing_client
    with factory() as db:
        db.add(AreaPricingRule(id="area-1", area_key="market road", duration_hours=1,
            base_price=Decimal("130.00"), maximum_price=Decimal("150.00"),
            enabled=True, approval_status="approved", effective_from=datetime.now(timezone.utc)-timedelta(days=1), version=8))
        db.commit()
    overridden = quote(pricing_client, area_id="  Market   Road ")
    assert Decimal(str(overridden["base_price"])) == Decimal("130")
    assert Decimal(str(overridden["final_service_charge"])) == Decimal("130")
    assert overridden["pricing_rule_snapshot"]["area"]["version"] == 8
    fallback = quote(pricing_client, area_id="another address")
    assert Decimal(str(fallback["base_price"])) == Decimal("120")
    assert fallback["pricing_rule_snapshot"]["area"] is None


def test_rupee_rounding_and_midnight_crossing_time_band(pricing_client):
    client,factory=pricing_client
    with factory() as db:
        duration=db.query(DurationPricing).filter_by(duration_hours=1).one()
        duration.base_price=Decimal("120.50")
        rule=db.query(TimePricingRule).filter_by(id="time-1").one()
        rule.start_time=time(22); rule.end_time=time(6); rule.multiplier=Decimal("1.25")
        db.commit()
    response=client.post("/api/v1/pricing/quotes",headers={"Authorization":"Bearer owner-token"},json={
        "duration_hours":1,"service_start_at":"2030-01-01T20:30:00+00:00"})
    assert response.status_code==200,response.text
    result=response.json()
    assert result["time_multiplier"]==1.25
    assert Decimal(str(result["raw_price"]))==Decimal("150.625000")
    assert Decimal(str(result["final_service_charge"]))==Decimal("151")
    assert Decimal(str(result["commission_amount"]))==Decimal("12.08")
    assert Decimal(str(result["worker_payout_amount"]))==Decimal("138.92")


def test_missing_settings_reject_quote(pricing_client):
    client, factory = pricing_client
    with factory() as db:
        settings=db.query(PricingSettings).filter_by(id="singleton").one()
        settings.commission_rate=None
        db.commit()
    response=client.post("/api/v1/pricing/quotes",headers={"Authorization":"Bearer owner-token"},json={
        "duration_hours":1,"service_start_at":"2030-01-01T12:00:00+05:30"})
    assert response.status_code==503
    assert "configuration is incomplete" in response.json()["detail"]


def test_admin_can_preview_saved_draft_without_activating_or_persisting_quote(pricing_client):
    client,factory=pricing_client
    with factory() as db:
        duration=db.query(DurationPricing).filter_by(duration_hours=1).one()
        duration.base_price=Decimal("130"); duration.maximum_price=Decimal("150")
        duration.enabled=False; duration.approval_status="draft"
        db.add(PricingSettingsDraft(id="singleton",values={
            "commission_rate":"0.08","quote_ttl_seconds":300,"rounding_policy":"half_up",
            "default_timezone":"Asia/Kolkata","surge_enabled":False,
            "time_pricing_enabled":False,"demand_pricing_enabled":False,
        },version=5,updated_by="pricing-admin"))
        db.commit()
    with factory() as db: before=db.query(PricingQuote).count()
    preview=client.post("/api/v1/admin/pricing/preview",headers={"Authorization":"Bearer admin-token"},json={
        "duration_hours":1,"service_start_at":"2030-01-01T06:30:00+00:00",
        "use_draft_configuration":True,"scenario_time_multiplier":"1.25","scenario_demand_multiplier":"1.20",
    })
    assert preview.status_code==200,preview.text
    result=preview.json()
    assert result["preview_only"] is True and result["configuration_source"]=="draft"
    assert Decimal(str(result["base_price"]))==Decimal("130")
    assert Decimal(str(result["raw_price"]))==Decimal("195.000000")
    assert Decimal(str(result["final_service_charge"]))==Decimal("150")
    assert Decimal(str(result["commission_amount"]))==Decimal("12.00")
    assert Decimal(str(result["worker_payout_amount"]))==Decimal("138.00")
    with factory() as db:
        assert db.query(PricingQuote).count()==before
        row=db.query(DurationPricing).filter_by(duration_hours=1).one()
        assert row.approval_status=="draft" and not row.enabled


def test_quote_ownership_expiration_single_use_and_server_price(pricing_client):
    client, factory=pricing_client
    q=quote(pricing_client,time_multiplier="1.25",demand_multiplier="1.20")
    qid=q["quote_id"]
    wrong_owner=client.get(f"/api/v1/pricing/quotes/{qid}",headers={"Authorization":"Bearer worker-token"})
    assert wrong_owner.status_code==404
    payload={"title":"Quote locked job","quote_id":qid,"service_start_at":SERVICE_START,
             "duration_type":"1 hour","location":None,"pay_amount":999999}
    created=client.post("/jobs",headers={"Authorization":"Bearer owner-token"},json=payload)
    assert created.status_code==200,created.text
    job=created.json()
    assert job["pay_amount"]==160
    replay=client.post("/jobs",headers={"Authorization":"Bearer owner-token"},json=payload)
    assert replay.status_code==409
    assert client.get(f"/api/v1/jobs/{job['id']}/worker-payout",headers={"Authorization":"Bearer worker-token"}).json()["worker_payout_amount"]==147.2
    with factory() as db:
        assert db.query(Job).count()==1
        assert db.query(PricingQuote).filter_by(id=qid).one().job_id==job["id"]

    expired=quote(pricing_client)
    with factory() as db:
        row=db.query(PricingQuote).filter_by(id=expired["quote_id"]).one()
        row.expires_at=datetime.now(timezone.utc)-timedelta(seconds=1); db.commit()
    expired_payload={**payload,"quote_id":expired["quote_id"]}
    assert client.post("/jobs",headers={"Authorization":"Bearer owner-token"},json=expired_payload).status_code==409
    with factory() as db: assert db.query(Job).count()==1


def test_admin_scopes_activation_safeguard_and_presence_lifecycle(pricing_client):
    client,factory=pricing_client
    path="/api/v1/admin/pricing/settings"
    assert client.get(path).status_code==401
    assert client.get(path,headers={"Authorization":"Bearer worker-token"}).status_code==403
    assert client.get(path,headers={"Authorization":"Bearer limited-admin-token"}).status_code==403
    admin_headers={"Authorization":"Bearer admin-token"}
    assert client.get(path,headers=admin_headers).status_code==200
    draft=client.patch(path,headers=admin_headers,json={
        "commission_rate":"0.08","quote_ttl_seconds":300,"rounding_policy":"half_up",
        "default_timezone":"Asia/Kolkata","surge_enabled":False,
        "time_pricing_enabled":False,"demand_pricing_enabled":False,
    })
    assert draft.status_code==200
    activated=client.post(path+"/activate",headers=admin_headers,json={})
    assert activated.status_code==422
    assert "1–12 hours" in activated.json()["detail"]
    assert client.get("/api/v1/admin/presence/summary",headers={"Authorization":"Bearer limited-admin-token"}).status_code==403

    worker_headers={"Authorization":"Bearer worker-token"}
    recruiter_headers={"Authorization":"Bearer recruiter-token"}
    for sid in ("worker-device-0001","worker-device-0002"):
        assert client.post("/api/v1/presence/heartbeat",headers=worker_headers,json={"session_identifier":sid,"device_platform":"test"}).status_code==200
    assert client.patch("/api/v1/workers/me/availability",headers=worker_headers,json={"available":True}).json()["available"] is True
    assert client.get("/api/v1/workers/me/availability",headers=worker_headers).json()["available"] is True
    assert client.get("/api/v1/workers/me/availability",headers={"Authorization":"Bearer stale-worker-token"}).json()["available"] is False
    assert client.post("/api/v1/presence/heartbeat",headers=recruiter_headers,json={"session_identifier":"recruiter-device-0001"}).status_code==200
    with factory() as db:
        db.add(PresenceSession(user_id="stale-worker-id",session_identifier="stale-device-0001",
            expires_at=datetime.now(timezone.utc)-timedelta(minutes=1),last_heartbeat_at=datetime.now(timezone.utc)-timedelta(minutes=5),
            availability_status="available",is_foreground=True))
        db.commit()
    summary=client.get("/api/v1/admin/presence/summary",headers=admin_headers).json()
    assert summary["online_workers"]==1 and summary["available_workers"]==1
    assert summary["online_recruiters"]==1
    assert summary["registered_workers"]==2 and summary["registered_recruiters"]==2
    assert client.post("/api/v1/presence/offline",headers=worker_headers,json={"session_identifier":"worker-device-0001"}).status_code==200
    summary=client.get("/api/v1/admin/presence/summary",headers=admin_headers).json()
    assert summary["online_workers"]==1
    client.post("/api/v1/presence/offline",headers=worker_headers,json={"session_identifier":"worker-device-0002"})
    summary=client.get("/api/v1/admin/presence/summary",headers=admin_headers).json()
    assert summary["online_workers"]==0 and summary["available_workers"]==0
