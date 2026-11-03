"""Server-authorized Admin API over the canonical ERRNO data model."""
from datetime import datetime, timedelta, timezone
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from database import get_db
from firebase_auth import require_admin
from models import AdminAuditLog, AdminPermission, Application, Job, Shop, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


class UserActivePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_active: bool


class JobStatusPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Admins may cancel an unstarted job. Assignment, start, and completion are
    # performed only by the applicant decision, assigned worker, and owner.
    status: Literal["cancelled"]


def _user_summary(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.full_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at,
    }


def _job_summary(job: Job, shop: Shop | None = None) -> dict:
    owner = shop.owner if shop else None
    return {
        "id": job.id,
        "title": job.title,
        "status": job.status,
        "category": job.category,
        "pay_amount": job.pay_amount,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "cancelled_at": job.cancelled_at,
        "shop_id": job.shop_id,
        "shop_name": shop.shop_name if shop else None,
        "owner_id": owner.id if owner else None,
        "owner_name": owner.full_name if owner else None,
    }


def _page(items: list, total: int, limit: int, offset: int) -> dict:
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def _audit(db: Session, admin: AdminPermission, action: str, resource_type: str,
           resource_id: str | None, metadata: dict | None = None) -> None:
    db.add(AdminAuditLog(
        administrator_uid=admin.firebase_uid,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome="success",
        change_metadata=metadata or {},
    ))


def _write_failure_log(action: str, resource_type: str, resource_id: str | None, reason: str) -> None:
    # Rejected requests are logged to server diagnostics without copying PII or tokens
    # into the durable mutation audit trail.
    logger.warning("admin_action_rejected action=%s resource_type=%s resource_id=%s reason=%s",
                   action, resource_type, resource_id, reason)


@router.get("/me")
def admin_me(admin: AdminPermission = Depends(require_admin())):
    return {
        "id": admin.id,
        "firebase_uid": admin.firebase_uid,
        "email": admin.email,
        "permissions": admin.permissions or [],
        "active": admin.active,
    }


@router.get("/dashboard")
def dashboard(
    _: AdminPermission = Depends(require_admin("dashboard.read")),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=6)
    total_users = db.query(func.count(User.id)).scalar() or 0
    workers = db.query(func.count(User.id)).filter(User.role == "worker").scalar() or 0
    owners = db.query(func.count(User.id)).filter(User.role.in_(("shop_owner", "shopkeeper"))).scalar() or 0
    total_jobs = db.query(func.count(Job.id)).scalar() or 0
    active_jobs = db.query(func.count(Job.id)).filter(
        Job.status.in_(("open", "assigned", "in_progress", "inProgress")),
    ).scalar() or 0
    completed_jobs = db.query(func.count(Job.id)).filter(Job.status == "completed").scalar() or 0

    registrations = db.query(User).order_by(User.created_at.desc()).limit(8).all()
    recent_jobs = db.query(Job).order_by(Job.created_at.desc()).limit(8).all()

    def daily_counts(model):
        rows = db.query(func.date(model.created_at), func.count(model.id)).filter(
            model.created_at >= since,
        ).group_by(func.date(model.created_at)).all()
        counts = {str(day): count for day, count in rows}
        return [
            {"date": (since.date() + timedelta(days=offset)).isoformat(),
             "total": counts.get((since.date() + timedelta(days=offset)).isoformat(), 0)}
            for offset in range(7)
        ]

    return {
        "metrics": {
            "total_users": total_users,
            "total_workers": workers,
            "total_shop_owners": owners,
            "total_shops": db.query(func.count(Shop.id)).scalar() or 0,
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "completed_jobs": completed_jobs,
            "total_applications": db.query(func.count(Application.id)).scalar() or 0,
        },
        "recent_registrations": [_user_summary(user) for user in registrations],
        "recent_jobs": [_job_summary(job, job.shop) for job in recent_jobs],
        "registrations_by_day": daily_counts(User),
        "jobs_by_day": daily_counts(Job),
    }


def _user_listing(role: str, q: str | None, active: bool | None, limit: int, offset: int,
                 db: Session, include_shop_counts: bool = False) -> dict:
    query = db.query(User).filter(User.role == role if role == "worker" else User.role.in_(("shop_owner", "shopkeeper")))
    if active is not None:
        query = query.filter(User.is_active.is_(active))
    if q:
        match = f"%{q.strip()}%"
        query = query.filter(or_(User.full_name.ilike(match), User.email.ilike(match), User.phone_number.ilike(match)))
    total = query.count()
    if include_shop_counts:
        shop_count = select(func.count(Shop.id)).where(Shop.owner_id == User.id).correlate(User).scalar_subquery()
        job_count = select(func.count(Job.id)).join(Shop, Job.shop_id == Shop.id).where(Shop.owner_id == User.id).correlate(User).scalar_subquery()
        rows = query.with_entities(User, shop_count.label("shop_count"), job_count.label("job_count"))\
            .order_by(User.created_at.desc(), User.id).offset(offset).limit(limit).all()
    else:
        application_count = select(func.count(Application.id)).where(Application.worker_id == User.id).correlate(User).scalar_subquery()
        rows = query.with_entities(User, application_count.label("application_count"))\
            .order_by(User.created_at.desc(), User.id).offset(offset).limit(limit).all()
    items = []
    for row in rows:
        user = row[0]
        item = _user_summary(user)
        if include_shop_counts:
            item["shop_count"] = row.shop_count
            item["job_count"] = row.job_count
        else:
            item["application_count"] = row.application_count
        items.append(item)
    return _page(items, total, limit, offset)


@router.get("/shop-owners")
def list_shop_owners(
    q: str | None = Query(default=None, max_length=120),
    active: bool | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: AdminPermission = Depends(require_admin("users.read")),
    db: Session = Depends(get_db),
):
    return _user_listing("shop_owner", q, active, limit, offset, db, include_shop_counts=True)


@router.get("/shop-owners/{user_id}")
def get_shop_owner(user_id: str, _: AdminPermission = Depends(require_admin("users.read")), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id, User.role.in_(("shop_owner", "shopkeeper"))).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Shop owner not found")
    shops = db.query(Shop).filter(Shop.owner_id == user.id).order_by(Shop.created_at.desc()).all()
    shop_ids = [shop.id for shop in shops]
    jobs = db.query(Job).filter(Job.shop_id.in_(shop_ids)).order_by(Job.created_at.desc()).limit(100).all() if shop_ids else []
    return {
        "user": _user_summary(user),
        "shops": [{"id": shop.id, "shop_name": shop.shop_name, "address": shop.address,
                   "category": shop.category, "created_at": shop.created_at} for shop in shops],
        "jobs": [_job_summary(job, job.shop) for job in jobs],
        "jobs_truncated": len(jobs) == 100,
    }


@router.patch("/shop-owners/{user_id}")
def patch_shop_owner(user_id: str, body: UserActivePatch,
                     admin: AdminPermission = Depends(require_admin("users.manage")),
                     db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id, User.role.in_(("shop_owner", "shopkeeper"))).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Shop owner not found")
    previous = user.is_active
    user.is_active = body.is_active
    _audit(db, admin, "shop_owner.account_status_changed", "user", user.id,
           {"is_active": {"from": previous, "to": user.is_active}})
    db.commit()
    db.refresh(user)
    return _user_summary(user)


@router.get("/workers")
def list_workers(
    q: str | None = Query(default=None, max_length=120),
    active: bool | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: AdminPermission = Depends(require_admin("users.read")),
    db: Session = Depends(get_db),
):
    return _user_listing("worker", q, active, limit, offset, db)


@router.get("/workers/{user_id}")
def get_worker(user_id: str, limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0),
               _: AdminPermission = Depends(require_admin("users.read")), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id, User.role == "worker").first()
    if user is None:
        raise HTTPException(status_code=404, detail="Worker not found")
    query = db.query(Application, Job).join(Job, Application.job_id == Job.id).filter(Application.worker_id == user.id)
    total = query.count()
    applications = query.order_by(Application.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "user": _user_summary(user),
        "applications": [{"id": app.id, "job_id": job.id, "job_title": job.title,
                           "job_status": job.status, "status": app.status, "created_at": app.created_at}
                          for app, job in applications],
        "total_applications": total,
        "limit": limit,
        "offset": offset,
    }


@router.patch("/workers/{user_id}")
def patch_worker(user_id: str, body: UserActivePatch,
                 admin: AdminPermission = Depends(require_admin("users.manage")), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id, User.role == "worker").first()
    if user is None:
        raise HTTPException(status_code=404, detail="Worker not found")
    previous = user.is_active
    user.is_active = body.is_active
    _audit(db, admin, "worker.account_status_changed", "user", user.id,
           {"is_active": {"from": previous, "to": user.is_active}})
    db.commit()
    db.refresh(user)
    return _user_summary(user)


@router.get("/jobs")
def list_jobs(
    q: str | None = Query(default=None, max_length=120),
    status_filter: str | None = Query(default=None, max_length=30),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: AdminPermission = Depends(require_admin("jobs.read")),
    db: Session = Depends(get_db),
):
    query = db.query(Job).outerjoin(Shop, Job.shop_id == Shop.id).outerjoin(User, Shop.owner_id == User.id)
    if status_filter:
        query = query.filter(Job.status == status_filter)
    if q:
        match = f"%{q.strip()}%"
        query = query.filter(or_(Job.title.ilike(match), Shop.shop_name.ilike(match), User.full_name.ilike(match)))
    total = query.count()
    application_count = select(func.count(Application.id)).where(Application.job_id == Job.id).correlate(Job).scalar_subquery()
    rows = query.with_entities(Job, application_count.label("application_count"))\
        .order_by(Job.created_at.desc(), Job.id).offset(offset).limit(limit).all()
    items = []
    for job, count in rows:
        item = _job_summary(job, job.shop)
        item["application_count"] = count
        items.append(item)
    return _page(items, total, limit, offset)


@router.get("/jobs/{job_id}")
def get_job(job_id: str, _: AdminPermission = Depends(require_admin("jobs.read")), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    applications = db.query(Application, User).join(User, Application.worker_id == User.id).filter(
        Application.job_id == job.id,
    ).order_by(Application.created_at.desc()).limit(100).all()
    item = _job_summary(job, job.shop)
    item.update({"description": job.description, "duration_type": job.duration_type,
                 "scheduled_date": job.scheduled_date, "location": job.location,
                 "assigned_worker_id": job.assigned_worker_id,
                 "applications": [{"id": app.id, "worker_id": worker.id, "worker_name": worker.full_name,
                                   "status": app.status, "created_at": app.created_at}
                                  for app, worker in applications]})
    return item


@router.patch("/jobs/{job_id}/status")
def patch_job_status(job_id: str, body: JobStatusPatch,
                     admin: AdminPermission = Depends(require_admin("jobs.manage")), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).with_for_update().first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if body.status == job.status:
        raise HTTPException(status_code=409, detail="Job already has that status")
    if body.status not in {"open": {"cancelled"}, "assigned": {"cancelled"}}.get(job.status, set()):
        _write_failure_log("job.status_changed", "job", job.id, "invalid_transition")
        raise HTTPException(status_code=409, detail="Invalid job status transition")
    old_status = job.status
    job.status = body.status
    job.cancelled_at = datetime.now(timezone.utc)
    _audit(db, admin, "job.status_changed", "job", job.id,
           {"status": {"from": old_status, "to": body.status}})
    db.commit()
    db.refresh(job)
    return _job_summary(job, job.shop)
