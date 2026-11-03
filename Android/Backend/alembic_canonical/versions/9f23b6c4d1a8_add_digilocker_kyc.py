"""Add consent-aware worker/staff KYC, verification sessions and private manual review metadata."""
from alembic import op
import sqlalchemy as sa

revision = "9f23b6c4d1a8"
down_revision = "5e91c0f4a8d2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "kyc_verification_profiles",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True),
        sa.Column("staff_firebase_uid", sa.String(160), unique=True),
        sa.Column("subject_role", sa.String(24), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="NOT_STARTED"),
        sa.Column("verification_method", sa.String(40)),
        sa.Column("provider", sa.String(40)),
        sa.Column("document_types", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("verified_document_types", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("reverification_required_at", sa.DateTime(timezone=True)),
        sa.Column("consent_withdrawn_at", sa.DateTime(timezone=True)),
        sa.Column("user_message_code", sa.String(80)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("(user_id IS NOT NULL AND staff_firebase_uid IS NULL) OR (user_id IS NULL AND staff_firebase_uid IS NOT NULL)", name="ck_kyc_profile_subject"),
        sa.CheckConstraint("subject_role IN ('worker','staff')", name="ck_kyc_profile_role"),
        sa.CheckConstraint("status IN ('NOT_STARTED','CONSENT_PENDING','VERIFICATION_PENDING','VERIFIED','FAILED','EXPIRED','MANUAL_REVIEW','REJECTED','REVERIFICATION_REQUIRED')", name="ck_kyc_profile_status"),
    )
    op.create_index("ix_kyc_verification_profiles_status", "kyc_verification_profiles", ["status"])
    op.create_table(
        "kyc_verification_sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("profile_id", sa.String(), sa.ForeignKey("kyc_verification_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("staff_firebase_uid", sa.String(160)),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="CONSENT_PENDING"),
        sa.Column("state_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("nonce_hash", sa.String(64), nullable=False),
        sa.Column("mock_callback_token_hash", sa.String(64)),
        sa.Column("requested_document_types", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("consent_version", sa.String(80), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("failure_code", sa.String(80)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('CONSENT_PENDING','VERIFICATION_PENDING','VERIFIED','FAILED','EXPIRED','CANCELLED')", name="ck_kyc_session_status"),
    )
    op.create_index("ix_kyc_sessions_profile_id", "kyc_verification_sessions", ["profile_id"])
    op.create_index("ix_kyc_sessions_user_id", "kyc_verification_sessions", ["user_id"])
    op.create_index("ix_kyc_sessions_staff_firebase_uid", "kyc_verification_sessions", ["staff_firebase_uid"])
    op.create_index("ix_kyc_sessions_expires_at", "kyc_verification_sessions", ["expires_at"])
    op.create_index("ix_kyc_sessions_user_status", "kyc_verification_sessions", ["user_id", "status"])
    op.create_table(
        "kyc_consent_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("profile_id", sa.String(), sa.ForeignKey("kyc_verification_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.String(), sa.ForeignKey("kyc_verification_sessions.id", ondelete="SET NULL")),
        sa.Column("subject_user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("subject_staff_uid", sa.String(160)),
        sa.Column("purpose", sa.String(240), nullable=False),
        sa.Column("document_types", sa.JSON(), nullable=False),
        sa.Column("consent_version", sa.String(80), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_kyc_consent_records_profile_id", "kyc_consent_records", ["profile_id"])
    op.create_index("ix_kyc_consent_records_session_id", "kyc_consent_records", ["session_id"])
    op.create_index("ix_kyc_consent_records_subject_user_id", "kyc_consent_records", ["subject_user_id"])
    op.create_table(
        "kyc_verified_documents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("profile_id", sa.String(), sa.ForeignKey("kyc_verification_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.String(), sa.ForeignKey("kyc_verification_sessions.id", ondelete="SET NULL")),
        sa.Column("document_type", sa.String(60), nullable=False),
        sa.Column("issuer_id", sa.String(160)),
        sa.Column("proof_status", sa.String(32), nullable=False),
        sa.Column("provider_document_ref_hash", sa.String(64)),
        sa.Column("masked_identifier", sa.String(40)),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("retain_until", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_kyc_verified_documents_profile_id", "kyc_verified_documents", ["profile_id"])
    op.create_table(
        "kyc_manual_reviews",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("profile_id", sa.String(), sa.ForeignKey("kyc_verification_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("document_type", sa.String(60), nullable=False),
        sa.Column("encrypted_storage_key", sa.String(240), nullable=False, unique=True),
        sa.Column("content_type", sa.String(80), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("scan_status", sa.String(24), nullable=False, server_default="QUARANTINED"),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING_SCAN"),
        sa.Column("review_reason_code", sa.String(80)),
        sa.Column("reviewer_uid", sa.String(160)),
        sa.Column("reviewer_note", sa.Text()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("resubmission_requested", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("retain_until", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("size_bytes > 0", name="ck_kyc_manual_size_positive"),
        sa.CheckConstraint("scan_status IN ('QUARANTINED','CLEAN','INFECTED','ERROR')", name="ck_kyc_manual_scan_status"),
        sa.CheckConstraint("status IN ('PENDING_SCAN','PENDING_REVIEW','APPROVED','REJECTED','RESUBMISSION_REQUESTED','DELETED')", name="ck_kyc_manual_status"),
    )
    op.create_index("ix_kyc_manual_reviews_profile_id", "kyc_manual_reviews", ["profile_id"])
    op.create_index("ix_kyc_manual_reviews_user_id", "kyc_manual_reviews", ["user_id"])
    op.create_table(
        "kyc_audit_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("profile_id", sa.String(), sa.ForeignKey("kyc_verification_profiles.id", ondelete="CASCADE")),
        sa.Column("actor_type", sa.String(24), nullable=False),
        sa.Column("actor_id", sa.String(160)),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("from_status", sa.String(32)),
        sa.Column("to_status", sa.String(32)),
        sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_kyc_audit_events_profile_id", "kyc_audit_events", ["profile_id"])
    op.create_index("ix_kyc_audit_events_created_at", "kyc_audit_events", ["created_at"])


def downgrade():
    op.drop_table("kyc_audit_events")
    op.drop_table("kyc_manual_reviews")
    op.drop_table("kyc_verified_documents")
    op.drop_table("kyc_consent_records")
    op.drop_table("kyc_verification_sessions")
    op.drop_table("kyc_verification_profiles")
