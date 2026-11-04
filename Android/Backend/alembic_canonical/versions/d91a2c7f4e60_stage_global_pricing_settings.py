"""Stage global commercial settings until administrator activation."""
from alembic import op
import sqlalchemy as sa

revision = "d91a2c7f4e60"
down_revision = "c42af1b73d90"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("pricing_settings_drafts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("values", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))


def downgrade():
    op.drop_table("pricing_settings_drafts")
