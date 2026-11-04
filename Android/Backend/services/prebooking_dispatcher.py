"""Durable dispatcher for pre-bookings. Run with ``python -m services.prebooking_dispatcher``."""
from __future__ import annotations

import hashlib
import logging
import math
import os
import signal
import socket
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_

from database import SessionLocal
from models import Job, PresenceSession, User, WorkerLocation, WorkerProfilePreferences
from services.notification_service import queue_notification

logger = logging.getLogger("errno.prebooking.dispatcher")
STOP = False
DISPATCH_LEAD = timedelta(hours=4)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _stop(*_):
    global STOP
    STOP = True


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def eligible_workers(db, job: Job, now: datetime) -> list[User]:
    """Resolve active, present workers at dispatch time; location is fresh and bounded when available."""
    rows = db.query(User, PresenceSession).join(
        PresenceSession, PresenceSession.user_id == User.id
    ).filter(
        User.role == "worker", User.is_active.is_(True),
        PresenceSession.expires_at > now,
        PresenceSession.availability_status == "available",
        PresenceSession.is_foreground.is_(True),
    ).all()
    radius = max(0.1, float(os.getenv("PREBOOKING_WORKER_RADIUS_KM", "5")))
    freshness = max(30, int(os.getenv("PREBOOKING_LOCATION_MAX_AGE_SECONDS", "300")))
    result: dict[str, User] = {}
    for worker, _session in rows:
        preferences = db.query(WorkerProfilePreferences).filter_by(user_id=worker.id).first()
        skills = preferences.preferred_skills if preferences else []
        if skills and job.category and job.category.casefold() not in {str(skill).casefold() for skill in skills}:
            continue
        if job.latitude is not None and job.longitude is not None:
            location = db.query(WorkerLocation).filter_by(user_id=worker.id).first()
            updated = _aware(location.updated_at) if location else None
            if location is None or updated is None or now - updated > timedelta(seconds=freshness):
                continue
            if _distance_km(job.latitude, job.longitude, location.latitude, location.longitude) > radius:
                continue
        result[worker.id] = worker
    return list(result.values())


def dispatch_locked_job(db, job: Job, now: datetime) -> int:
    """Queue idempotent worker invitations and mark dispatch. Caller owns the job row lock."""
    now = _aware(now) or utc_now()
    scheduled = _aware(job.scheduled_at)
    dispatch_at = _aware(job.dispatch_at)
    if (job.booking_type != "PRE_BOOKING" or job.status != "open"
            or job.prebooking_dispatch_status == "CANCELLED"):
        return 0
    if job.prebooking_dispatch_status == "DISPATCHED":
        return job.prebooking_dispatch_worker_count or 0
    if scheduled is None or scheduled <= now:
        job.prebooking_dispatch_status = "FAILED"
        job.prebooking_dispatch_failure_code = "SCHEDULE_PASSED"
        job.prebooking_dispatch_failure_detail = "The scheduled start time has passed; no worker request was sent."
        job.prebooking_dispatch_completed_at = now
        job.prebooking_dispatch_lease_owner = None
        job.prebooking_dispatch_lease_until = None
        return 0
    if dispatch_at is None or dispatch_at > now:
        return 0

    workers = eligible_workers(db, job, now)
    job.prebooking_dispatch_worker_count = len(workers)
    job.prebooking_dispatch_lease_owner = None
    job.prebooking_dispatch_lease_until = None
    job.prebooking_dispatch_failure_code = None
    job.prebooking_dispatch_failure_detail = None
    if not workers:
        retry = now + timedelta(seconds=max(30, int(os.getenv("PREBOOKING_NO_WORKER_RETRY_SECONDS", "300"))))
        job.prebooking_dispatch_status = "NO_ELIGIBLE_WORKERS"
        job.prebooking_dispatch_failure_code = "NO_ELIGIBLE_WORKERS"
        job.prebooking_dispatch_failure_detail = "No eligible available workers matched at this dispatch attempt."
        job.prebooking_next_attempt_at = min(retry, scheduled - timedelta(seconds=1))
        job.prebooking_dispatch_completed_at = now
        return 0

    for worker in workers:
        digest = hashlib.sha256(f"{job.id}:{job.prebooking_schedule_version}:{worker.id}".encode()).hexdigest()[:48]
        queue_notification(
            db, recipient=worker, event_type="prebooking_worker_request", category="booking",
            title="New scheduled booking nearby",
            body=f"A shopkeeper needs a worker for {job.scheduled_date or 'a scheduled booking'}. Open ERRNO to review and apply.",
            data={"route": "job", "job_id": job.id},
            event_id=f"prebook:{digest}",
            deduplication_key=f"prebook:{job.id}:{job.prebooking_schedule_version}:{worker.id}",
            expires_at=scheduled,
        )
    job.prebooking_dispatch_status = "DISPATCHED"
    job.prebooking_dispatch_completed_at = now
    job.prebooking_next_attempt_at = None
    return len(workers)


def dispatch_immediately_or_retry(db, job: Job, now: datetime) -> None:
    """Run late-booking dispatch atomically while retaining the booking on transient errors."""
    try:
        with db.begin_nested():
            dispatch_locked_job(db, job, now)
    except Exception as exc:
        job.prebooking_dispatch_status = "FAILED_RETRYABLE"
        job.prebooking_next_attempt_at = now + timedelta(seconds=15)
        job.prebooking_dispatch_failure_code = type(exc).__name__[:80]
        job.prebooking_dispatch_failure_detail = str(exc)[:500]
        job.prebooking_dispatch_lease_owner = None
        job.prebooking_dispatch_lease_until = None


def dispatch_due_once(*, owner: str | None = None, now: datetime | None = None) -> bool:
    """Claim one due row with SKIP LOCKED, then process under a second lock/transaction."""
    now = _aware(now) or utc_now()
    owner = owner or f"{socket.gethostname()}:{os.getpid()}"
    lease_seconds = max(10, int(os.getenv("PREBOOKING_DISPATCH_LEASE_SECONDS", "120")))
    with SessionLocal() as db:
        row = db.query(Job).filter(
            Job.booking_type == "PRE_BOOKING", Job.status == "open",
            or_(
                ((Job.prebooking_dispatch_status.in_(["SCHEDULED", "FAILED_RETRYABLE", "NO_ELIGIBLE_WORKERS"])) &
                 (or_(Job.prebooking_next_attempt_at.is_(None), Job.prebooking_next_attempt_at <= now))),
                ((Job.prebooking_dispatch_status == "DISPATCHING") & (Job.prebooking_dispatch_lease_until < now)),
            ),
            Job.dispatch_at <= now, Job.scheduled_at > now,
        ).order_by(Job.dispatch_at, Job.created_at).with_for_update(skip_locked=True).first()
        if row is None:
            expired = db.query(Job).filter(
                Job.booking_type == "PRE_BOOKING", Job.status == "open",
                Job.scheduled_at <= now,
                Job.prebooking_dispatch_status.in_(["SCHEDULED", "DISPATCHING", "NO_ELIGIBLE_WORKERS", "FAILED_RETRYABLE"]),
            ).order_by(Job.scheduled_at, Job.created_at).with_for_update(skip_locked=True).first()
            if expired is None:
                db.rollback()
                return False
            expired.prebooking_dispatch_status = "FAILED"
            expired.prebooking_dispatch_failure_code = "BOOKING_TIME_PASSED"
            expired.prebooking_dispatch_failure_detail = "The scheduled start time passed before worker invitations could be queued."
            expired.prebooking_dispatch_completed_at = now
            expired.prebooking_dispatch_lease_owner = None
            expired.prebooking_dispatch_lease_until = None
            expired.prebooking_next_attempt_at = None
            db.commit()
            logger.warning("prebooking_expired job_id=%s", expired.id)
            return True
        generation = row.prebooking_schedule_version
        row.prebooking_dispatch_status = "DISPATCHING"
        row.prebooking_dispatch_attempts = (row.prebooking_dispatch_attempts or 0) + 1
        row.prebooking_dispatch_started_at = now
        row.prebooking_dispatch_lease_owner = owner
        row.prebooking_dispatch_lease_until = now + timedelta(seconds=lease_seconds)
        job_id = row.id
        db.commit()

    with SessionLocal() as db:
        row = db.query(Job).filter(Job.id == job_id).with_for_update().first()
        if row is None or row.prebooking_schedule_version != generation or row.status != "open" or row.prebooking_dispatch_status != "DISPATCHING" or row.prebooking_dispatch_lease_owner != owner:
            db.rollback()
            return True
        try:
            dispatch_locked_job(db, row, now)
            db.commit()
            logger.info("prebooking_dispatch job_id=%s generation=%s status=%s workers=%s", row.id, generation, row.prebooking_dispatch_status, row.prebooking_dispatch_worker_count)
        except Exception as exc:
            db.rollback()
            with SessionLocal() as error_db:
                failed = error_db.query(Job).filter(Job.id == job_id).with_for_update().first()
                if failed is not None and failed.prebooking_schedule_version == generation and failed.status == "open":
                    attempts = max(1, failed.prebooking_dispatch_attempts or 1)
                    delay = min(1800, 15 * (2 ** min(attempts - 1, 7)))
                    failed.prebooking_dispatch_status = "FAILED_RETRYABLE"
                    failed.prebooking_next_attempt_at = now + timedelta(seconds=delay)
                    failed.prebooking_dispatch_failure_code = type(exc).__name__[:80]
                    failed.prebooking_dispatch_failure_detail = str(exc)[:500]
                    failed.prebooking_dispatch_lease_owner = None
                    failed.prebooking_dispatch_lease_until = None
                    error_db.commit()
            logger.exception("prebooking_dispatch_failed job_id=%s generation=%s", job_id, generation)
    return True


def run_forever() -> None:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    poll = max(0.2, float(os.getenv("PREBOOKING_DISPATCH_POLL_SECONDS", "1")))
    while not STOP:
        worked = False
        try:
            worked = dispatch_due_once()
        except Exception:
            logger.exception("prebooking_dispatch_loop_error")
        if not worked:
            time.sleep(poll)


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    run_forever()
