import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Float, Index, func, text, JSON
from sqlalchemy.orm import relationship
from db_base import Base

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
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    is_phone_verified = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    shops = relationship("Shop", back_populates="owner", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="worker", cascade="all, delete-orphan")

class OTP(Base):
    __tablename__ = "otps"

    id = Column(String, primary_key=True, default=generate_uuid)
    phone_number = Column(String, index=True, nullable=False)
    otp_code = Column(String, nullable=False)
    # Preserve the existing OTP timestamp/default semantics and field behavior.
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_verified = Column(Boolean, default=False)

class Shop(Base):
    __tablename__ = "shops"

    id = Column(String, primary_key=True, default=generate_uuid)
    owner_id = Column(
        String,
        ForeignKey("users.id", name="fk_shops_owner_id_users"),
        nullable=False,
        index=True,
    )
    shop_name = Column(String, nullable=False, default="My Store", server_default=text("'My Store'"))
    address = Column(Text, nullable=True, default="Okhla Market Area, New Delhi", server_default=text("'Okhla Market Area, New Delhi'"))
    category = Column(String, nullable=True, default="General Store", server_default=text("'General Store'"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    owner = relationship("User", back_populates="shops")
    jobs = relationship("Job", back_populates="shop", cascade="all, delete-orphan")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    shop_id = Column(
        String,
        ForeignKey("shops.id", name="fk_jobs_shop_id_shops"),
        nullable=True,
        index=True,
    )
    title = Column(String, nullable=False)
    category = Column(String, nullable=True, default="Store Helper", server_default=text("'Store Helper'"))
    description = Column(Text, nullable=True)
    pay_amount = Column(Float, nullable=False, default=349.0, server_default=text("349.0"))
    duration_type = Column(String, nullable=False, default="Full Shift (8 hrs)", server_default=text("'Full Shift (8 hrs)'"))
    scheduled_date = Column(String, nullable=True, default="Today", server_default=text("'Today'"))
    location = Column(String, nullable=True, default="Okhla Market Area", server_default=text("'Okhla Market Area'"))
    pickup_location = Column(String, nullable=True)
    drop_location = Column(String, nullable=True)
    is_delivery = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    status = Column(String, nullable=False, default="open", server_default=text("'open'"))  # open, assigned, completed
    assigned_worker_id = Column(
        String,
        ForeignKey("users.id", name="fk_jobs_assigned_worker_id_users"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        Index("ix_jobs_created_at", created_at.desc()),
        Index("ix_jobs_status_created_at", "status", created_at.desc()),
    )

    shop = relationship("Shop", back_populates="jobs")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")

class Application(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("jobs.id", name="fk_applications_job_id_jobs"), nullable=False)
    worker_id = Column(
        String,
        ForeignKey("users.id", name="fk_applications_worker_id_users"),
        nullable=False,
        index=True,
    )
    status = Column(String, nullable=False, default="pending", server_default=text("'pending'"))  # pending, accepted, rejected, cancelled
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (
        Index("uq_applications_job_worker", "job_id", "worker_id", unique=True),
    )

    job = relationship("Job", back_populates="applications")
    worker = relationship("User", back_populates="applications")


class AdminPermission(Base):
    """Operator-provisioned admin access keyed by verified Firebase UID."""
    __tablename__ = "admin_permissions"

    id = Column(String, primary_key=True, default=generate_uuid)
    firebase_uid = Column(String, nullable=False, unique=True, index=True)
    email = Column(String, nullable=True)
    permissions = Column(JSON, nullable=False, default=list, server_default=text("'[]'"))
    active = Column(Boolean, nullable=False, default=True, server_default=text("true"), index=True)
    granted_by_uid = Column(String, nullable=False)
    reason = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class AdminAuditLog(Base):
    """Immutable record of successful privileged actions and permission changes."""
    __tablename__ = "admin_audit_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    administrator_uid = Column(String, nullable=False, index=True)
    action = Column(String(120), nullable=False)
    resource_type = Column(String(80), nullable=False)
    resource_id = Column(String(120), nullable=True)
    outcome = Column(String(20), nullable=False, default="success", server_default=text("'success'"))
    change_metadata = Column("metadata", JSON, nullable=False, default=dict, server_default=text("'{}'"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
