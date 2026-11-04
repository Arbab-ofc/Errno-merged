"""Add durable four-hour pre-booking dispatch lifecycle."""
from alembic import op
import sqlalchemy as sa

revision = "fb4a6c90d112"
down_revision = "eb72a31c4890"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("booking_type", sa.String(length=20), nullable=False, server_default="CURRENT"))
    op.add_column("jobs", sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("dispatch_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("prebooking_dispatch_status", sa.String(length=32), nullable=True))
    op.add_column("jobs", sa.Column("prebooking_schedule_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("jobs", sa.Column("prebooking_dispatch_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("jobs", sa.Column("prebooking_next_attempt_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("prebooking_dispatch_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("prebooking_dispatch_completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("prebooking_dispatch_lease_owner", sa.String(length=120), nullable=True))
    op.add_column("jobs", sa.Column("prebooking_dispatch_lease_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("prebooking_dispatch_worker_count", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("prebooking_dispatch_failure_code", sa.String(length=80), nullable=True))
    op.add_column("jobs", sa.Column("prebooking_dispatch_failure_detail", sa.String(length=500), nullable=True))
    op.create_check_constraint("ck_jobs_booking_type", "jobs", "booking_type IN ('CURRENT','PRE_BOOKING')")
    op.create_check_constraint("ck_jobs_prebooking_schedule_version", "jobs", "prebooking_schedule_version >= 1")
    op.create_check_constraint("ck_jobs_prebooking_dispatch_attempts", "jobs", "prebooking_dispatch_attempts >= 0")
    op.create_check_constraint("ck_jobs_prebooking_worker_count", "jobs", "prebooking_dispatch_worker_count IS NULL OR prebooking_dispatch_worker_count >= 0")
    op.create_check_constraint("ck_jobs_prebooking_dispatch_status", "jobs", "prebooking_dispatch_status IS NULL OR prebooking_dispatch_status IN ('SCHEDULED','DISPATCHING','DISPATCHED','NO_ELIGIBLE_WORKERS','FAILED_RETRYABLE','FAILED','CANCELLED')")
    op.create_index("ix_jobs_prebooking_dispatch", "jobs", ["prebooking_dispatch_status", "prebooking_next_attempt_at", "dispatch_at"])


def downgrade() -> None:
    op.drop_index("ix_jobs_prebooking_dispatch", table_name="jobs")
    for name in ("ck_jobs_prebooking_dispatch_status", "ck_jobs_prebooking_worker_count", "ck_jobs_prebooking_dispatch_attempts", "ck_jobs_prebooking_schedule_version", "ck_jobs_booking_type"):
        op.drop_constraint(name, "jobs", type_="check")
    for name in ("prebooking_dispatch_failure_detail", "prebooking_dispatch_failure_code", "prebooking_dispatch_worker_count", "prebooking_dispatch_lease_until", "prebooking_dispatch_lease_owner", "prebooking_dispatch_completed_at", "prebooking_dispatch_started_at", "prebooking_next_attempt_at", "prebooking_dispatch_attempts", "prebooking_schedule_version", "prebooking_dispatch_status", "dispatch_at", "scheduled_at", "booking_type"):
        op.drop_column("jobs", name)
