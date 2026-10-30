from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import User, Shop
from schemas import SendOTPRequest, SendOTPResponse, VerifyOTPRequest, AuthResponse, RegisterRequest, UserResponse
from firebase_auth import authenticated_user, verified_claims

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/send-otp", response_model=SendOTPResponse)
def send_otp(request: SendOTPRequest, db: Session = Depends(get_db)):
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Phone OTP is disabled because no verified OTP provider is configured. Use Firebase Authentication.",
    )

@router.post("/verify-otp", response_model=AuthResponse)
def verify_otp(request: VerifyOTPRequest, db: Session = Depends(get_db)):
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Phone OTP verification is disabled because no verified OTP provider is configured. Use Firebase Authentication.",
    )

@router.post("/register", response_model=AuthResponse)
def register_user(
    request: RegisterRequest,
    claims: dict = Depends(verified_claims),
    db: Session = Depends(get_db),
):
    uid = claims["uid"]
    verified_phone = claims.get("phone_number")
    digits = lambda value: "".join(character for character in value if character.isdigit())
    verified_digits = digits(verified_phone or "")
    requested_digits = digits(request.phone_number)
    same_verified_phone = verified_digits == requested_digits or (
        (verified_phone or "").startswith("+91")
        and len(requested_digits) == 10
        and verified_digits.endswith(requested_digits)
    )
    if not verified_phone or not same_verified_phone:
        raise HTTPException(status_code=403, detail="Registration phone must match the verified Firebase identity")

    user = db.query(User).filter(User.firebase_uid == uid).first()
    phone_owner = db.query(User).filter(User.phone_number == verified_phone).first()
    if phone_owner is not None and phone_owner.firebase_uid not in (None, uid):
        raise HTTPException(status_code=409, detail="Phone number is linked to another account")
    if user is None:
        if phone_owner is not None:
            user = phone_owner
            user.firebase_uid = uid
        else:
            user = User(firebase_uid=uid, email=claims.get("email"), phone_number=verified_phone,
                        full_name=claims.get("name"), is_phone_verified=True)
            db.add(user)
    elif user.phone_number not in (None, verified_phone):
        raise HTTPException(status_code=409, detail="Account already has a different verified phone number")

    if user.role is not None and user.role != request.role:
        raise HTTPException(status_code=409, detail="Role has already been selected")
    user.full_name = request.full_name.strip()
    user.phone_number = verified_phone
    user.email = claims.get("email") or user.email
    user.is_phone_verified = True
    user.role = request.role
    if request.role in ("shop_owner", "shopkeeper") and not user.shops:
        user.shops.append(Shop(shop_name=f"{user.full_name or 'My'} Store"))
    db.commit()
    db.refresh(user)
    return AuthResponse(success=True, token=None, message="Profile registered", user=UserResponse.model_validate(user))

@router.get("/me/{phone_number}", response_model=UserResponse)
def get_user_profile(phone_number: str, user: User = Depends(authenticated_user)):
    # Preserve the old path shape while resolving identity exclusively from verified Firebase claims.
    if user.phone_number is not None and user.phone_number != phone_number:
        raise HTTPException(status_code=403, detail="You may only access your own profile")
    return UserResponse.from_orm(user)
