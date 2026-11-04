from pydantic import BaseModel, Field, ConfigDict, model_validator
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


class WhatsAppOTPRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phone: str = Field(..., min_length=8, max_length=16, pattern=r"^\+[1-9][0-9]{7,14}$")
    role: str = Field(..., pattern="^(WORKER|SHOPKEEPER|worker|shop_owner|shopkeeper)$")


class WhatsAppOTPResendRequest(WhatsAppOTPRequest):
    requestId: str = Field(..., min_length=16, max_length=64)


class WhatsAppOTPVerifyRequest(WhatsAppOTPResendRequest):
    otp: str = Field(..., pattern=r"^[0-9]{6}$")
    fullName: Optional[str] = Field(default=None, min_length=1, max_length=120)


class WhatsAppOTPSendResponse(BaseModel):
    success: bool
    requestId: str
    expiresInSeconds: int
    resendAfterSeconds: int
    deliveryStatus: str

# Shop Schemas
class ShopCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    shop_name: str = Field(..., min_length=1, max_length=160, example="Rahul General Store")
    address: Optional[str] = Field(default=None, max_length=500)
    category: Optional[str] = Field(default=None, max_length=100)

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
    model_config = ConfigDict(extra="forbid")
    title: str = Field(..., min_length=1, max_length=160, example="Counter Staff Assistant")
    category: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=5000)
    pay_amount: float = Field(default=349.0, gt=0, le=10000000)
    duration_type: str = Field(default="Full Shift (8 hrs)", min_length=1, max_length=80)
    scheduled_date: Optional[str] = Field(default=None, max_length=100)
    location: Optional[str] = Field(default=None, max_length=500)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    pickup_location: Optional[str] = None
    drop_location: Optional[str] = None
    is_delivery: bool = False
    quote_id: str = Field(..., min_length=1, max_length=64)
    service_start_at: datetime

    @model_validator(mode="after")
    def coordinates_are_a_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together")
        return self

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
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    pickup_location: Optional[str] = None
    drop_location: Optional[str] = None
    is_delivery: bool
    status: str
    assigned_worker_id: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Application Schemas
class ApplicationResponse(BaseModel):
    id: str
    job_id: str
    worker_id: str
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ApplicationShopSummary(BaseModel):
    id: str
    shop_name: str
    address: Optional[str] = None
    category: Optional[str] = None

class ApplicationJobSummary(BaseModel):
    id: str
    title: str
    location: Optional[str] = None
    status: str
    pay_amount: float
    scheduled_date: Optional[str] = None
    shop: Optional[ApplicationShopSummary] = None

class WorkerApplicationResponse(ApplicationResponse):
    job: ApplicationJobSummary

class WorkerApplicationsPage(BaseModel):
    items: List[WorkerApplicationResponse]
    total: int
    limit: int
    offset: int
    has_more: bool

class ApplicationDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(..., pattern="^(accepted|rejected)$")

class OwnerApplicationResponse(BaseModel):
    id: str
    job_id: str
    job_title: str
    worker_id: str
    worker_name: Optional[str] = None
    status: str
