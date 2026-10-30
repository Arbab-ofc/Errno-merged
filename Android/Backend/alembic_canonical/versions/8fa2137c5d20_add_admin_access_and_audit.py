"""Add operator-provisioned administrator access and audit records.

Revision ID: 8fa2137c5d20
Revises: 1c64eb87a321
"""

from alembic import op
import sqlalchemy as sa


revision = "8fa2137c5d20"
down_revision = "1c64eb87a321"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_permissions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("firebase_uid", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("permissions", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("granted_by_uid", sa.String(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_admin_permissions"),
    )
    op.create_index("ix_admin_permissions_firebase_uid", "admin_permissions", ["firebase_uid"], unique=True)
    op.create_index("ix_admin_permissions_active", "admin_permissions", ["active"], unique=False)

    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("administrator_uid", sa.String(), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=120), nullable=True),
        sa.Column("outcome", sa.String(length=20), server_default=sa.text("'success'"), nullable=False),
        sa.Column("metadata", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_admin_audit_logs"),
    )
    op.create_index("ix_admin_audit_logs_administrator_uid", "admin_audit_logs", ["administrator_uid"], unique=False)
    op.create_index("ix_admin_audit_logs_created_at", "admin_audit_logs", ["created_at"], unique=False)
    op.create_index(
        "ix_admin_audit_resource_created",
        "admin_audit_logs",
        ["resource_type", "resource_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_admin_audit_resource_created", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_created_at", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_administrator_uid", table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")
    op.drop_index("ix_admin_permissions_active", table_name="admin_permissions")
    op.drop_index("ix_admin_permissions_firebase_uid", table_name="admin_permissions")
    op.drop_table("admin_permissions")
