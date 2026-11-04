import sys
import asyncio
from pathlib import Path
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import firebase_auth
from database import Base, get_db
from models import Job, Shop, User, WorkerLocation
from routers import maps

@pytest.fixture
def maps_client(monkeypatch):
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory=sessionmaker(bind=engine,autoflush=False,autocommit=False)
    with factory() as db:
        db.add_all([
            User(id="owner",firebase_uid="owner-uid",role="shop_owner",is_active=True),
            User(id="worker",firebase_uid="worker-uid",role="worker",is_active=True),
            User(id="other",firebase_uid="other-uid",role="shop_owner",is_active=True),
            Shop(id="shop",owner_id="owner",shop_name="Test shop"),
            Job(id="job",shop_id="shop",title="Test",status="in_progress",assigned_worker_id="worker",location="Market",latitude=28.6,longitude=77.2,duration_type="2 hours",pay_amount=1),
            WorkerLocation(user_id="worker",job_id="job",latitude=28.61,longitude=77.21,updated_at=datetime.now(timezone.utc)),
        ]); db.commit()
    def get_test_db():
        db=factory()
        try: yield db
        finally: db.close()
    ids={"owner-token":"owner-uid","worker-token":"worker-uid","other-token":"other-uid"}
    def verify(token):
        if token not in ids: raise HTTPException(401,"Invalid token")
        return {"uid":ids[token]}
    monkeypatch.setattr(firebase_auth,"verify_firebase_token",verify)
    monkeypatch.setattr(maps,"verify_firebase_token",verify)
    monkeypatch.setattr(maps,"SessionLocal",factory)
    app=FastAPI(); app.include_router(maps.router); app.include_router(__import__("routers.jobs",fromlist=["router"]).router)
    app.dependency_overrides[get_db]=get_test_db
    with TestClient(app) as client: yield client,factory
    Base.metadata.drop_all(engine); engine.dispose()

def test_tracking_location_is_visible_only_to_owning_shopkeeper(maps_client):
    client,_=maps_client
    owner={"Authorization":"Bearer owner-token"}
    assert client.get("/jobs/job/tracking/location",headers=owner).json()["location"]["latitude"]==28.61
    assert client.get("/jobs/job/tracking/location",headers={"Authorization":"Bearer other-token"}).status_code==403
    assert client.get("/jobs/job/tracking/location",headers={"Authorization":"Bearer worker-token"}).status_code==403
    assert client.get("/jobs/job/tracking/location").status_code==401

def test_tracking_websocket_authorizes_job_and_closes_on_termination(maps_client):
    client,factory=maps_client
    with client.websocket_connect("/ws/jobs/job/tracking",headers={"Authorization":"Bearer owner-token"}) as ws:
        first=ws.receive_json(); assert first["state"]=="online"
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/jobs/job/tracking",headers={"Authorization":"Bearer other-token"}) as outsider:
                outsider.receive_json()
        with factory() as db:
            db.query(Job).filter_by(id="job").update({Job.status:"completed"}); db.commit()
        ws.send_text("heartbeat")
        assert ws.receive_json()["state"]=="ended"

def test_nearby_search_rejects_unowned_job_and_requires_postgis(maps_client):
    client,_=maps_client
    assert client.get("/jobs/job/nearby-workers?radius_km=5",headers={"Authorization":"Bearer other-token"}).status_code==403
    assert client.get("/jobs/job/nearby-workers?radius_km=0",headers={"Authorization":"Bearer owner-token"}).status_code==422
    assert client.get("/jobs/job/nearby-workers?radius_km=5",headers={"Authorization":"Bearer owner-token"}).status_code==503

def test_tracking_hub_broadcasts_updates_and_closes_ended_sessions():
    from routers.maps import TrackingHub
    class Socket:
        def __init__(self): self.messages=[]; self.closed=False
        async def send_json(self,payload): self.messages.append(payload)
        async def close(self,code=1000): self.closed=True
    async def run():
        hub=TrackingHub(); ws=Socket(); hub._clients["booking"]={ws}
        await hub._broadcast("booking",{"state":"online","latitude":1.0,"longitude":2.0})
        await hub._broadcast("booking",{"state":"ended"},close=True)
        assert ws.messages[0]["latitude"]==1.0
        assert ws.messages[1]["state"]=="ended" and ws.closed
        assert "booking" not in hub._clients
    asyncio.run(run())

def test_tracking_socket_closes_when_authenticated_user_is_disabled(maps_client):
    client,factory=maps_client
    with client.websocket_connect("/ws/jobs/job/tracking",headers={"Authorization":"Bearer owner-token"}) as ws:
        assert ws.receive_json()["state"]=="online"
        with factory() as db:
            db.query(User).filter_by(id="owner").update({User.is_active:False}); db.commit()
        ws.send_text("heartbeat")
        assert ws.receive_json()["type"]=="heartbeat_ack"
        with pytest.raises(WebSocketDisconnect): ws.receive_json()
