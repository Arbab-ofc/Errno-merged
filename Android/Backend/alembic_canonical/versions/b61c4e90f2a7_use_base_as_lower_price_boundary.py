"""Remove the redundant minimum price boundary.

Revision ID: b61c4e90f2a7
Revises: a45d92e27c11
"""
from alembic import op
import sqlalchemy as sa

revision = "b61c4e90f2a7"
down_revision = "a45d92e27c11"
branch_labels = None
depends_on = None


def upgrade():
    # Preserve any already-entered floor as the starting/base price only when
    # no base was entered. Existing approved configurations remain untouched.
    op.execute(sa.text("UPDATE duration_pricing SET base_price = minimum_price WHERE base_price IS NULL AND minimum_price IS NOT NULL"))
    op.drop_column("duration_pricing", "minimum_price")
    op.drop_column("pricing_quotes", "minimum_price")


def downgrade():
    # Restores the old column shape, but does not reintroduce a distinct floor.
    op.add_column("duration_pricing", sa.Column("minimum_price", sa.Numeric(12, 2), nullable=True))
    op.add_column("pricing_quotes", sa.Column("minimum_price", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.execute(sa.text("UPDATE duration_pricing SET minimum_price = base_price"))
    op.execute(sa.text("UPDATE pricing_quotes SET minimum_price = base_price"))
    op.alter_column("pricing_quotes", "minimum_price", server_default=None)
