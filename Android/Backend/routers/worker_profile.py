from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from database import get_db
from firebase_auth import authenticated_user, require_role
from models import User, WorkerProfilePreferences

router = APIRouter(prefix="/api/v1/workers/me/profile", tags=["Worker profile"])


class WorkerProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preferredSkills: list[str] = Field(min_length=0, max_length=20)

    @field_validator("preferredSkills")
    @classmethod
    def normalize_skills(cls, values: list[str]) -> list[str]:
        cleaned = []
        for value in values:
            skill = value.strip()
            if not skill or len(skill) > 60:
                raise ValueError("Each skill must contain 1 to 60 characters")
            if skill not in cleaned:
                cleaned.append(skill)
        return cleaned


def _worker(user: User) -> None:
    require_role(user, "worker")


@router.get("")
def get_worker_profile(user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    _worker(user)
    row = db.query(WorkerProfilePreferences).filter_by(user_id=user.id).first()
    return {"preferredSkills": row.preferred_skills if row else []}


@router.patch("")
def update_worker_profile(body: WorkerProfileUpdate, user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    _worker(user)
    row = db.query(WorkerProfilePreferences).filter_by(user_id=user.id).with_for_update().first()
    if row is None:
        row = WorkerProfilePreferences(user_id=user.id)
        db.add(row)
    row.preferred_skills = body.preferredSkills
    db.commit()
    db.refresh(row)
    return {"preferredSkills": row.preferred_skills}
