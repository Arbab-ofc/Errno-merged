"""Record all pricing component versions used by each quote.

Revision ID: 3b7280d1c6a4
Revises: f84e2d6a91b3
"""
from alembic import op
import sqlalchemy as sa

revision = "3b7280d1c6a4"
down_revision = "f84e2d6a91b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable for pre-existing quotes: their historical component identities
    # cannot be reconstructed without fabricating audit data.
    op.add_column("pricing_quotes", sa.Column("pricing_rule_snapshot", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("pricing_quotes", "pricing_rule_snapshot")
