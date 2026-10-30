"""Persist job lifecycle timestamps.

Revision ID: 34d6bcf1a902
Revises: 8fa2137c5d20
"""

from alembic import op
import sqlalchemy as sa


revision = "34d6bcf1a902"
down_revision = "8fa2137c5d20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Reverses only the additive lifecycle metadata; status and job records remain intact.
    op.drop_column("jobs", "cancelled_at")
    op.drop_column("jobs", "completed_at")
    op.drop_column("jobs", "started_at")
