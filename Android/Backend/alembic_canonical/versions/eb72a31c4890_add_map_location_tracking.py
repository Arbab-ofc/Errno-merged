"""Add job map coordinates and booking-bound worker location storage."""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geography

revision = "eb72a31c4890"
down_revision = "a8b72c4e9d11"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.add_column("jobs", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("jobs", sa.Column("longitude", sa.Float(), nullable=True))
    op.create_check_constraint("ck_jobs_map_coordinates_pair", "jobs", "(latitude IS NULL AND longitude IS NULL) OR (latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180)")
    op.create_table(
        "worker_live_locations",
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("job_id", sa.String(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("location", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180", name="ck_worker_live_location_coordinates"),
    )
    op.create_index("ix_worker_live_locations_job_id", "worker_live_locations", ["job_id"])
    op.create_index("ix_worker_live_locations_updated_at", "worker_live_locations", ["updated_at"])
    op.create_index("ix_worker_live_locations_location_gist", "worker_live_locations", ["location"], postgresql_using="gist")

def downgrade() -> None:
    op.drop_index("ix_worker_live_locations_location_gist", table_name="worker_live_locations")
    op.drop_index("ix_worker_live_locations_updated_at", table_name="worker_live_locations")
    op.drop_index("ix_worker_live_locations_job_id", table_name="worker_live_locations")
    op.drop_table("worker_live_locations")
    op.drop_constraint("ck_jobs_map_coordinates_pair", "jobs", type_="check")
    op.drop_column("jobs", "longitude")
    op.drop_column("jobs", "latitude")
