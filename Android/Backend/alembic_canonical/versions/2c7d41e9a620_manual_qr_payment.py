"""Add provider configuration and audited manual payment attempts."""
from alembic import op
import sqlalchemy as sa

revision = "2c7d41e9a620"
down_revision = "fb4a6c90d112"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payment_transactions", sa.Column("provider", sa.String(length=24), nullable=False, server_default="RAZORPAY"))
    op.add_column("company_payment_configuration", sa.Column("active_provider", sa.String(length=24), nullable=False, server_default="MANUAL_QR"))
    op.add_column("company_payment_configuration", sa.Column("qr_public_id", sa.String(length=500), nullable=True))
    op.add_column("company_payment_configuration", sa.Column("merchant_name", sa.String(length=160), nullable=True))
    op.add_column("company_payment_configuration", sa.Column("upi_id", sa.String(length=160), nullable=True))
    op.add_column("company_payment_configuration", sa.Column("updated_by", sa.String(length=160), nullable=True))
    op.create_table("manual_payment_submissions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("booking_id", sa.String(), nullable=False),
        sa.Column("payment_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("asset_public_id", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=80), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="PENDING_REVIEW", nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(length=160), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["booking_id"], ["jobs.id"]),
        sa.ForeignKeyConstraint(["payment_id"], ["payment_transactions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("booking_id", "attempt_number", name="uq_manual_payment_attempt"))
    op.create_index("ix_manual_payment_submissions_booking_id", "manual_payment_submissions", ["booking_id"])
    op.create_index("ix_manual_payment_submissions_payment_id", "manual_payment_submissions", ["payment_id"])
    op.create_index("ix_manual_payment_submissions_user_id", "manual_payment_submissions", ["user_id"])
    op.create_index("ix_manual_payment_submissions_status", "manual_payment_submissions", ["status"])


def downgrade():
    op.drop_table("manual_payment_submissions")
    for col in ("updated_by", "upi_id", "merchant_name", "qr_public_id", "active_provider"):
        op.drop_column("company_payment_configuration", col)
    op.drop_column("payment_transactions", "provider")
