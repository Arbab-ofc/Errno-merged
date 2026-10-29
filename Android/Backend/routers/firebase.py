from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from firebase_auth import verified_claims
from models import User

router = APIRouter(prefix="/api/v1", tags=["Firebase authentication"])


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=120)
    role: str | None = Field(default=None, pattern="^(worker|shop_owner)$")


def profile(user: User) -> dict:
    return {
        "id": str(user.id),
        "firebase_uid": user.firebase_uid,
        "name": user.full_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "role": user.role,
        "onboarding_completed": user.role in ("worker", "shopkeeper", "shop_owner"),
    }


def current_user(claims: dict, db: Session) -> User:
    user = db.query(User).filter(User.firebase_uid == claims["uid"]).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User profile not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    return user


@router.post("/auth/firebase")
def firebase_login(claims: dict = Depends(verified_claims), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.firebase_uid == claims["uid"]).first()
    if user is None:
        # Deliberately do not link by email: legacy accounts require an explicit linking flow.
        user = User(
            firebase_uid=claims["uid"],
            full_name=claims.get("name"),
            email=claims.get("email"),
            phone_number=None,
            role=None,
            is_active=True,
            is_phone_verified=False,
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            # A concurrent first login may have inserted this UID. Roll back and resolve it.
            db.rollback()
            user = db.query(User).filter(User.firebase_uid == claims["uid"]).first()
            if user is None:
                raise HTTPException(status_code=409, detail="Account conflict requires support") from None
        else:
            db.refresh(user)
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    return {"success": True, "user": profile(user)}


@router.get("/users/me")
def get_me(claims: dict = Depends(verified_claims), db: Session = Depends(get_db)):
    return profile(current_user(claims, db))


@router.patch("/users/me")
def update_me(
    body: ProfileUpdate,
    claims: dict = Depends(verified_claims),
    db: Session = Depends(get_db),
):
    user = current_user(claims, db)
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(status_code=422, detail="Name cannot be blank")
        user.full_name = name
    if body.role is not None:
        if user.role is not None and user.role != body.role:
            raise HTTPException(status_code=409, detail="Role has already been selected")
        user.role = body.role
    db.commit()
    db.refresh(user)
    return profile(user)


@router.post("/auth/logout")
def logout(_: dict = Depends(verified_claims)):
    # Firebase ID tokens are stateless; mobile clients clear their local Firebase session.
    return {"success": True, "message": "Local session cleared by client"}
