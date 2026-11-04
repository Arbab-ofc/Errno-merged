"""Add Razorpay transactions, append-only wallet, withdrawals, cash and refunds."""
from alembic import op
import sqlalchemy as sa

revision = "5e91c0f4a8d2"
down_revision = "46aa7d91bc02"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("payment_transactions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("booking_id", sa.String(), sa.ForeignKey("jobs.id"), nullable=False, unique=True),
        sa.Column("shopkeeper_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("worker_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("order_id", sa.String(100), unique=True), sa.Column("payment_id", sa.String(100), unique=True),
        sa.Column("amount_paise", sa.Integer(), nullable=False),
        sa.Column("commission_paise", sa.Integer(), nullable=False),
        sa.Column("worker_earning_paise", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("status", sa.String(32), nullable=False, server_default="PAYMENT_PENDING"),
        sa.Column("idempotency_key", sa.String(160), nullable=False, unique=True),
        sa.Column("provider_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
        sa.Column("refunded_paise", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount_paise > 0", name="ck_payment_amount_positive"),
        sa.CheckConstraint("commission_paise >= 0 AND worker_earning_paise >= 0", name="ck_payment_split_nonnegative"),
        sa.CheckConstraint("commission_paise + worker_earning_paise = amount_paise", name="ck_payment_split_balances"),
        sa.CheckConstraint("refunded_paise >= 0 AND refunded_paise <= amount_paise", name="ck_payment_refund_range"))
    op.create_index("ix_payment_transactions_booking_id", "payment_transactions", ["booking_id"])
    op.create_index("ix_payment_transactions_shopkeeper_id", "payment_transactions", ["shopkeeper_id"])
    op.create_index("ix_payment_transactions_worker_id", "payment_transactions", ["worker_id"])
    op.create_table("payment_webhook_events",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("provider_event_id", sa.String(160), nullable=False, unique=True),
        sa.Column("event_type", sa.String(100), nullable=False), sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True)), sa.Column("outcome", sa.String(32), nullable=False, server_default="received"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_payment_webhook_events_created_at", "payment_webhook_events", ["created_at"])
    op.create_table("worker_wallet_ledger",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("worker_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("booking_id", sa.String(), sa.ForeignKey("jobs.id")), sa.Column("payment_id", sa.String(), sa.ForeignKey("payment_transactions.id")),
        sa.Column("withdrawal_id", sa.String()), sa.Column("category", sa.String(40), nullable=False),
        sa.Column("amount_paise", sa.Integer(), nullable=False), sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("idempotency_key", sa.String(180), nullable=False, unique=True), sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount_paise > 0", name="ck_wallet_entry_positive"))
    for col in ("worker_id", "booking_id", "payment_id", "withdrawal_id", "created_at"):
        op.create_index(f"ix_worker_wallet_ledger_{col}", "worker_wallet_ledger", [col])
    op.create_table("worker_withdrawals",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("worker_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount_paise", sa.Integer(), nullable=False), sa.Column("payout_method_id", sa.String(160), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="PENDING_EXTERNAL_PAYOUT"),
        sa.Column("idempotency_key", sa.String(160), nullable=False, unique=True), sa.Column("reviewed_by", sa.String()),
        sa.Column("review_reason", sa.Text()), sa.Column("provider_payout_id", sa.String(120), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount_paise > 0", name="ck_withdrawal_amount_positive"))
    op.create_index("ix_worker_withdrawals_worker_id", "worker_withdrawals", ["worker_id"])
    op.create_table("worker_payout_methods",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("worker_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider_reference", sa.String(160), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="PENDING_VERIFICATION"),
        sa.Column("kyc_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("verified_by", sa.String()), sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("worker_id", "provider_reference", name="uq_worker_payout_provider_reference"))
    op.create_index("ix_worker_payout_methods_worker_id", "worker_payout_methods", ["worker_id"])
    op.create_table("cash_collections",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("booking_id", sa.String(), sa.ForeignKey("jobs.id"), nullable=False, unique=True),
        sa.Column("payment_id", sa.String(), sa.ForeignKey("payment_transactions.id"), nullable=False),
        sa.Column("shopkeeper_id", sa.String(), sa.ForeignKey("users.id"), nullable=False), sa.Column("worker_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount_paise", sa.Integer(), nullable=False), sa.Column("shopkeeper_confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("worker_confirmed_at", sa.DateTime(timezone=True)), sa.Column("reconciliation_status", sa.String(40), nullable=False, server_default="PENDING_RECONCILIATION"),
        sa.Column("evidence_reference", sa.String(500)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount_paise > 0", name="ck_cash_amount_positive"))
    op.create_index("ix_cash_collections_booking_id", "cash_collections", ["booking_id"])
    op.create_index("ix_cash_collections_payment_id", "cash_collections", ["payment_id"])
    op.create_table("financial_refunds",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("payment_id", sa.String(), sa.ForeignKey("payment_transactions.id"), nullable=False),
        sa.Column("amount_paise", sa.Integer(), nullable=False), sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("provider_refund_id", sa.String(120), unique=True), sa.Column("status", sa.String(32), nullable=False, server_default="REQUESTED"),
        sa.Column("created_by", sa.String(), nullable=False), sa.Column("idempotency_key", sa.String(160), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount_paise > 0", name="ck_refund_amount_positive"))
    op.create_index("ix_financial_refunds_payment_id", "financial_refunds", ["payment_id"])
    op.create_table("platform_finance_ledger",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("payment_id", sa.String(), sa.ForeignKey("payment_transactions.id"), nullable=False),
        sa.Column("refund_id", sa.String(), sa.ForeignKey("financial_refunds.id")),
        sa.Column("cash_collection_id", sa.String(), sa.ForeignKey("cash_collections.id")),
        sa.Column("entry_type", sa.String(40), nullable=False), sa.Column("amount_paise", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("idempotency_key", sa.String(200), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount_paise > 0", name="ck_platform_finance_amount_positive"))
    op.create_index("ix_platform_finance_ledger_payment_id", "platform_finance_ledger", ["payment_id"])
    op.create_index("ix_platform_finance_ledger_refund_id", "platform_finance_ledger", ["refund_id"])
    op.create_index("ix_platform_finance_ledger_cash_collection_id", "platform_finance_ledger", ["cash_collection_id"])
    op.create_table("financial_audit_events",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("actor_id", sa.String()), sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("resource_type", sa.String(60), nullable=False), sa.Column("resource_id", sa.String(160)),
        sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_financial_audit_events_actor_id", "financial_audit_events", ["actor_id"])
    op.create_index("ix_financial_audit_events_resource_id", "financial_audit_events", ["resource_id"])
    op.create_index("ix_financial_audit_events_created_at", "financial_audit_events", ["created_at"])
    op.create_table("company_payment_configuration",
        sa.Column("id", sa.String(40), primary_key=True), sa.Column("qr_asset_url", sa.String(2048)),
        sa.Column("status", sa.String(24), nullable=False, server_default="UNCONFIGURED"),
        sa.Column("verified_by", sa.String()), sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))


def downgrade():
    op.drop_table("company_payment_configuration")
    op.drop_table("financial_audit_events")
    op.drop_table("platform_finance_ledger")
    op.drop_table("financial_refunds")
    op.drop_table("cash_collections")
    op.drop_table("worker_withdrawals")
    op.drop_table("worker_payout_methods")
    op.drop_table("worker_wallet_ledger")
    op.drop_table("payment_webhook_events")
    op.drop_table("payment_transactions")
