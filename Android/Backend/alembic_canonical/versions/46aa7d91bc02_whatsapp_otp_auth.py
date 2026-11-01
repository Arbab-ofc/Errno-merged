"""Add WhatsApp OTP challenges, revocable backend sessions and gateway audit."""
from alembic import op
import sqlalchemy as sa

revision = "46aa7d91bc02"
down_revision = "3b7280d1c6a4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "whatsapp_otp_challenges",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("phone_number", sa.String(16), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("otp_digest", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resend_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("delivery_status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("gateway_message_id", sa.String(160)),
        sa.Column("request_ip_hash", sa.String(64)),
        sa.CheckConstraint("role IN ('worker','shop_owner','shopkeeper')", name="ck_wa_otp_role"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_wa_otp_attempts"),
    )
    op.create_index("ix_whatsapp_otp_challenges_phone_number", "whatsapp_otp_challenges", ["phone_number"])
    op.create_index("ix_whatsapp_otp_challenges_expires_at", "whatsapp_otp_challenges", ["expires_at"])
    op.create_index("ix_whatsapp_otp_challenges_request_ip_hash", "whatsapp_otp_challenges", ["request_ip_hash"])
    op.create_index("ix_wa_otp_phone_created", "whatsapp_otp_challenges", ["phone_number", "created_at"])

    op.create_table(
        "backend_auth_sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_digest", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_backend_auth_sessions_user_id", "backend_auth_sessions", ["user_id"])
    op.create_index("ix_backend_auth_sessions_token_digest", "backend_auth_sessions", ["token_digest"], unique=True)
    op.create_index("ix_backend_auth_sessions_expires_at", "backend_auth_sessions", ["expires_at"])

    op.create_table(
        "whatsapp_gateway_audit",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("message_id", sa.String(160)),
        sa.Column("destination_suffix", sa.String(4)),
        sa.Column("details", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_whatsapp_gateway_audit_event_type", "whatsapp_gateway_audit", ["event_type"])
    op.create_index("ix_whatsapp_gateway_audit_created_at", "whatsapp_gateway_audit", ["created_at"])


def downgrade():
    op.drop_table("whatsapp_gateway_audit")
    op.drop_table("backend_auth_sessions")
    op.drop_table("whatsapp_otp_challenges")
