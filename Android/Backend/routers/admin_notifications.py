from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session
from database import get_db
from firebase_auth import require_admin
from models import Notification, NotificationDeliveryAttempt, NotificationDevice, NotificationOutbox, User
from services.notification_service import record_admin_retry

router = APIRouter(prefix="/api/v1/admin/notifications", tags=["Admin Notifications"])

@router.get("")
def admin_inbox(user=Depends(require_admin("notifications.read")), db: Session=Depends(get_db), limit: int=Query(50,ge=1,le=100)):
    account=db.query(User).filter_by(firebase_uid=user.firebase_uid).first()
    if account is None: return {"items":[]}
    rows = db.query(Notification).filter_by(recipient_user_id=account.id, category="admin").order_by(Notification.created_at.desc()).limit(limit).all()
    return {"items":[{"id":r.id,"title":r.title,"body":r.body,"eventType":r.event_type,"data":r.data_payload,"createdAt":r.created_at,"readAt":r.read_at} for r in rows]}

@router.get("/unread-count")
def admin_unread_count(user=Depends(require_admin("notifications.read")), db: Session=Depends(get_db)):
    account=db.query(User).filter_by(firebase_uid=user.firebase_uid).first()
    count=db.query(Notification).filter_by(recipient_user_id=account.id if account else "",category="admin",read_at=None).count()
    return {"count":count}

@router.get("/delivery")
def delivery_summary(user=Depends(require_admin("notifications.audit")), db: Session=Depends(get_db)):
    counts = dict(db.query(NotificationOutbox.status,func.count(NotificationOutbox.id)).group_by(NotificationOutbox.status).all())
    oldest = db.query(func.min(NotificationOutbox.created_at)).filter(NotificationOutbox.status.in_(["queued","retrying"])).scalar()
    if oldest and oldest.tzinfo is None: oldest = oldest.replace(tzinfo=timezone.utc)
    queue_latency = max(0, int((datetime.now(timezone.utc)-oldest).total_seconds())) if oldest else 0
    recent = db.query(NotificationDeliveryAttempt).order_by(NotificationDeliveryAttempt.attempted_at.desc()).limit(100).all()
    return {"queue":counts,"queueLatencySeconds":queue_latency,"activeDevices":db.query(NotificationDevice).filter_by(active=True).count(),
        "invalidTokens":db.query(func.count(distinct(NotificationDeliveryAttempt.device_id))).filter(
            NotificationDeliveryAttempt.status=="invalid_token", NotificationDeliveryAttempt.device_id.is_not(None)).scalar() or 0,
        "recentAttempts":[{"notificationId":a.notification_id,"deviceId":a.device_id,"status":a.status,"errorCode":a.error_code,"attemptedAt":a.attempted_at,
            "outboxId":(db.query(NotificationOutbox.id).filter_by(notification_id=a.notification_id).scalar())} for a in recent]}

@router.post("/delivery/{outbox_id}/retry")
def retry_delivery(outbox_id: str, user=Depends(require_admin("notifications.manage")), db: Session=Depends(get_db)):
    row = db.query(NotificationOutbox).filter_by(id=outbox_id).with_for_update().first()
    if row is None: raise HTTPException(404,"Queue item not found")
    if row.status not in {"permanently_failed","retrying"}: raise HTTPException(409,"Queue item is not eligible for retry")
    row.status="queued"; row.attempts=0; row.next_attempt_at=datetime.now(timezone.utc); row.processed_at=None; row.last_error_code=None; row.lease_owner=None; row.lease_until=None
    record_admin_retry(db,admin_uid=user.firebase_uid or user.id,outbox_id=row.id)
    db.commit(); return {"status":"queued"}

@router.patch("/{notification_id}/read")
def mark_admin_read(notification_id: str, user=Depends(require_admin("notifications.read")), db: Session=Depends(get_db)):
    account=db.query(User).filter_by(firebase_uid=user.firebase_uid).first()
    row=db.query(Notification).filter_by(id=notification_id,recipient_user_id=account.id if account else "",category="admin").first()
    if row is None: raise HTTPException(404,"Notification not found")
    row.read_at=row.read_at or datetime.now(timezone.utc); db.commit(); return {"read":True}

@router.patch("/read-all")
def mark_admin_all(user=Depends(require_admin("notifications.read")), db: Session=Depends(get_db)):
    account=db.query(User).filter_by(firebase_uid=user.firebase_uid).first()
    n=db.query(Notification).filter_by(recipient_user_id=account.id if account else "",category="admin",read_at=None).update({Notification.read_at:datetime.now(timezone.utc)},synchronize_session=False); db.commit(); return {"updated":n}
