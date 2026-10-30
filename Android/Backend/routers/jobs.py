from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from database import get_db
from models import Job, Application, User, Shop
from schemas import (JobCreateRequest, JobResponse, ApplicationResponse, ApplicationDecisionRequest,
                     OwnerApplicationResponse, WorkerApplicationResponse, WorkerApplicationsPage,
                     ApplicationJobSummary, ApplicationShopSummary)
from firebase_auth import authenticated_user, require_role
from job_lifecycle import VALID_JOB_STATUSES, can_transition

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.post("", response_model=JobResponse)
def create_job(request: JobCreateRequest, user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "shop_owner", "shopkeeper")
    shop_id = None
    if user:
        shop = db.query(Shop).filter(Shop.owner_id == user.id).first()
        if shop:
            shop_id = shop.id
        else:
            shop = Shop(owner_id=user.id, shop_name=f"{user.full_name or 'My'} Store")
            db.add(shop)
            db.flush()
            shop_id = shop.id

    job = Job(
        shop_id=shop_id,
        title=request.title,
        category=request.category,
        description=request.description,
        pay_amount=request.pay_amount,
        duration_type=request.duration_type,
        scheduled_date=request.scheduled_date,
        location=request.location,
        pickup_location=request.pickup_location,
        drop_location=request.drop_location,
        is_delivery=request.is_delivery,
        status="open"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return JobResponse.from_orm(job)

@router.get("", response_model=List[JobResponse])
def get_jobs(status_filter: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Job)
    if status_filter:
        query = query.filter(Job.status == status_filter)
    jobs = query.order_by(Job.created_at.desc()).all()
    return [JobResponse.from_orm(j) for j in jobs]

@router.get("/mine", response_model=List[JobResponse])
def get_my_jobs(user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "shop_owner", "shopkeeper")
    shop_ids = [row.id for row in db.query(Shop.id).filter(Shop.owner_id == user.id).all()]
    if not shop_ids:
        return []
    return [JobResponse.from_orm(job) for job in db.query(Job).filter(Job.shop_id.in_(shop_ids)).order_by(Job.created_at.desc()).all()]

@router.get("/worker/mine", response_model=List[JobResponse])
def get_worker_jobs(user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "worker")
    return [JobResponse.from_orm(job) for job in db.query(Job).filter(
        Job.assigned_worker_id == user.id
    ).order_by(Job.created_at.desc()).all()]

@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.from_orm(job)

@router.post("/{job_id}/apply", response_model=ApplicationResponse)
def apply_for_job(job_id: str, user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "worker")
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "open":
        raise HTTPException(status_code=409, detail="This job is no longer accepting applications")

    worker = user

    existing_app = db.query(Application).filter(
        Application.job_id == job_id,
        Application.worker_id == worker.id
    ).first()

    if existing_app:
        return ApplicationResponse.from_orm(existing_app)

    app = Application(
        job_id=job_id,
        worker_id=worker.id,
        status="pending"
    )
    db.add(app)
    try:
        db.commit()
    except IntegrityError:
        # The unique job/worker key closes the concurrent duplicate-apply race.
        db.rollback()
        existing_app = db.query(Application).filter(
            Application.job_id == job_id,
            Application.worker_id == worker.id,
        ).first()
        if existing_app is None:
            raise
        return ApplicationResponse.from_orm(existing_app)
    db.refresh(app)

    return ApplicationResponse.from_orm(app)

@router.get("/applications/me", response_model=WorkerApplicationsPage)
def get_my_applications(
    limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
    user: User = Depends(authenticated_user), db: Session = Depends(get_db),
):
    require_role(user, "worker")
    query = db.query(Application).filter(Application.worker_id == user.id)
    total = query.count()
    rows = query.options(joinedload(Application.job).joinedload(Job.shop)).order_by(
        Application.created_at.desc(), Application.id.desc()
    ).offset(offset).limit(limit).all()
    items = []
    for application in rows:
        job = application.job
        shop = job.shop
        items.append(WorkerApplicationResponse(
            id=application.id, job_id=job.id, worker_id=application.worker_id,
            status=application.status, created_at=application.created_at,
            job=ApplicationJobSummary(
                id=job.id, title=job.title, location=job.location, status=job.status,
                pay_amount=job.pay_amount, scheduled_date=job.scheduled_date,
                shop=ApplicationShopSummary(id=shop.id, shop_name=shop.shop_name,
                                            address=shop.address, category=shop.category) if shop else None,
            ),
        ))
    return WorkerApplicationsPage(items=items, total=total, limit=limit, offset=offset,
                                  has_more=offset + len(items) < total)

@router.delete("/{job_id}/applications/me", response_model=ApplicationResponse)
def cancel_my_application(job_id: str, user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "worker")
    application = db.query(Application).filter(
        Application.job_id == job_id, Application.worker_id == user.id
    ).with_for_update().first()
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.status != "pending":
        raise HTTPException(status_code=409, detail="Only pending applications can be cancelled")
    application.status = "cancelled"
    db.commit()
    db.refresh(application)
    return ApplicationResponse.from_orm(application)

@router.get("/applications/owner", response_model=List[OwnerApplicationResponse])
def get_owner_applications(user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "shop_owner", "shopkeeper")
    rows = db.query(Application, Job, User).join(Job, Application.job_id == Job.id).join(
        User, Application.worker_id == User.id
    ).join(Shop, Job.shop_id == Shop.id).filter(Shop.owner_id == user.id).order_by(
        Application.created_at.desc()
    ).all()
    return [OwnerApplicationResponse(
        id=application.id, job_id=job.id, job_title=job.title,
        worker_id=worker.id, worker_name=worker.full_name,
        status=application.status, created_at=application.created_at,
    ) for application, job, worker in rows]

@router.get("/{job_id}/applications", response_model=List[ApplicationResponse])
def get_job_applications(job_id: str, user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "shop_owner", "shopkeeper")
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.shop_id is None or db.query(Shop.id).filter(Shop.id == job.shop_id, Shop.owner_id == user.id).first() is None:
        raise HTTPException(status_code=403, detail="You do not own this job")
    rows = db.query(Application).filter(Application.job_id == job_id).order_by(Application.created_at.asc()).all()
    return [ApplicationResponse.from_orm(row) for row in rows]

@router.patch("/{job_id}/applications/{application_id}", response_model=ApplicationResponse)
def decide_application(job_id: str, application_id: str, body: ApplicationDecisionRequest,
                       user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "shop_owner", "shopkeeper")
    job = db.query(Job).filter(Job.id == job_id).with_for_update().first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.shop_id is None or db.query(Shop.id).filter(Shop.id == job.shop_id, Shop.owner_id == user.id).first() is None:
        raise HTTPException(status_code=403, detail="You do not own this job")
    application = db.query(Application).filter(Application.id == application_id, Application.job_id == job_id).with_for_update().first()
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.status != "pending" or job.status != "open":
        raise HTTPException(status_code=409, detail="Application or job is no longer pending")
    if body.decision == "accepted":
        job.status = "assigned"
        job.assigned_worker_id = application.worker_id
        application.status = "accepted"
        db.query(Application).filter(
            Application.job_id == job_id,
            Application.id != application_id,
            Application.status == "pending",
        ).update({Application.status: "rejected"}, synchronize_session=False)
    else:
        application.status = "rejected"
    db.commit()
    db.refresh(application)
    return ApplicationResponse.from_orm(application)

@router.patch("/{job_id}/status", response_model=JobResponse)
def update_job_status(
    job_id: str,
    new_status: str = Query(..., pattern="^(open|assigned|in_progress|completed|cancelled)$"),
    user: User = Depends(authenticated_user),
    db: Session = Depends(get_db),
):
    job = db.query(Job).filter(Job.id == job_id).with_for_update().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    require_role(user, "shop_owner", "shopkeeper")
    shop = db.query(Shop).filter(Shop.id == job.shop_id, Shop.owner_id == user.id).first()
    if shop is None:
        raise HTTPException(status_code=403, detail="You do not own this job")

    if new_status not in VALID_JOB_STATUSES or not can_transition(job.status, new_status):
        raise HTTPException(status_code=409, detail="Invalid job status transition")

    job.status = new_status
    job.cancelled_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(job)

    return JobResponse.from_orm(job)

@router.post("/{job_id}/start", response_model=JobResponse)
def start_assigned_job(job_id: str, user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "worker")
    job = db.query(Job).filter(Job.id == job_id).with_for_update().first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.assigned_worker_id != user.id:
        raise HTTPException(status_code=403, detail="Only the assigned worker can start this job")
    if job.status != "assigned":
        raise HTTPException(status_code=409, detail="Only assigned jobs can be started")
    job.status = "in_progress"
    job.started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return JobResponse.from_orm(job)

@router.post("/{job_id}/complete", response_model=JobResponse)
def confirm_job_completion(job_id: str, user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "shop_owner", "shopkeeper")
    job = db.query(Job).filter(Job.id == job_id).with_for_update().first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.shop_id is None or db.query(Shop.id).filter(Shop.id == job.shop_id, Shop.owner_id == user.id).first() is None:
        raise HTTPException(status_code=403, detail="You do not own this job")
    if job.status != "in_progress":
        raise HTTPException(status_code=409, detail="Only in-progress jobs can be completed")
    if not job.assigned_worker_id:
        raise HTTPException(status_code=409, detail="An assigned worker is required before completion")
    job.status = "completed"
    job.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return JobResponse.from_orm(job)
