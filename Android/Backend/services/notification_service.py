"""Durable, transactional notification inbox and outbox primitives.

This module never contacts FCM. Callers add rows to the caller's SQLAlchemy
transaction so a notification cannot precede an uncommitted business change.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import (AdminAuditLog, AdminPermission, Notification,
                    NotificationDevice, NotificationOutbox,
                    NotificationPreference, NotificationRegistrationThrottle, User)

MAX_PAYLOAD_BYTES = 4096
VALID_CATEGORIES = {"booking", "job", "payment", "account", "verification", "marketing", "admin"}
PREFERENCE_FIELD = {
    "booking": "booking_updates_enabled",
    "payment": "payment_updates_enabled",
    "account": "account_updates_enabled",
    "verification": "account_updates_enabled",
    "marketing": "marketing_enabled",
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _fernet() -> Fernet:
    key = os.getenv("NOTIFICATION_TOKEN_ENCRYPTION_KEY", "").strip().encode()
    if not key:
        raise HTTPException(503, detail="Device token protection is not configured")
    try:
        return Fernet(key)
    except Exception:
        raise HTTPException(503, detail="Device token protection is not configured") from None


def token_hash(token: str) -> str:
    secret = os.getenv("NOTIFICATION_TOKEN_HASH_SECRET", "").encode()
    if len(secret) < 32:
        raise HTTPException(503, detail="Device token lookup is not configured")
    return hmac.new(secret, token.encode(), hashlib.sha256).hexdigest()


def encrypt_token(token: str) -> str:
    return _fernet().encrypt(token.encode()).decode()


def decrypt_token(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, UnicodeDecodeError):
        raise ValueError("Stored device token could not be decrypted") from None


def sanitize_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Allow routing identifiers only; never put auth or personal data in push."""
    if not payload:
        return {}
    allowed_keys = {"route", "job_id", "booking_id", "payment_id", "kyc_profile_id", "notification_id", "event_id"}
    cleaned: dict[str, Any] = {}
    for key, value in payload.items():
        if key not in allowed_keys or value is None:
            continue
        text = str(value)
        if len(text) > 160 or any(ch in text for ch in "\r\n\x00"):
            continue
        cleaned[key] = text
    if len(json.dumps(cleaned, separators=(",", ":")).encode()) > MAX_PAYLOAD_BYTES:
        raise ValueError("Notification routing payload is too large")
    return cleaned


def queue_notification(
    db: Session,
    *,
    recipient: User,
    event_type: str,
    category: str,
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
    priority: str = "normal",
    event_id: str | None = None,
    deduplication_key: str | None = None,
    expires_at: datetime | None = None,
) -> Notification | None:
    """Persist inbox + dispatch work in the active business transaction."""
    # In-app transactional records remain durable even when push is disabled. The
    # dispatcher separately respects NOTIFICATION_WORKER_ENABLED / push settings.
    if category not in VALID_CATEGORIES:
        raise ValueError("Unsupported notification category")
    routing = sanitize_payload(data)
    event_id = event_id or str(uuid.uuid4())
    deduplication_key = deduplication_key or f"{event_id}:{recipient.id}:{event_type}"
    existing = db.query(Notification).filter(Notification.deduplication_key == deduplication_key).first()
    if existing is not None:
        return existing

    notification = Notification(
        recipient_user_id=recipient.id,
        recipient_role="admin" if category == "admin" else (recipient.role or "unknown"),
        event_id=event_id,
        event_type=event_type,
        title=title[:180],
        body=body[:500],
        priority=priority if priority in {"low", "normal", "high"} else "normal",
        category=category,
        data_payload=routing,
        deduplication_key=deduplication_key[:300],
        expires_at=expires_at,
    )
    db.add(notification)
    db.flush()
    db.add(NotificationOutbox(
        notification_id=notification.id,
        event_id=event_id,
        event_type=event_type,
        recipient_user_id=recipient.id,
        payload={
            "notification_id": notification.id,
            "title": notification.title,
            "body": notification.body,
            "category": notification.category,
            "priority": notification.priority,
            "data": routing,
        },
        status="queued",
        next_attempt_at=utcnow(),
    ))
    return notification


def queue_admin_notifications(
    db: Session, *, permission: str, event_type: str, title: str, body: str,
    data: dict[str, Any], event_id: str,
) -> int:
    """Resolve only active admins who explicitly have notifications.read."""
    admins = db.query(User).join(AdminPermission, AdminPermission.firebase_uid == User.firebase_uid).filter(
        AdminPermission.active.is_(True), User.is_active.is_(True),
    ).all()
    count = 0
    for admin in admins:
        permission_row = db.query(AdminPermission).filter(
            AdminPermission.firebase_uid == admin.firebase_uid,
            AdminPermission.active.is_(True),
        ).first()
        if permission_row and permission in (permission_row.permissions or []) and "notifications.read" in (permission_row.permissions or []):
            result = queue_notification(
                db, recipient=admin, event_type=event_type, category="admin", title=title, body=body,
                data=data, priority="high", event_id=event_id,
                deduplication_key=f"{event_id}:{admin.id}:{event_type}",
            )
            count += result is not None
    return count


def record_admin_retry(db: Session, *, admin_uid: str, outbox_id: str) -> None:
    db.add(AdminAuditLog(
        administrator_uid=admin_uid,
        action="notifications.delivery_retry",
        resource_type="notification_outbox",
        resource_id=outbox_id,
        outcome="success",
        change_metadata={"operation": "manual_retry"},
    ))


def register_device(
    db: Session, *, user: User, platform: str, device_identifier: str,
    fcm_token: str, app_version: str | None,
) -> NotificationDevice:
    if platform not in {"android", "ios"}:
        raise HTTPException(422, detail="Unsupported device platform")
    if not device_identifier or len(device_identifier) > 160:
        raise HTTPException(422, detail="Invalid device identifier")
    if not fcm_token or len(fcm_token) > 4096 or len(fcm_token) < 20 or any(ch.isspace() for ch in fcm_token):
        raise HTTPException(422, detail="Invalid push token")
    digest = token_hash(fcm_token)
    now = utcnow()
    row = db.query(NotificationDevice).filter(NotificationDevice.token_hash == digest).with_for_update().first()
    by_installation = db.query(NotificationDevice).filter(
        NotificationDevice.user_id == user.id,
        NotificationDevice.device_identifier == device_identifier,
    ).with_for_update().first()
    if row and by_installation and row.id != by_installation.id:
        # This install rotated to a new token; retire its old token row first.
        by_installation.active = False
        by_installation.invalidated_at = now
        by_installation = None
    row = row or by_installation
    if row is None:
        active_count = db.query(NotificationDevice).filter(
            NotificationDevice.user_id == user.id,
            NotificationDevice.active.is_(True),
        ).count()
        if active_count >= 20:
            raise HTTPException(429, detail="Device registration limit reached")
        row = NotificationDevice(user_id=user.id, device_identifier=device_identifier, token_hash=digest)
        db.add(row)
    row.user_id = user.id  # A token transferred to another authenticated account is reassigned.
    row.role = user.role or "unknown"
    row.platform = platform
    row.device_identifier = device_identifier
    row.token_hash = digest
    row.encrypted_token = encrypt_token(fcm_token)
    row.app_version = app_version[:40] if app_version else None
    row.active = True
    row.invalidated_at = None
    row.last_seen_at = now
    row.updated_at = now
    db.flush()
    return row


def enforce_registration_rate_limit(db: Session, user_id: str, *, limit: int = 30) -> None:
    now = utcnow()
    row = db.query(NotificationRegistrationThrottle).filter_by(user_id=user_id).with_for_update().first()
    if row is None:
        row = NotificationRegistrationThrottle(user_id=user_id, window_started_at=now, attempts=0)
        db.add(row)
        db.flush()
    start = row.window_started_at
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if now - start >= timedelta(minutes=1):
        row.window_started_at, row.attempts = now, 0
    if row.attempts >= limit:
        raise HTTPException(429, detail="Device registration rate limit exceeded")
    row.attempts += 1


def preferences_for(db: Session, user_id: str) -> NotificationPreference:
    row = db.query(NotificationPreference).filter_by(user_id=user_id).first()
    if row is None:
        row = NotificationPreference(user_id=user_id)
        db.add(row)
        db.flush()
    return row


def push_is_allowed(db: Session, user_id: str, category: str, event_type: str | None = None) -> bool:
    field = "job_alerts_enabled" if event_type == "job_recommendation" else PREFERENCE_FIELD.get(category)
    if field is None:
        return True
    row = db.query(NotificationPreference).filter_by(user_id=user_id).first()
    if row is None:
        return category != "marketing"
    return bool(getattr(row, field))


def role_for_user(user: User) -> str:
    return user.role or "unknown"
