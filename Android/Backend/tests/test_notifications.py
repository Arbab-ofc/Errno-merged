"""Focused notification service and API security regression tests."""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("NOTIFICATION_TOKEN_ENCRYPTION_KEY", "Z2RZbG1vT2ZrSnoyUTJFam10blp5VmlNbnV4UTVfN0c=")
os.environ.setdefault("NOTIFICATION_TOKEN_HASH_SECRET", "unit-test-token-hash-secret-keep-it-long-32")

from database import Base, get_db
import models
from firebase_auth import authenticated_user
from main import app

@pytest.fixture
def ctx(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread":False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = Session()
    user = models.User(firebase_uid="test-user", full_name="Test", role="worker", is_active=True)
    other = models.User(firebase_uid="other-user", full_name="Other", role="shopkeeper", is_active=True)
    db.add_all([user,other]); db.commit()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[authenticated_user] = lambda: user
    yield db,user,other,Session
    app.dependency_overrides.clear(); db.close(); Base.metadata.drop_all(engine); engine.dispose()

def test_device_register_rotation_reassignment_and_owner_delete(ctx):
    db,user,other,_=ctx; client=TestClient(app)
    first=client.post("/api/v1/devices/register",json={"platform":"android","deviceId":"install-1","fcmToken":"token-value-that-is-long-enough-001"})
    assert first.status_code==200
    device=first.json()["deviceId"]
    second=client.post("/api/v1/devices/register",json={"platform":"android","deviceId":"install-1","fcmToken":"token-value-that-is-long-enough-002"})
    assert second.status_code==200
    row=db.query(models.NotificationDevice).filter_by(id=second.json()["deviceId"]).one()
    assert row.user_id==user.id and row.active
    assert client.delete(f"/api/v1/devices/{device}").status_code in (204,404)

def test_token_reassignment_and_foreign_device_removal(ctx):
    db,user,other,_=ctx; client=TestClient(app)
    from services.notification_service import register_device
    row=register_device(db,user=user,platform="ios",device_identifier="shared-install",fcm_token="shared-token-value-long-enough-123",app_version=None)
    db.commit()
    moved=register_device(db,user=other,platform="ios",device_identifier="shared-install",fcm_token="shared-token-value-long-enough-123",app_version=None)
    db.commit()
    assert moved.id==row.id and moved.user_id==other.id
    assert client.delete(f"/api/v1/devices/{moved.id}").status_code==404

def test_inbox_keyset_pagination_and_mark_all(ctx):
    db,user,_,_=ctx; client=TestClient(app)
    from services.notification_service import queue_notification
    for i in range(4):
        queue_notification(db,recipient=user,event_type="job_started",category="job",title=str(i),body="Update",event_id=f"page-{i}")
    db.commit()
    first=client.get("/api/v1/notifications?limit=2").json()
    assert len(first["items"])==2 and first["nextCursor"]
    second=client.get(f"/api/v1/notifications?limit=2&cursor={first['nextCursor']}").json()
    assert len(second["items"])==2
    assert client.patch("/api/v1/notifications/read-all").json()["updated"]==4

def test_inbox_read_preferences_and_cross_user_access(ctx):
    db,user,other,_=ctx; client=TestClient(app)
    from services.notification_service import queue_notification
    row=queue_notification(db,recipient=other,event_type="booking_created",category="booking",title="A",body="B",event_id="test:event")
    mine=queue_notification(db,recipient=user,event_type="booking_created",category="booking",title="Mine",body="B",event_id="test:mine")
    db.commit()
    assert client.get("/api/v1/notifications/unread-count").json()["count"]==1
    assert client.patch(f"/api/v1/notifications/{row.id}/read").status_code==404
    assert client.patch(f"/api/v1/notifications/{mine.id}/read").status_code==200
    assert client.get("/api/v1/notifications/unread-count").json()["count"]==0
    assert client.patch("/api/v1/notifications/preferences",json={"marketing_enabled":True}).json()["marketing_enabled"] is True

def test_transaction_rollback_removes_inbox_and_outbox(ctx):
    db,user,_,Session=ctx
    from services.notification_service import queue_notification
    row=queue_notification(db,recipient=user,event_type="job_started",category="job",title="Started",body="Update",event_id="rollback-event")
    db.rollback()
    fresh=Session()
    assert fresh.query(models.Notification).filter_by(id=row.id).count()==0
    assert fresh.query(models.NotificationOutbox).filter_by(event_id="rollback-event").count()==0
    fresh.close()

def test_deduplication_preserves_single_notification_and_outbox(ctx):
    db,user,_,_=ctx
    from services.notification_service import queue_notification
    a=queue_notification(db,recipient=user,event_type="job_started",category="job",title="Started",body="Update",event_id="duplicate-event")
    b=queue_notification(db,recipient=user,event_type="job_started",category="job",title="Started",body="Update",event_id="duplicate-event")
    db.commit()
    assert a.id==b.id
    assert db.query(models.NotificationOutbox).filter_by(event_id="duplicate-event").count()==1

def test_disabled_provider_is_never_marked_accepted(ctx,monkeypatch):
    db,user,_,_=ctx
    from services.notification_service import queue_notification
    from services.notification_dispatcher import dispatch_one
    from services.fcm_provider import PushResult
    device=models.NotificationDevice(user_id=user.id,role="worker",platform="android",device_identifier="d",encrypted_token="x",token_hash="a"*64,active=True)
    db.add(device)
    queue_notification(db,recipient=user,event_type="job_started",category="job",title="Started",body="Update",event_id="no-fcm")
    db.commit()
    def unavailable(*_): return PushResult(False,error_code="PUSH_DISABLED",retryable=True)
    assert dispatch_one(db,sender=unavailable)
    item=db.query(models.NotificationOutbox).filter_by(event_id="no-fcm").one()
    assert item.status=="retrying" and item.last_error_code=="PUSH_DISABLED"

def test_accepted_and_invalid_token_delivery_are_distinguished(ctx):
    db,user,_,_=ctx
    from services.notification_service import queue_notification
    from services.notification_dispatcher import dispatch_one
    from services.fcm_provider import PushResult
    device=models.NotificationDevice(user_id=user.id,role="worker",platform="android",device_identifier="valid",encrypted_token="x",token_hash="b"*64,active=True)
    invalid=models.NotificationDevice(user_id=user.id,role="worker",platform="ios",device_identifier="invalid",encrypted_token="x",token_hash="c"*64,active=True)
    db.add_all([device,invalid]); queue_notification(db,recipient=user,event_type="job_started",category="job",title="Started",body="Update",event_id="accept-invalid")
    db.commit()
    def mixed(row,_): return PushResult(True,provider_message_id="projects/p/messages/123") if row.id==device.id else PushResult(False,error_code="UNREGISTERED",invalid_token=True)
    assert dispatch_one(db,sender=mixed)
    outbox=db.query(models.NotificationOutbox).filter_by(event_id="accept-invalid").one()
    assert outbox.status=="permanently_failed"
    assert db.query(models.NotificationDeliveryAttempt).filter_by(notification_id=outbox.notification_id,status="accepted_by_fcm").count()==1
    assert db.query(models.NotificationDevice).filter_by(id=invalid.id).one().active is False
