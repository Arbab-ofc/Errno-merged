"""Create the canonical schema matching the active FastAPI models.

Revision ID: 1c64eb87a321
Revises:
Create Date: 2026-10-30

This is the initial revision for the isolated canonical migration environment.
It is not part of the legacy six-revision chain.
"""

from alembic import op
import sqlalchemy as sa


revision = "1c64eb87a321"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This baseline is only valid for a new, empty application schema.
    bind = op.get_bind()
    existing_public_relations = set(
        bind.execute(
            sa.text(
                """
                SELECT relation.relname
                FROM pg_catalog.pg_class AS relation
                JOIN pg_catalog.pg_namespace AS namespace
                  ON namespace.oid = relation.relnamespace
                WHERE namespace.nspname = 'public'
                  AND relation.relkind IN ('r', 'p', 'v', 'm', 'f', 'S')
                """
            )
        ).scalars()
    )
    unexpected_relations = existing_public_relations - {"alembic_version"}
    if unexpected_relations:
        raise RuntimeError(
            "Canonical initial migration requires an empty public schema; found existing relations."
        )

    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("phone_number", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("firebase_uid", sa.String(), nullable=True),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_phone_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_phone_number", "users", ["phone_number"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_users_firebase_uid", "users", ["firebase_uid"], unique=True)

    op.create_table(
        "otps",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("phone_number", sa.String(), nullable=False),
        sa.Column("otp_code", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_otps"),
    )
    op.create_index("ix_otps_phone_number", "otps", ["phone_number"], unique=False)

    op.create_table(
        "shops",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("shop_name", sa.String(), server_default=sa.text("'My Store'"), nullable=False),
        sa.Column("address", sa.Text(), server_default=sa.text("'Okhla Market Area, New Delhi'"), nullable=True),
        sa.Column("category", sa.String(), server_default=sa.text("'General Store'"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name="fk_shops_owner_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_shops"),
    )
    op.create_index("ix_shops_owner_id", "shops", ["owner_id"], unique=False)

    op.create_table(
        "jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("shop_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("category", sa.String(), server_default=sa.text("'Store Helper'"), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("pay_amount", sa.Float(), server_default=sa.text("349.0"), nullable=False),
        sa.Column("duration_type", sa.String(), server_default=sa.text("'Full Shift (8 hrs)'"), nullable=False),
        sa.Column("scheduled_date", sa.String(), server_default=sa.text("'Today'"), nullable=True),
        sa.Column("location", sa.String(), server_default=sa.text("'Okhla Market Area'"), nullable=True),
        sa.Column("pickup_location", sa.String(), nullable=True),
        sa.Column("drop_location", sa.String(), nullable=True),
        sa.Column("is_delivery", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("status", sa.String(), server_default=sa.text("'open'"), nullable=False),
        sa.Column("assigned_worker_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], name="fk_jobs_shop_id_shops"),
        sa.ForeignKeyConstraint(["assigned_worker_id"], ["users.id"], name="fk_jobs_assigned_worker_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_jobs"),
    )
    op.create_index("ix_jobs_shop_id", "jobs", ["shop_id"], unique=False)
    op.create_index("ix_jobs_assigned_worker_id", "jobs", ["assigned_worker_id"], unique=False)
    op.create_index("ix_jobs_created_at", "jobs", [sa.text("created_at DESC")], unique=False)
    op.create_index(
        "ix_jobs_status_created_at",
        "jobs",
        ["status", sa.text("created_at DESC")],
        unique=False,
    )

    op.create_table(
        "applications",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("worker_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], name="fk_applications_job_id_jobs"),
        sa.ForeignKeyConstraint(["worker_id"], ["users.id"], name="fk_applications_worker_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_applications"),
    )
    op.create_index("uq_applications_job_worker", "applications", ["job_id", "worker_id"], unique=True)
    op.create_index("ix_applications_worker_id", "applications", ["worker_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_applications_worker_id", table_name="applications")
    op.drop_index("uq_applications_job_worker", table_name="applications")
    op.drop_table("applications")
    op.drop_index("ix_jobs_status_created_at", table_name="jobs")
    op.drop_index("ix_jobs_created_at", table_name="jobs")
    op.drop_index("ix_jobs_assigned_worker_id", table_name="jobs")
    op.drop_index("ix_jobs_shop_id", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index("ix_shops_owner_id", table_name="shops")
    op.drop_table("shops")
    op.drop_index("ix_otps_phone_number", table_name="otps")
    op.drop_table("otps")
    op.drop_index("ix_users_firebase_uid", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_phone_number", table_name="users")
    op.drop_table("users")
