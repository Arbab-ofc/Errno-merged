from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models import Job, Application, User, Shop
from schemas import JobCreateRequest, JobResponse, ApplicationResponse

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.post("", response_model=JobResponse)
def create_job(request: JobCreateRequest, owner_phone: Optional[str] = "9971439107", db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone_number == owner_phone).first()
    shop_id = None
    if user:
        shop = db.query(Shop).filter(Shop.owner_id == user.id).first()
        if shop:
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

@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.from_orm(job)

@router.post("/{job_id}/apply", response_model=ApplicationResponse)
def apply_for_job(job_id: str, worker_phone: str = "9971439107", db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    worker = db.query(User).filter(User.phone_number == worker_phone).first()
    if not worker:
        worker = User(phone_number=worker_phone, role="worker", full_name="Aman Kumar")
        db.add(worker)
        db.commit()
        db.refresh(worker)

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
    db.commit()
    db.refresh(app)

    return ApplicationResponse.from_orm(app)

@router.patch("/{job_id}/status", response_model=JobResponse)
def update_job_status(job_id: str, new_status: str, worker_id: Optional[str] = None, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = new_status
    if worker_id:
        job.assigned_worker_id = worker_id

    db.commit()
    db.refresh(job)

    return JobResponse.from_orm(job)
