import base64
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from database import get_db
from firebase_auth import authenticated_user
from models import Notification, NotificationPreference
from services.notification_service import preferences_for

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])

def _cursor(value):
    if not value: return None
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode()
        ts, ident = raw.split("|", 1)
        return datetime.fromisoformat(ts), ident
    except Exception: raise HTTPException(422, "Invalid cursor")

def _encode(row):
    raw = f"{row.created_at.isoformat()}|{row.id}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")

@router.get("")
def list_notifications(cursor: str | None = None, limit: int = Query(30, ge=1, le=100), category: str | None = None,
                      unread: bool | None = None, user=Depends(authenticated_user), db: Session=Depends(get_db)):
    q = db.query(Notification).filter(Notification.recipient_user_id == user.id)
    q = q.filter(or_(Notification.expires_at.is_(None), Notification.expires_at > datetime.now(timezone.utc)))
    if category: q = q.filter(Notification.category == category)
    if unread is True: q = q.filter(Notification.read_at.is_(None))
    elif unread is False: q = q.filter(Notification.read_at.is_not(None))
    pos = _cursor(cursor)
    if pos:
        ts, ident = pos
        q = q.filter(or_(Notification.created_at < ts, and_(Notification.created_at == ts, Notification.id < ident)))
    rows = q.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit + 1).all()
    more = len(rows) > limit
    rows = rows[:limit]
    return {"items": [{"id":r.id,"eventType":r.event_type,"title":r.title,"body":r.body,"category":r.category,
        "priority":r.priority,"data":r.data_payload,"createdAt":r.created_at,"readAt":r.read_at} for r in rows],
        "nextCursor": _encode(rows[-1]) if more and rows else None}

@router.get("/unread-count")
def unread_count(user=Depends(authenticated_user), db: Session=Depends(get_db)):
    now=datetime.now(timezone.utc)
    return {"count": db.query(Notification).filter(Notification.recipient_user_id==user.id, Notification.read_at.is_(None),
        or_(Notification.expires_at.is_(None),Notification.expires_at>now)).count()}

@router.patch("/read-all")
def read_all(user=Depends(authenticated_user), db: Session=Depends(get_db)):
    now = datetime.now(timezone.utc)
    count = db.query(Notification).filter_by(recipient_user_id=user.id, read_at=None).update({Notification.read_at: now}, synchronize_session=False)
    db.commit(); return {"updated": count}

@router.patch("/{notification_id}/read")
def read_one(notification_id: str, user=Depends(authenticated_user), db: Session=Depends(get_db)):
    row = db.query(Notification).filter_by(id=notification_id, recipient_user_id=user.id).first()
    if row is None: raise HTTPException(404, "Notification not found")
    row.read_at = row.read_at or datetime.now(timezone.utc); db.commit(); return {"readAt": row.read_at}

@router.delete("/{notification_id}", status_code=204)
def delete_one(notification_id: str, user=Depends(authenticated_user), db: Session=Depends(get_db)):
    row = db.query(Notification).filter_by(id=notification_id, recipient_user_id=user.id).first()
    if row is None: raise HTTPException(404, "Notification not found")
    db.delete(row); db.commit()

@router.get("/preferences")
def get_preferences(user=Depends(authenticated_user), db: Session=Depends(get_db)):
    row = preferences_for(db, user.id); db.commit()
    return {key:getattr(row,key) for key in ("booking_updates_enabled","job_alerts_enabled","payment_updates_enabled","account_updates_enabled","marketing_enabled")}

class PreferencesPatch(BaseModel):
    booking_updates_enabled: bool | None = None
    job_alerts_enabled: bool | None = None
    payment_updates_enabled: bool | None = None
    account_updates_enabled: bool | None = None
    marketing_enabled: bool | None = None

@router.patch("/preferences")
def patch_preferences(body: PreferencesPatch, user=Depends(authenticated_user), db: Session=Depends(get_db)):
    row = preferences_for(db, user.id)
    for key,value in body.model_dump(exclude_unset=True).items():
        if value is None: raise HTTPException(422, "Preference values cannot be null")
        setattr(row,key,value)
    row.updated_at = datetime.now(timezone.utc); db.commit()
    return {key:getattr(row,key) for key in ("booking_updates_enabled","job_alerts_enabled","payment_updates_enabled","account_updates_enabled","marketing_enabled")}
