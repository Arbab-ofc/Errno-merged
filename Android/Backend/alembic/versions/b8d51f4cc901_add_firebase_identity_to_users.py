"""Add Firebase identity mapping for Google authenticated users."""
from alembic import op
import sqlalchemy as sa

revision = "b8d51f4cc901"
down_revision = "74231e067d69"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(), nullable=True))
    op.add_column("users", sa.Column("firebase_uid", sa.String(), nullable=True))
    op.create_index("ix_users_firebase_uid", "users", ["firebase_uid"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.alter_column("users", "phone_number", existing_type=sa.String(), nullable=True)
    op.alter_column("users", "role", existing_type=sa.Enum("shop_owner", "worker", name="userrole"), nullable=True)


def downgrade() -> None:
    # Refuse lossy downgrade if Firebase-only accounts have been created.
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT 1 FROM users WHERE firebase_uid IS NOT NULL LIMIT 1")).first():
        raise RuntimeError("Cannot remove Firebase identities while Firebase-backed users exist")
    op.alter_column("users", "role", existing_type=sa.Enum("shop_owner", "worker", name="userrole"), nullable=False)
    op.alter_column("users", "phone_number", existing_type=sa.String(), nullable=False)
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_firebase_uid", table_name="users")
    op.drop_column("users", "firebase_uid")
    op.drop_column("users", "email")
