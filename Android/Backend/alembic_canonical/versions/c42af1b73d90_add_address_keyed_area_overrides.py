"""Add address-keyed area-specific pricing overrides."""
from alembic import op
import sqlalchemy as sa

revision = "c42af1b73d90"
down_revision = "b61c4e90f2a7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("area_pricing_rules",
        sa.Column("id", sa.String(), primary_key=True),
        # Uses the same address text already persisted by canonical shops/jobs;
        # normalized in application code instead of inventing a second area ID space.
        sa.Column("area_key", sa.String(500), nullable=False),
        sa.Column("duration_hours", sa.Integer(), nullable=False),
        sa.Column("base_price", sa.Numeric(12, 2)),
        sa.Column("maximum_price", sa.Numeric(12, 2)),
        sa.Column("time_rule_id", sa.String(), sa.ForeignKey("time_pricing_rules.id")),
        sa.Column("demand_rule_id", sa.String(), sa.ForeignKey("demand_pricing_rules.id")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("approval_status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("effective_from", sa.DateTime(timezone=True)),
        sa.Column("effective_until", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_by", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("duration_hours BETWEEN 1 AND 12", name="ck_area_pricing_duration"))
    op.create_index("ix_area_pricing_rules_area_key", "area_pricing_rules", ["area_key"])


def downgrade():
    op.drop_index("ix_area_pricing_rules_area_key", table_name="area_pricing_rules")
    op.drop_table("area_pricing_rules")
