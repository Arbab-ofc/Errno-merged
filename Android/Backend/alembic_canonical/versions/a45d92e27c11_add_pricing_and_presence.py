"""Add versioned pricing, quotes, audit, and shared presence sessions."""
from alembic import op
import sqlalchemy as sa

revision = "a45d92e27c11"
down_revision = "8fa2137c5d20"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("duration_pricing",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("duration_hours", sa.Integer(), nullable=False, unique=True),
        sa.Column("minimum_price", sa.Numeric(12, 2)), sa.Column("base_price", sa.Numeric(12, 2)), sa.Column("maximum_price", sa.Numeric(12, 2)),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"), sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("approval_status", sa.String(20), nullable=False, server_default="draft"), sa.Column("effective_from", sa.DateTime(timezone=True)),
        sa.Column("effective_until", sa.DateTime(timezone=True)), sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String()), sa.Column("updated_by", sa.String()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("duration_hours BETWEEN 1 AND 12", name="ck_duration_pricing_hours"))
    op.create_table("pricing_settings",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("surge_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("time_pricing_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")), sa.Column("demand_pricing_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("combined_multiplier_cap", sa.Numeric(8, 4)), sa.Column("commission_rate", sa.Numeric(8, 6)), sa.Column("quote_ttl_seconds", sa.Integer()),
        sa.Column("rounding_policy", sa.String(30)), sa.Column("default_timezone", sa.String(80)), sa.Column("heartbeat_interval_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("presence_ttl_seconds", sa.Integer(), nullable=False, server_default="180"), sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_by", sa.String()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_table("time_pricing_rules",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False), sa.Column("timezone", sa.String(80), nullable=False), sa.Column("multiplier", sa.Numeric(8, 4), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")), sa.Column("effective_from", sa.DateTime(timezone=True)),
        sa.Column("effective_until", sa.DateTime(timezone=True)), sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_table("demand_pricing_rules",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("demand_level", sa.String(40), nullable=False),
        sa.Column("minimum_demand_ratio", sa.Numeric(12, 4)), sa.Column("maximum_demand_ratio", sa.Numeric(12, 4)),
        sa.Column("availability_thresholds", sa.JSON(), nullable=False, server_default=sa.text("'{}'")), sa.Column("multiplier", sa.Numeric(8, 4), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")), sa.Column("effective_from", sa.DateTime(timezone=True)),
        sa.Column("effective_until", sa.DateTime(timezone=True)), sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.create_table("pricing_quotes",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False), sa.Column("duration_hours", sa.Integer(), nullable=False),
        sa.Column("service_start_at", sa.DateTime(timezone=True), nullable=False), sa.Column("area_id", sa.String()), sa.Column("base_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("minimum_price", sa.Numeric(12, 2), nullable=False), sa.Column("maximum_price", sa.Numeric(12, 2), nullable=False), sa.Column("time_band", sa.String(120)),
        sa.Column("time_multiplier", sa.Numeric(8, 4), nullable=False), sa.Column("demand_level", sa.String(40)), sa.Column("demand_multiplier", sa.Numeric(8, 4), nullable=False),
        sa.Column("raw_price", sa.Numeric(12, 2), nullable=False), sa.Column("final_service_charge", sa.Numeric(12, 2), nullable=False),
        sa.Column("commission_rate", sa.Numeric(8, 6), nullable=False), sa.Column("commission_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("worker_payout_amount", sa.Numeric(12, 2), nullable=False), sa.Column("pricing_rule_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)), sa.Column("job_id", sa.String(), sa.ForeignKey("jobs.id"), unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"))
    op.create_index("ix_pricing_quotes_user_id", "pricing_quotes", ["user_id"])
    op.create_table("pricing_audit_logs", sa.Column("id", sa.String(), primary_key=True), sa.Column("admin_user_id", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False), sa.Column("entity_id", sa.String(120)), sa.Column("action", sa.String(80), nullable=False),
        sa.Column("previous_value", sa.JSON()), sa.Column("new_value", sa.JSON()), sa.Column("pricing_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_pricing_audit_logs_admin_user_id", "pricing_audit_logs", ["admin_user_id"])
    op.create_index("ix_pricing_audit_logs_created_at", "pricing_audit_logs", ["created_at"])
    op.create_table("user_presence_sessions", sa.Column("id", sa.String(), primary_key=True), sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_identifier", sa.String(160), nullable=False), sa.Column("device_platform", sa.String(30)), sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("is_foreground", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("availability_status", sa.String(20), nullable=False, server_default="unavailable"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("user_id", "session_identifier", name="uq_presence_user_session"))
    op.create_index("ix_user_presence_sessions_user_id", "user_presence_sessions", ["user_id"])
    op.create_index("ix_user_presence_sessions_expires_at", "user_presence_sessions", ["expires_at"])
    # These are reference maxima only. The 4–6 hour figures are marked provisional; every row stays disabled/draft.
    refs = [160, 240, 320, 420, 510, 625, 720, 830, 920, 1000, 1100, 1200]
    for duration, maximum in enumerate(refs, 1):
        op.execute(sa.text("INSERT INTO duration_pricing (id,duration_hours,maximum_price,enabled,approval_status,version) VALUES (:id,:duration,:maximum,false,'draft',1)")
                   .bindparams(id=f"reference-{duration}", duration=duration, maximum=maximum))
    op.execute(sa.text("INSERT INTO pricing_settings (id,version) VALUES ('singleton',1)"))


def downgrade():
    op.drop_table("user_presence_sessions")
    op.drop_table("pricing_audit_logs")
    op.drop_index("ix_pricing_quotes_user_id", table_name="pricing_quotes")
    op.drop_table("pricing_quotes")
    op.drop_table("demand_pricing_rules")
    op.drop_table("time_pricing_rules")
    op.drop_table("pricing_settings")
    op.drop_table("duration_pricing")
