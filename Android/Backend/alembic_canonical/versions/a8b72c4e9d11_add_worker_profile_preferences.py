"""Add persistent worker preferred skills."""
from alembic import op
import sqlalchemy as sa

revision = "a8b72c4e9d11"
down_revision = "d17a6c90e241"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "worker_profile_preferences",
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("preferred_skills", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("worker_profile_preferences")
