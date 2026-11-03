"""Durable notification queue worker. Run separately: python -m services.notification_dispatcher."""
from __future__ import annotations

import logging
import os
import random
import signal
import socket
import time
from datetime import datetime, timedelta, timezone

from database import SessionLocal
from models import Notification, NotificationDeliveryAttempt, NotificationDevice, NotificationOutbox
from services.fcm_provider import send_to_device
from services.notification_service import decrypt_token, push_is_allowed
from services.notification_service import queue_admin_notifications

logger = logging.getLogger("errno.notifications.worker")
STOP = False


def _stop(*_):
    global STOP
    STOP = True


def dispatch_one(db, *, owner: str | None = None, sender=send_to_device) -> bool:
    now = datetime.now(timezone.utc)
    owner = owner or socket.gethostname()[:50]
    lease_seconds = int(os.getenv("NOTIFICATION_LEASE_SECONDS", "120"))
    row = db.query(NotificationOutbox).filter(
        ((NotificationOutbox.status == "queued") | (NotificationOutbox.status == "retrying") |
         ((NotificationOutbox.status == "sending") & (NotificationOutbox.lease_until < now))),
        NotificationOutbox.next_attempt_at <= now,
    ).order_by(NotificationOutbox.created_at).with_for_update(skip_locked=True).first()
    if row is None:
        return False
    row.status, row.lease_owner, row.lease_until = "sending", owner, now + timedelta(seconds=lease_seconds)
    row.attempts += 1
    db.commit()  # Lease commits before any network call; abandoned leases are reclaimable.
    notification = db.query(Notification).filter_by(id=row.notification_id).first()
    if notification is None:
        row.status, row.processed_at = "permanently_failed", now
        row.last_error_code = "NOTIFICATION_MISSING"
        db.commit()
        return True
    expires = notification.expires_at
    if expires is not None:
        expires = expires.replace(tzinfo=timezone.utc) if expires.tzinfo is None else expires
        if expires <= now:
            row.status, row.processed_at, row.lease_owner, row.lease_until = "expired", now, None, None
            db.commit()
            return True
    devices = db.query(NotificationDevice).filter_by(user_id=row.recipient_user_id, active=True).all()
    if not push_is_allowed(db, row.recipient_user_id, notification.category, notification.event_type):
        row.status, row.processed_at, row.lease_owner, row.lease_until = "suppressed", now, None, None
        db.commit()
        return True
    if not devices:
        row.status, row.processed_at, row.lease_owner, row.lease_until = "no_devices", now, None, None
        db.commit()
        return True
    already_accepted = {device_id for (device_id,) in db.query(NotificationDeliveryAttempt.device_id).filter(
        NotificationDeliveryAttempt.notification_id == notification.id,
        NotificationDeliveryAttempt.status == "accepted_by_fcm",
        NotificationDeliveryAttempt.device_id.is_not(None),
    ).all()}
    devices = [device for device in devices if device.id not in already_accepted]
    if not devices:
        row.status, row.processed_at, row.lease_owner, row.lease_until = "accepted_by_fcm", now, None, None
        db.commit()
        return True
    max_attempts = max(1, int(os.getenv("NOTIFICATION_MAX_ATTEMPTS", "6")))
    base = max(1, int(os.getenv("NOTIFICATION_RETRY_BASE_SECONDS", "15")))
    cap = max(base, int(os.getenv("NOTIFICATION_RETRY_MAX_SECONDS", "3600")))
    results = []
    for device in devices:
        try:
            result = sender(device, row.payload)
        except Exception as exc:  # The worker itself must remain alive on provider errors.
            logger.exception("notification_provider_exception outbox_id=%s", row.id)
            from services.fcm_provider import PushResult
            result = PushResult(False, error_code=type(exc).__name__.upper()[:80], retryable=True)
        attempt = NotificationDeliveryAttempt(
            notification_id=notification.id, device_id=device.id,
            attempt_number=(db.query(NotificationDeliveryAttempt.attempt_number).filter_by(
                notification_id=notification.id, device_id=device.id).order_by(
                    NotificationDeliveryAttempt.attempt_number.desc()).limit(1).scalar() or 0) + 1,
            provider_message_id=result.provider_message_id if result.accepted else None,
            status="accepted_by_fcm" if result.accepted else ("invalid_token" if result.invalid_token else "failed"),
            error_code=result.error_code,
        )
        db.add(attempt)
        results.append(result)
        if result.invalid_token:
            device.active = False
            device.invalidated_at = now
    accepted = any(result.accepted for result in results)
    retryable = any(result.retryable for result in results)
    all_devices_accepted = accepted and all(
        result.accepted or device.id in already_accepted
        for device, result in zip(devices, results)
    )
    if all_devices_accepted:
        row.status, row.processed_at, row.last_error_code = "accepted_by_fcm", now, None
    elif retryable and row.attempts < max_attempts:
        delay = min(cap, base * 2 ** (row.attempts - 1))
        row.status, row.next_attempt_at = "retrying", now + timedelta(seconds=random.uniform(delay * .75, delay * 1.25))
        row.last_error_code = next((r.error_code for r in results if r.error_code), "PROVIDER_UNAVAILABLE")
        for attempt in db.query(NotificationDeliveryAttempt).filter_by(notification_id=notification.id, attempt_number=row.attempts):
            attempt.next_retry_at = row.next_attempt_at
    elif accepted:
        row.status, row.processed_at = "permanently_failed", now
        row.last_error_code = "PARTIAL_DEVICE_FAILURE"
    else:
        row.status, row.processed_at = "permanently_failed", now
        row.last_error_code = next((r.error_code for r in results if r.error_code), "NO_ACTIVE_DEVICE")
        if row.attempts >= max_attempts and notification.category != "admin":
            queue_admin_notifications(db, permission="notifications.audit", event_type="notification_delivery_failures",
                title="Notification delivery failures", body="A notification exceeded the configured delivery retry limit.",
                data={"route":"notifications","notification_id":notification.id}, event_id=f"notification-failure:{row.id}")
    row.lease_owner, row.lease_until = None, None
    db.commit()
    logger.info("notification_dispatch outbox_id=%s status=%s attempts=%s", row.id, row.status, row.attempts)
    return True


def run_forever() -> None:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    if os.getenv("NOTIFICATION_WORKER_ENABLED", "true").strip().lower() not in {"1", "true", "yes", "on"}:
        logger.warning("notification_worker_disabled")
        return
    poll = max(.2, float(os.getenv("NOTIFICATION_WORKER_POLL_SECONDS", "2")))
    cleanup_after = 0.0
    while not STOP:
        db = SessionLocal()
        try:
            worked = dispatch_one(db)
            if time.monotonic() >= cleanup_after:
                cleanup_retained_records(db)
                cleanup_after = time.monotonic() + 6 * 60 * 60
        except Exception:
            db.rollback()
            logger.exception("notification_worker_iteration_failed")
            worked = False
        finally:
            db.close()
        if not worked:
            time.sleep(poll)


def cleanup_retained_records(db) -> tuple[int, int]:
    """Delete old delivery logs and inbox/outbox rows using configurable retention."""
    now = datetime.now(timezone.utc)
    attempt_days = max(1, int(os.getenv("NOTIFICATION_DELIVERY_LOG_RETENTION_DAYS", "180")))
    inbox_days = max(1, int(os.getenv("NOTIFICATION_RETENTION_DAYS", "365")))
    attempt_cutoff = now - timedelta(days=attempt_days)
    inbox_cutoff = now - timedelta(days=inbox_days)
    attempts = db.query(NotificationDeliveryAttempt).filter(NotificationDeliveryAttempt.attempted_at < attempt_cutoff).delete(synchronize_session=False)
    old_ids = db.query(Notification.id).filter(Notification.created_at < inbox_cutoff).subquery()
    db.query(NotificationDeliveryAttempt).filter(NotificationDeliveryAttempt.notification_id.in_(old_ids)).delete(synchronize_session=False)
    db.query(NotificationOutbox).filter(NotificationOutbox.notification_id.in_(old_ids)).delete(synchronize_session=False)
    notifications = db.query(Notification).filter(Notification.id.in_(old_ids)).delete(synchronize_session=False)
    db.commit()
    logger.info("notification_retention_cleanup attempts=%s notifications=%s", attempts, notifications)
    return attempts, notifications


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    run_forever()
