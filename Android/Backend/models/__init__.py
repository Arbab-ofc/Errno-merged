import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Float, Index, func, text, JSON, Integer, Numeric, Time, CheckConstraint, UniqueConstraint, Date
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
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
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


class DurationPricing(Base):
    __tablename__ = "duration_pricing"
    id = Column(String, primary_key=True, default=generate_uuid)
    duration_hours = Column(Integer, nullable=False, unique=True)
    base_price = Column(Numeric(12, 2), nullable=True)
    maximum_price = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(3), nullable=False, default="INR", server_default=text("'INR'"))
    enabled = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    approval_status = Column(String(20), nullable=False, default="draft", server_default=text("'draft'"))
    effective_from = Column(DateTime(timezone=True), nullable=True)
    effective_until = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default=text("1"))
    created_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    __table_args__ = (CheckConstraint("duration_hours BETWEEN 1 AND 12", name="ck_duration_pricing_hours"),)


class PricingSettings(Base):
    __tablename__ = "pricing_settings"
    id = Column(String, primary_key=True, default=generate_uuid)
    surge_enabled = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    time_pricing_enabled = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    demand_pricing_enabled = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    combined_multiplier_cap = Column(Numeric(8, 4), nullable=True)
    commission_rate = Column(Numeric(8, 6), nullable=True)
    quote_ttl_seconds = Column(Integer, nullable=True)
    rounding_policy = Column(String(30), nullable=True)
    default_timezone = Column(String(80), nullable=True)
    heartbeat_interval_seconds = Column(Integer, nullable=False, default=60, server_default=text("60"))
    presence_ttl_seconds = Column(Integer, nullable=False, default=180, server_default=text("180"))
    version = Column(Integer, nullable=False, default=1, server_default=text("1"))
    updated_by = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class PricingSettingsDraft(Base):
    __tablename__ = "pricing_settings_drafts"
    id = Column(String, primary_key=True, default=generate_uuid)
    values = Column(JSON, nullable=False)
    version = Column(Integer, nullable=False)
    updated_by = Column(String, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class TimePricingRule(Base):
    __tablename__ = "time_pricing_rules"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(120), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    timezone = Column(String(80), nullable=False)
    multiplier = Column(Numeric(8, 4), nullable=False)
    enabled = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    effective_from = Column(DateTime(timezone=True), nullable=True)
    effective_until = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default=text("1"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class DemandPricingRule(Base):
    __tablename__ = "demand_pricing_rules"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(120), nullable=False)
    demand_level = Column(String(40), nullable=False)
    minimum_demand_ratio = Column(Numeric(12, 4), nullable=True)
    maximum_demand_ratio = Column(Numeric(12, 4), nullable=True)
    availability_thresholds = Column(JSON, nullable=False, default=dict, server_default=text("'{}'"))
    multiplier = Column(Numeric(8, 4), nullable=False)
    enabled = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    effective_from = Column(DateTime(timezone=True), nullable=True)
    effective_until = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default=text("1"))


class AreaPricingRule(Base):
    """Address-keyed override using the canonical shop/job address strings."""
    __tablename__ = "area_pricing_rules"
    id = Column(String, primary_key=True, default=generate_uuid)
    area_key = Column(String(500), nullable=False, index=True)
    duration_hours = Column(Integer, nullable=False)
    base_price = Column(Numeric(12, 2), nullable=True)
    maximum_price = Column(Numeric(12, 2), nullable=True)
    time_rule_id = Column(String, ForeignKey("time_pricing_rules.id"), nullable=True)
    demand_rule_id = Column(String, ForeignKey("demand_pricing_rules.id"), nullable=True)
    enabled = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    approval_status = Column(String(20), nullable=False, default="draft", server_default=text("'draft'"))
    effective_from = Column(DateTime(timezone=True), nullable=True)
    effective_until = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, nullable=False, default=1, server_default=text("1"))
    updated_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    __table_args__ = (CheckConstraint("duration_hours BETWEEN 1 AND 12", name="ck_area_pricing_duration"),)


class PricingQuote(Base):
    __tablename__ = "pricing_quotes"
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    duration_hours = Column(Integer, nullable=False)
    service_start_at = Column(DateTime(timezone=True), nullable=False)
    area_id = Column(String, nullable=True)
    base_price = Column(Numeric(12, 2), nullable=False)
    maximum_price = Column(Numeric(12, 2), nullable=False)
    time_band = Column(String(120), nullable=True)
    time_multiplier = Column(Numeric(8, 4), nullable=False)
    demand_level = Column(String(40), nullable=True)
    demand_multiplier = Column(Numeric(8, 4), nullable=False)
    raw_price = Column(Numeric(16, 6), nullable=False)
    final_service_charge = Column(Numeric(12, 2), nullable=False)
    commission_rate = Column(Numeric(8, 6), nullable=False)
    commission_amount = Column(Numeric(12, 2), nullable=False)
    worker_payout_amount = Column(Numeric(12, 2), nullable=False)
    pricing_rule_version = Column(Integer, nullable=False)
    pricing_rule_snapshot = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=True, unique=True)
    status = Column(String(20), nullable=False, default="active", server_default=text("'active'"))


class PaymentTransaction(Base):
    """One provider order per booking; amounts mirror the immutable quote snapshot."""
    __tablename__ = "payment_transactions"
    id = Column(String, primary_key=True, default=generate_uuid)
    booking_id = Column(String, ForeignKey("jobs.id"), nullable=False, unique=True, index=True)
    shopkeeper_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    worker_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    order_id = Column(String(100), nullable=True, unique=True)
    payment_id = Column(String(100), nullable=True, unique=True)
    amount_paise = Column(Integer, nullable=False)
    commission_paise = Column(Integer, nullable=False)
    worker_earning_paise = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False, default="INR", server_default=text("'INR'"))
    status = Column(String(32), nullable=False, default="PAYMENT_PENDING", server_default=text("'PAYMENT_PENDING'"))
    idempotency_key = Column(String(160), nullable=False, unique=True)
    provider_payload = Column(JSON, nullable=False, default=dict, server_default=text("'{}'"))
    paid_at = Column(DateTime(timezone=True), nullable=True)
    refunded_paise = Column(Integer, nullable=False, default=0, server_default=text("0"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        CheckConstraint("amount_paise > 0", name="ck_payment_amount_positive"),
        CheckConstraint("commission_paise >= 0 AND worker_earning_paise >= 0", name="ck_payment_split_nonnegative"),
        CheckConstraint("commission_paise + worker_earning_paise = amount_paise", name="ck_payment_split_balances"),
        CheckConstraint("refunded_paise >= 0 AND refunded_paise <= amount_paise", name="ck_payment_refund_range"),
    )


class PaymentWebhookEvent(Base):
    __tablename__ = "payment_webhook_events"
    id = Column(String, primary_key=True, default=generate_uuid)
    provider_event_id = Column(String(160), nullable=False, unique=True)
    event_type = Column(String(100), nullable=False)
    payload_digest = Column(String(64), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    outcome = Column(String(32), nullable=False, default="received", server_default=text("'received'"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)


class WalletLedgerEntry(Base):
    """Append-only worker balance movement in integer paise."""
    __tablename__ = "worker_wallet_ledger"
    id = Column(String, primary_key=True, default=generate_uuid)
    worker_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    booking_id = Column(String, ForeignKey("jobs.id"), nullable=True, index=True)
    payment_id = Column(String, ForeignKey("payment_transactions.id"), nullable=True, index=True)
    withdrawal_id = Column(String, nullable=True, index=True)
    category = Column(String(40), nullable=False)
    amount_paise = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False, default="INR", server_default=text("'INR'"))
    idempotency_key = Column(String(180), nullable=False, unique=True)
    metadata_json = Column(JSON, nullable=False, default=dict, server_default=text("'{}'"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    __table_args__ = (CheckConstraint("amount_paise > 0", name="ck_wallet_entry_positive"),)


class WorkerWithdrawal(Base):
    __tablename__ = "worker_withdrawals"
    id = Column(String, primary_key=True, default=generate_uuid)
    worker_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    amount_paise = Column(Integer, nullable=False)
    payout_method_id = Column(String(160), nullable=False)
    status = Column(String(40), nullable=False, default="PENDING_EXTERNAL_PAYOUT", server_default=text("'PENDING_EXTERNAL_PAYOUT'"))
    idempotency_key = Column(String(160), nullable=False, unique=True)
    reviewed_by = Column(String, nullable=True)
    review_reason = Column(Text, nullable=True)
    provider_payout_id = Column(String(120), nullable=True, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    __table_args__ = (CheckConstraint("amount_paise > 0", name="ck_withdrawal_amount_positive"),)


class WorkerPayoutMethod(Base):
    __tablename__ = "worker_payout_methods"
    id = Column(String, primary_key=True, default=generate_uuid)
    worker_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    provider_reference = Column(String(160), nullable=False)
    status = Column(String(24), nullable=False, default="PENDING_VERIFICATION", server_default=text("'PENDING_VERIFICATION'"))
    kyc_verified = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    verified_by = Column(String, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (UniqueConstraint("worker_id", "provider_reference", name="uq_worker_payout_provider_reference"),)


class WorkerProfilePreferences(Base):
    __tablename__ = "worker_profile_preferences"
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    preferred_skills = Column(JSON, nullable=False, default=list, server_default=text("'[]'"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class CashCollection(Base):
    __tablename__ = "cash_collections"
    id = Column(String, primary_key=True, default=generate_uuid)
    booking_id = Column(String, ForeignKey("jobs.id"), nullable=False, unique=True, index=True)
    payment_id = Column(String, ForeignKey("payment_transactions.id"), nullable=False, index=True)
    shopkeeper_id = Column(String, ForeignKey("users.id"), nullable=False)
    worker_id = Column(String, ForeignKey("users.id"), nullable=False)
    amount_paise = Column(Integer, nullable=False)
    shopkeeper_confirmed_at = Column(DateTime(timezone=True), nullable=True)
    worker_confirmed_at = Column(DateTime(timezone=True), nullable=True)
    reconciliation_status = Column(String(40), nullable=False, default="PENDING_RECONCILIATION", server_default=text("'PENDING_RECONCILIATION'"))
    evidence_reference = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (CheckConstraint("amount_paise > 0", name="ck_cash_amount_positive"),)


class FinancialRefund(Base):
    __tablename__ = "financial_refunds"
    id = Column(String, primary_key=True, default=generate_uuid)
    payment_id = Column(String, ForeignKey("payment_transactions.id"), nullable=False, index=True)
    amount_paise = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    provider_refund_id = Column(String(120), nullable=True, unique=True)
    status = Column(String(32), nullable=False, default="REQUESTED", server_default=text("'REQUESTED'"))
    created_by = Column(String, nullable=False)
    idempotency_key = Column(String(160), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (CheckConstraint("amount_paise > 0", name="ck_refund_amount_positive"),)


class PlatformFinanceLedgerEntry(Base):
    """Append-only ERRNO commission collection and reversal movements."""
    __tablename__ = "platform_finance_ledger"
    id = Column(String, primary_key=True, default=generate_uuid)
    payment_id = Column(String, ForeignKey("payment_transactions.id"), nullable=False, index=True)
    refund_id = Column(String, ForeignKey("financial_refunds.id"), nullable=True, index=True)
    cash_collection_id = Column(String, ForeignKey("cash_collections.id"), nullable=True, index=True)
    entry_type = Column(String(40), nullable=False)
    amount_paise = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False, default="INR", server_default=text("'INR'"))
    idempotency_key = Column(String(200), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (CheckConstraint("amount_paise > 0", name="ck_platform_finance_amount_positive"),)


class FinancialAuditEvent(Base):
    __tablename__ = "financial_audit_events"
    id = Column(String, primary_key=True, default=generate_uuid)
    actor_id = Column(String, nullable=True, index=True)
    event_type = Column(String(80), nullable=False)
    resource_type = Column(String(60), nullable=False)
    resource_id = Column(String(160), nullable=True, index=True)
    details = Column(JSON, nullable=False, default=dict, server_default=text("'{}'"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=generate_uuid)
    recipient_user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recipient_role = Column(String(24), nullable=False)
    event_id = Column(String(64), nullable=False, index=True)
    event_type = Column(String(80), nullable=False)
    title = Column(String(180), nullable=False)
    body = Column(String(500), nullable=False)
    priority = Column(String(16), nullable=False, default="normal", server_default="normal")
    category = Column(String(32), nullable=False)
    data_payload = Column(JSON, nullable=False, default=dict, server_default=text("'{}'"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    read_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    deduplication_key = Column(String(300), nullable=False, unique=True)
    __table_args__ = (
        CheckConstraint("priority IN ('low','normal','high')", name="ck_notification_priority"),
        CheckConstraint("category IN ('booking','job','payment','account','verification','marketing','admin')", name="ck_notification_category"),
        Index("ix_notifications_recipient_created", "recipient_user_id", "created_at", "id"),
        Index("ix_notifications_recipient_read", "recipient_user_id", "read_at", "created_at"),
        Index("ix_notifications_category_created", "category", "created_at"),
    )


class NotificationDevice(Base):
    __tablename__ = "notification_devices"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(24), nullable=False)
    platform = Column(String(12), nullable=False)
    device_identifier = Column(String(160), nullable=False)
    encrypted_token = Column(Text, nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True)
    app_version = Column(String(40), nullable=True)
    active = Column(Boolean, nullable=False, default=True, server_default=text("true"), index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    invalidated_at = Column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        CheckConstraint("platform IN ('android','ios')", name="ck_notification_device_platform"),
        UniqueConstraint("user_id", "device_identifier", name="uq_notification_device_user_install"),
        Index("ix_notification_devices_user_active", "user_id", "active"),
    )


class NotificationOutbox(Base):
    __tablename__ = "notification_outbox"

    id = Column(String, primary_key=True, default=generate_uuid)
    notification_id = Column(String, ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False, unique=True)
    event_id = Column(String(64), nullable=False)
    event_type = Column(String(80), nullable=False)
    recipient_user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    payload = Column(JSON, nullable=False, default=dict, server_default=text("'{}'"))
    status = Column(String(24), nullable=False, default="queued", server_default="queued")
    attempts = Column(Integer, nullable=False, default=0, server_default="0")
    next_attempt_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    last_error_code = Column(String(80), nullable=True)
    lease_owner = Column(String(80), nullable=True)
    lease_until = Column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        CheckConstraint("status IN ('queued','sending','retrying','accepted_by_fcm','permanently_failed','no_devices','suppressed','expired')", name="ck_notification_outbox_status"),
        UniqueConstraint("event_id", "recipient_user_id", "event_type", name="uq_notification_outbox_event_recipient"),
        Index("ix_notification_outbox_dispatch", "status", "next_attempt_at", "created_at"),
        Index("ix_notification_outbox_lease", "status", "lease_until"),
    )


class NotificationDeliveryAttempt(Base):
    __tablename__ = "notification_delivery_attempts"

    id = Column(String, primary_key=True, default=generate_uuid)
    notification_id = Column(String, ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(String, ForeignKey("notification_devices.id", ondelete="SET NULL"), nullable=True, index=True)
    attempt_number = Column(Integer, nullable=False)
    provider_message_id = Column(String(240), nullable=True)
    status = Column(String(24), nullable=False)
    error_code = Column(String(80), nullable=True)
    attempted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        CheckConstraint("status IN ('accepted_by_fcm','invalid_token','failed')", name="ck_notification_delivery_status"),
        UniqueConstraint("notification_id", "device_id", "attempt_number", name="uq_notification_delivery_attempt"),
    )


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    booking_updates_enabled = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    job_alerts_enabled = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    payment_updates_enabled = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    account_updates_enabled = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    marketing_enabled = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class NotificationRegistrationThrottle(Base):
    __tablename__ = "notification_registration_throttles"
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    window_started_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, nullable=False, default=0, server_default="0")


class CompanyPaymentConfiguration(Base):
    __tablename__ = "company_payment_configuration"
    id = Column(String(40), primary_key=True, default="company")
    qr_asset_url = Column(String(2048), nullable=True)
    status = Column(String(24), nullable=False, default="UNCONFIGURED", server_default=text("'UNCONFIGURED'"))
    verified_by = Column(String, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class KYCVerificationProfile(Base):
    """Current server-authoritative identity verification state for a worker or staff subject."""
    __tablename__ = "kyc_verification_profiles"
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, unique=True)
    staff_firebase_uid = Column(String(160), nullable=True, unique=True)
    subject_role = Column(String(24), nullable=False)
    status = Column(String(32), nullable=False, default="NOT_STARTED", server_default=text("'NOT_STARTED'"), index=True)
    verification_method = Column(String(40), nullable=True)
    provider = Column(String(40), nullable=True)
    document_types = Column(JSON, nullable=False, default=list, server_default=text("'[]'"))
    verified_document_types = Column(JSON, nullable=False, default=list, server_default=text("'[]'"))
    verified_at = Column(DateTime(timezone=True), nullable=True)
    reverification_required_at = Column(DateTime(timezone=True), nullable=True)
    consent_withdrawn_at = Column(DateTime(timezone=True), nullable=True)
    user_message_code = Column(String(80), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        CheckConstraint("(user_id IS NOT NULL AND staff_firebase_uid IS NULL) OR (user_id IS NULL AND staff_firebase_uid IS NOT NULL)", name="ck_kyc_profile_subject"),
        CheckConstraint("subject_role IN ('worker','staff')", name="ck_kyc_profile_role"),
        CheckConstraint("status IN ('NOT_STARTED','CONSENT_PENDING','VERIFICATION_PENDING','VERIFIED','FAILED','EXPIRED','MANUAL_REVIEW','REJECTED','REVERIFICATION_REQUIRED')", name="ck_kyc_profile_status"),
    )


class KYCVerificationSession(Base):
    __tablename__ = "kyc_verification_sessions"
    id = Column(String, primary_key=True, default=generate_uuid)
    profile_id = Column(String, ForeignKey("kyc_verification_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    staff_firebase_uid = Column(String(160), nullable=True, index=True)
    provider = Column(String(40), nullable=False)
    status = Column(String(32), nullable=False, default="CONSENT_PENDING", server_default=text("'CONSENT_PENDING'"))
    state_hash = Column(String(64), nullable=False, unique=True)
    nonce_hash = Column(String(64), nullable=False)
    mock_callback_token_hash = Column(String(64), nullable=True)
    requested_document_types = Column(JSON, nullable=False, default=list, server_default=text("'[]'"))
    consent_version = Column(String(80), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    failure_code = Column(String(80), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        CheckConstraint("status IN ('CONSENT_PENDING','VERIFICATION_PENDING','VERIFIED','FAILED','EXPIRED','CANCELLED')", name="ck_kyc_session_status"),
        Index("ix_kyc_sessions_user_status", "user_id", "status"),
    )


class KYCConsentRecord(Base):
    __tablename__ = "kyc_consent_records"
    id = Column(String, primary_key=True, default=generate_uuid)
    profile_id = Column(String, ForeignKey("kyc_verification_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String, ForeignKey("kyc_verification_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    subject_user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    subject_staff_uid = Column(String(160), nullable=True)
    purpose = Column(String(240), nullable=False)
    document_types = Column(JSON, nullable=False)
    consent_version = Column(String(80), nullable=False)
    granted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class KYCVerifiedDocument(Base):
    __tablename__ = "kyc_verified_documents"
    id = Column(String, primary_key=True, default=generate_uuid)
    profile_id = Column(String, ForeignKey("kyc_verification_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String, ForeignKey("kyc_verification_sessions.id", ondelete="SET NULL"), nullable=True)
    document_type = Column(String(60), nullable=False)
    issuer_id = Column(String(160), nullable=True)
    proof_status = Column(String(32), nullable=False)
    provider_document_ref_hash = Column(String(64), nullable=True)
    masked_identifier = Column(String(40), nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict, server_default=text("'{}'"))
    verified_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    retain_until = Column(DateTime(timezone=True), nullable=True)


class KYCManualReview(Base):
    __tablename__ = "kyc_manual_reviews"
    id = Column(String, primary_key=True, default=generate_uuid)
    profile_id = Column(String, ForeignKey("kyc_verification_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    document_type = Column(String(60), nullable=False)
    encrypted_storage_key = Column(String(240), nullable=False, unique=True)
    content_type = Column(String(80), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False)
    scan_status = Column(String(24), nullable=False, default="QUARANTINED", server_default=text("'QUARANTINED'"))
    status = Column(String(32), nullable=False, default="PENDING_SCAN", server_default=text("'PENDING_SCAN'"))
    review_reason_code = Column(String(80), nullable=True)
    reviewer_uid = Column(String(160), nullable=True)
    reviewer_note = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    resubmission_requested = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    retain_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        CheckConstraint("size_bytes > 0", name="ck_kyc_manual_size_positive"),
        CheckConstraint("scan_status IN ('QUARANTINED','CLEAN','INFECTED','ERROR')", name="ck_kyc_manual_scan_status"),
        CheckConstraint("status IN ('PENDING_SCAN','PENDING_REVIEW','APPROVED','REJECTED','RESUBMISSION_REQUESTED','DELETED')", name="ck_kyc_manual_status"),
    )


class KYCAuditEvent(Base):
    __tablename__ = "kyc_audit_events"
    id = Column(String, primary_key=True, default=generate_uuid)
    profile_id = Column(String, ForeignKey("kyc_verification_profiles.id", ondelete="CASCADE"), nullable=True, index=True)
    actor_type = Column(String(24), nullable=False)
    actor_id = Column(String(160), nullable=True)
    event_type = Column(String(80), nullable=False)
    from_status = Column(String(32), nullable=True)
    to_status = Column(String(32), nullable=True)
    details = Column(JSON, nullable=False, default=dict, server_default=text("'{}'"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)


class PricingAudit(Base):
    __tablename__ = "pricing_audit_logs"
    id = Column(String, primary_key=True, default=generate_uuid)
    admin_user_id = Column(String, nullable=False, index=True)
    entity_type = Column(String(80), nullable=False)
    entity_id = Column(String(120), nullable=True)
    action = Column(String(80), nullable=False)
    previous_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    pricing_version = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)


class PresenceSession(Base):
    __tablename__ = "user_presence_sessions"
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_identifier = Column(String(160), nullable=False)
    device_platform = Column(String(30), nullable=True)
    last_heartbeat_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    is_foreground = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    availability_status = Column(String(20), nullable=False, default="unavailable", server_default=text("'unavailable'"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    __table_args__ = (UniqueConstraint("user_id", "session_identifier", name="uq_presence_user_session"),)


class WorkerLocation(Base):
    __tablename__ = "worker_live_locations"
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), index=True)


class WhatsAppOTPChallenge(Base):
    """Short-lived phone challenge; only a keyed digest of the code is stored."""
    __tablename__ = "whatsapp_otp_challenges"
    id = Column(String, primary_key=True, default=generate_uuid)
    phone_number = Column(String(16), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    otp_digest = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    resend_after = Column(DateTime(timezone=True), nullable=False)
    attempt_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    delivery_status = Column(String(20), nullable=False, default="pending", server_default=text("'pending'"))
    gateway_message_id = Column(String(160), nullable=True)
    request_ip_hash = Column(String(64), nullable=True, index=True)
    __table_args__ = (
        CheckConstraint("role IN ('worker','shop_owner','shopkeeper')", name="ck_wa_otp_role"),
        CheckConstraint("attempt_count >= 0", name="ck_wa_otp_attempts"),
        Index("ix_wa_otp_phone_created", "phone_number", "created_at"),
    )


class BackendAuthSession(Base):
    """Opaque revocable backend bearer sessions issued after OTP verification."""
    __tablename__ = "backend_auth_sessions"
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_digest = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    user = relationship("User")
    __table_args__ = (Index("ix_backend_auth_sessions_token_digest", "token_digest", unique=True),)


class WhatsAppGatewayAudit(Base):
    """Operational status and message metadata; intentionally contains no OTP text."""
    __tablename__ = "whatsapp_gateway_audit"
    id = Column(String, primary_key=True, default=generate_uuid)
    event_type = Column(String(40), nullable=False, index=True)
    outcome = Column(String(20), nullable=False)
    message_id = Column(String(160), nullable=True)
    destination_suffix = Column(String(4), nullable=True)
    details = Column(JSON, nullable=False, default=dict, server_default=text("'{}'"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
