import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Float, Integer
from sqlalchemy.orm import relationship
from database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    full_name = Column(String, nullable=True)
    phone_number = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, nullable=True, index=True)
    firebase_uid = Column(String, nullable=True, unique=True, index=True)
    role = Column(String, nullable=True, default=None)  # assigned by the existing onboarding flow
    is_active = Column(Boolean, default=True)
    is_phone_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    shops = relationship("Shop", back_populates="owner", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="worker", cascade="all, delete-orphan")

class OTP(Base):
    __tablename__ = "otps"

    id = Column(String, primary_key=True, default=generate_uuid)
    phone_number = Column(String, index=True, nullable=False)
    otp_code = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_verified = Column(Boolean, default=False)

class Shop(Base):
    __tablename__ = "shops"

    id = Column(String, primary_key=True, default=generate_uuid)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    shop_name = Column(String, nullable=False, default="My Store")
    address = Column(Text, nullable=True, default="Okhla Market Area, New Delhi")
    category = Column(String, nullable=True, default="General Store")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="shops")
    jobs = relationship("Job", back_populates="shop", cascade="all, delete-orphan")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    shop_id = Column(String, ForeignKey("shops.id"), nullable=True)
    title = Column(String, nullable=False)
    category = Column(String, nullable=True, default="Store Helper")
    description = Column(Text, nullable=True)
    pay_amount = Column(Float, nullable=False, default=349.0)
    duration_type = Column(String, nullable=False, default="Full Shift (8 hrs)")
    scheduled_date = Column(String, nullable=True, default="Today")
    location = Column(String, nullable=True, default="Okhla Market Area")
    pickup_location = Column(String, nullable=True)
    drop_location = Column(String, nullable=True)
    is_delivery = Column(Boolean, default=False)
    status = Column(String, nullable=False, default="open")  # open, assigned, completed
    assigned_worker_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    shop = relationship("Shop", back_populates="jobs")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")

class Application(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    worker_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(String, nullable=False, default="pending")  # pending, accepted, rejected
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    job = relationship("Job", back_populates="applications")
    worker = relationship("User", back_populates="applications")
