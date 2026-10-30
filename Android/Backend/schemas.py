from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

# Auth Schemas
class SendOTPRequest(BaseModel):
    phone_number: str = Field(..., example="9971439107")
    role: Optional[str] = Field(default="shopkeeper", example="shopkeeper")

class SendOTPResponse(BaseModel):
    success: bool
    message: str
    otp_demo: Optional[str] = None

class VerifyOTPRequest(BaseModel):
    phone_number: str = Field(..., example="9971439107")
    otp_code: str = Field(..., example="123456")

class UserResponse(BaseModel):
    id: str
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[str] = None
    is_phone_verified: bool

    class Config:
        from_attributes = True

class AuthResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: Optional[str] = None
    user: Optional[UserResponse] = None

class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str = Field(..., min_length=1, max_length=120)
    phone_number: str = Field(..., min_length=7, max_length=20)
    role: str = Field(..., pattern="^(worker|shop_owner|shopkeeper)$")

# Shop Schemas
class ShopCreateRequest(BaseModel):
    shop_name: str = Field(..., example="Rahul General Store")
    address: Optional[str] = Field(default="Okhla Market Area, New Delhi")
    category: Optional[str] = Field(default="General Store")

class ShopResponse(BaseModel):
    id: str
    owner_id: str
    shop_name: str
    address: Optional[str] = None
    category: Optional[str] = None

    class Config:
        from_attributes = True

# Job Schemas
class JobCreateRequest(BaseModel):
    title: str = Field(..., example="Counter Staff Assistant")
    category: Optional[str] = Field(default="Store Helper")
    description: Optional[str] = Field(default="Assist with customer checkout and inventory stocking.")
    pay_amount: float = Field(default=349.0)
    duration_type: str = Field(default="Full Shift (8 hrs)")
    scheduled_date: Optional[str] = Field(default="Today")
    location: Optional[str] = Field(default="Okhla Market Area, New Delhi")
    pickup_location: Optional[str] = None
    drop_location: Optional[str] = None
    is_delivery: bool = False

class JobResponse(BaseModel):
    id: str
    shop_id: Optional[str] = None
    title: str
    category: Optional[str] = None
    description: Optional[str] = None
    pay_amount: float
    duration_type: str
    scheduled_date: Optional[str] = None
    location: Optional[str] = None
    pickup_location: Optional[str] = None
    drop_location: Optional[str] = None
    is_delivery: bool
    status: str
    assigned_worker_id: Optional[str] = None

    class Config:
        from_attributes = True

# Application Schemas
class ApplicationResponse(BaseModel):
    id: str
    job_id: str
    worker_id: str
    status: str

    class Config:
        from_attributes = True
