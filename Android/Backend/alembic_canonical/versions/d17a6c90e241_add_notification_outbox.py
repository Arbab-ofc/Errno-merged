"""Add durable notifications, device registry, inbox and transactional outbox."""
from alembic import op
import sqlalchemy as sa

revision = "d17a6c90e241"
down_revision = "9f23b6c4d1a8"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("notifications",
        sa.Column("id",sa.String(),primary_key=True), sa.Column("recipient_user_id",sa.String(),sa.ForeignKey("users.id",ondelete="CASCADE"),nullable=False),
        sa.Column("recipient_role",sa.String(24),nullable=False), sa.Column("event_id",sa.String(64),nullable=False), sa.Column("event_type",sa.String(80),nullable=False),
        sa.Column("title",sa.String(180),nullable=False),sa.Column("body",sa.String(500),nullable=False),sa.Column("priority",sa.String(16),nullable=False,server_default="normal"),
        sa.Column("category",sa.String(32),nullable=False),sa.Column("data_payload",sa.JSON(),nullable=False,server_default=sa.text("'{}'")),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column("read_at",sa.DateTime(timezone=True)),sa.Column("expires_at",sa.DateTime(timezone=True)),
        sa.Column("deduplication_key",sa.String(300),nullable=False,unique=True))
    op.create_check_constraint("ck_notification_priority", "notifications", "priority IN ('low','normal','high')")
    op.create_check_constraint("ck_notification_category", "notifications", "category IN ('booking','job','payment','account','verification','marketing','admin')")
    op.create_index("ix_notifications_event_id","notifications",["event_id"])
    op.create_index("ix_notifications_recipient_created","notifications",["recipient_user_id","created_at","id"])
    op.create_index("ix_notifications_recipient_read","notifications",["recipient_user_id","read_at","created_at"])
    op.create_index("ix_notifications_category_created","notifications",["category","created_at"])
    op.create_table("notification_devices",
        sa.Column("id",sa.String(),primary_key=True),sa.Column("user_id",sa.String(),sa.ForeignKey("users.id",ondelete="CASCADE"),nullable=False),
        sa.Column("role",sa.String(24),nullable=False),sa.Column("platform",sa.String(12),nullable=False),sa.Column("device_identifier",sa.String(160),nullable=False),
        sa.Column("encrypted_token",sa.Text(),nullable=False),sa.Column("token_hash",sa.String(64),nullable=False,unique=True),sa.Column("app_version",sa.String(40)),
        sa.Column("active",sa.Boolean(),nullable=False,server_default=sa.true()),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column("last_seen_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column("invalidated_at",sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id","device_identifier",name="uq_notification_device_user_install"))
    op.create_check_constraint("ck_notification_device_platform", "notification_devices", "platform IN ('android','ios')")
    op.create_index("ix_notification_devices_user_id","notification_devices",["user_id"])
    op.create_index("ix_notification_devices_active","notification_devices",["active"])
    op.create_index("ix_notification_devices_user_active","notification_devices",["user_id","active"])
    op.create_table("notification_outbox",
        sa.Column("id",sa.String(),primary_key=True),sa.Column("notification_id",sa.String(),sa.ForeignKey("notifications.id",ondelete="CASCADE"),nullable=False,unique=True),
        sa.Column("event_id",sa.String(64),nullable=False),sa.Column("event_type",sa.String(80),nullable=False),sa.Column("recipient_user_id",sa.String(),sa.ForeignKey("users.id",ondelete="CASCADE"),nullable=False),
        sa.Column("payload",sa.JSON(),nullable=False,server_default=sa.text("'{}'")),sa.Column("status",sa.String(24),nullable=False,server_default="queued"),sa.Column("attempts",sa.Integer(),nullable=False,server_default="0"),
        sa.Column("next_attempt_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column("processed_at",sa.DateTime(timezone=True)),
        sa.Column("last_error_code",sa.String(80)),sa.Column("lease_owner",sa.String(80)),sa.Column("lease_until",sa.DateTime(timezone=True)),
        sa.UniqueConstraint("event_id","recipient_user_id","event_type",name="uq_notification_outbox_event_recipient"))
    op.create_check_constraint("ck_notification_outbox_status", "notification_outbox", "status IN ('queued','sending','retrying','accepted_by_fcm','permanently_failed','no_devices','suppressed','expired')")
    op.create_index("ix_notification_outbox_dispatch","notification_outbox",["status","next_attempt_at","created_at"])
    op.create_index("ix_notification_outbox_lease","notification_outbox",["status","lease_until"])
    op.create_table("notification_delivery_attempts",
        sa.Column("id",sa.String(),primary_key=True),sa.Column("notification_id",sa.String(),sa.ForeignKey("notifications.id",ondelete="CASCADE"),nullable=False),
        sa.Column("device_id",sa.String(),sa.ForeignKey("notification_devices.id",ondelete="SET NULL")),sa.Column("attempt_number",sa.Integer(),nullable=False),sa.Column("provider_message_id",sa.String(240)),
        sa.Column("status",sa.String(24),nullable=False),sa.Column("error_code",sa.String(80)),sa.Column("attempted_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column("next_retry_at",sa.DateTime(timezone=True)),
        sa.UniqueConstraint("notification_id","device_id","attempt_number",name="uq_notification_delivery_attempt"))
    op.create_check_constraint("ck_notification_delivery_status", "notification_delivery_attempts", "status IN ('accepted_by_fcm','invalid_token','failed')")
    op.create_index("ix_notification_delivery_attempts_notification_id","notification_delivery_attempts",["notification_id"])
    op.create_index("ix_notification_delivery_attempts_device_id","notification_delivery_attempts",["device_id"])
    op.create_table("notification_preferences",
        sa.Column("user_id",sa.String(),sa.ForeignKey("users.id",ondelete="CASCADE"),primary_key=True),sa.Column("booking_updates_enabled",sa.Boolean(),nullable=False,server_default=sa.true()),
        sa.Column("job_alerts_enabled",sa.Boolean(),nullable=False,server_default=sa.true()),sa.Column("payment_updates_enabled",sa.Boolean(),nullable=False,server_default=sa.true()),
        sa.Column("account_updates_enabled",sa.Boolean(),nullable=False,server_default=sa.true()),sa.Column("marketing_enabled",sa.Boolean(),nullable=False,server_default=sa.false()),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()))
    op.create_table("notification_registration_throttles",
        sa.Column("user_id",sa.String(),sa.ForeignKey("users.id",ondelete="CASCADE"),primary_key=True),
        sa.Column("window_started_at",sa.DateTime(timezone=True),nullable=False),sa.Column("attempts",sa.Integer(),nullable=False,server_default="0"))

def downgrade():
    op.drop_table("notification_registration_throttles")
    op.drop_table("notification_preferences")
    op.drop_index("ix_notification_delivery_attempts_device_id",table_name="notification_delivery_attempts")
    op.drop_index("ix_notification_delivery_attempts_notification_id",table_name="notification_delivery_attempts")
    op.drop_table("notification_delivery_attempts")
    op.drop_index("ix_notification_outbox_lease",table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_dispatch",table_name="notification_outbox")
    op.drop_table("notification_outbox")
    op.drop_index("ix_notification_devices_user_active",table_name="notification_devices")
    op.drop_index("ix_notification_devices_active",table_name="notification_devices")
    op.drop_index("ix_notification_devices_user_id",table_name="notification_devices")
    op.drop_table("notification_devices")
    op.drop_index("ix_notifications_category_created",table_name="notifications")
    op.drop_index("ix_notifications_recipient_read",table_name="notifications")
    op.drop_index("ix_notifications_recipient_created",table_name="notifications")
    op.drop_index("ix_notifications_event_id",table_name="notifications")
    op.drop_table("notifications")
