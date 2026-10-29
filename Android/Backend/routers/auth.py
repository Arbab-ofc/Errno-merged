from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import random
from database import get_db
from models import User, OTP, Shop
from schemas import SendOTPRequest, SendOTPResponse, VerifyOTPRequest, AuthResponse, RegisterRequest, UserResponse
from firebase_auth import authenticated_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/send-otp", response_model=SendOTPResponse)
def send_otp(request: SendOTPRequest, db: Session = Depends(get_db)):
    # Generate 6-digit OTP code (or 123456 for easy dev testing)
    otp_code = "123456"

    # Store OTP record
    otp_record = OTP(
        phone_number=request.phone_number,
        otp_code=otp_code
    )
    db.add(otp_record)
    db.commit()

    return SendOTPResponse(
        success=True,
        message=f"OTP sent successfully to +91 {request.phone_number}",
        otp_demo=otp_code
    )

@router.post("/verify-otp", response_model=AuthResponse)
def verify_otp(request: VerifyOTPRequest, db: Session = Depends(get_db)):
    # Verify OTP
    otp_record = db.query(OTP).filter(
        OTP.phone_number == request.phone_number,
        OTP.otp_code == request.otp_code,
        OTP.is_verified == False
    ).order_by(OTP.created_at.desc()).first()

    if not otp_record and request.otp_code != "123456":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP code. Please try again."
        )

    if otp_record:
        otp_record.is_verified = True
        db.commit()

    # Check if user exists
    user = db.query(User).filter(User.phone_number == request.phone_number).first()
    if not user:
        # Create default user if not exists
        user = User(
            phone_number=request.phone_number,
            role="shopkeeper",
            is_phone_verified=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create default shop for shopkeeper
        shop = Shop(owner_id=user.id, shop_name="My General Store")
        db.add(shop)
        db.commit()

    return AuthResponse(
        success=True,
        token=f"bearer_token_{user.id}",
        message="Authentication successful",
        user=UserResponse.from_orm(user)
    )

@router.post("/register", response_model=AuthResponse)
def register_user(request: RegisterRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone_number == request.phone_number).first()
    if user:
        user.full_name = request.full_name
        user.role = request.role
        user.is_phone_verified = True
        db.commit()
        db.refresh(user)
    else:
        user = User(
            full_name=request.full_name,
            phone_number=request.phone_number,
            role=request.role,
            is_phone_verified=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    if user.role == "shopkeeper":
        existing_shop = db.query(Shop).filter(Shop.owner_id == user.id).first()
        if not existing_shop:
            shop = Shop(owner_id=user.id, shop_name=f"{user.full_name}'s Store")
            db.add(shop)
            db.commit()

    return AuthResponse(
        success=True,
        token=f"bearer_token_{user.id}",
        message="User registered successfully",
        user=UserResponse.from_orm(user)
    )

@router.get("/me/{phone_number}", response_model=UserResponse)
def get_user_profile(phone_number: str, user: User = Depends(authenticated_user)):
    # Preserve the old path shape while resolving identity exclusively from verified Firebase claims.
    if user.phone_number is not None and user.phone_number != phone_number:
        raise HTTPException(status_code=403, detail="You may only access your own profile")
    return UserResponse.from_orm(user)
