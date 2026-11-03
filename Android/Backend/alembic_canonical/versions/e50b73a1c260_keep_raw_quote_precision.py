"""Keep sub-rupee multiplier precision in quote raw amounts."""
from alembic import op
import sqlalchemy as sa

revision = "e50b73a1c260"
down_revision = "d91a2c7f4e60"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("pricing_quotes", "raw_price", type_=sa.Numeric(16, 6), existing_type=sa.Numeric(12, 2), existing_nullable=False)


def downgrade():
    # Existing raw quote values may contain precision beyond cents; a downgrade
    # necessarily rounds that display-only raw field back to the historic scale.
    op.alter_column("pricing_quotes", "raw_price", type_=sa.Numeric(12, 2), existing_type=sa.Numeric(16, 6), existing_nullable=False)
