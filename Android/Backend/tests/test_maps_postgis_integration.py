"""Read-only PostGIS verification for the dedicated disposable errno_phase22_test DB."""
import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

@pytest.fixture(scope="module")
def postgis_db():
    raw=os.environ.get("ERRNO_TEST_DATABASE_URL")
    if not raw: pytest.skip("ERRNO_TEST_DATABASE_URL is not configured")
    url=make_url(raw)
    if url.get_backend_name() not in ("postgresql","postgres") or url.host not in ("localhost","127.0.0.1","::1") or url.database!="errno_phase22_test":
        pytest.fail("PostGIS test accepts only the dedicated loopback errno_phase22_test database")
    engine=create_engine(url,pool_pre_ping=True)
    try: yield engine
    finally: engine.dispose()

def test_map_migration_postgis_columns_and_gist_index(postgis_db):
    with postgis_db.connect() as db:
        assert db.execute(text("SELECT PostGIS_Full_Version()")).scalar_one()
        assert db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()=="fb4a6c90d112"
        indexes={row[0] for row in db.execute(text("SELECT indexname FROM pg_indexes WHERE schemaname='public' AND tablename='worker_live_locations'"))}
        assert "ix_worker_live_locations_location_gist" in indexes
        columns={row[0] for row in db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='jobs'"))}
        assert {"latitude","longitude","booking_type","scheduled_at","dispatch_at","prebooking_dispatch_status"} <= columns

def test_postgis_nearby_distance_and_radius_boundary(postgis_db):
    with postgis_db.connect() as db:
        within, outside = db.execute(text("""
            SELECT ST_DWithin(origin, nearby, 5000), ST_DWithin(origin, far, 5000)
            FROM (SELECT ST_SetSRID(ST_MakePoint(85.3240,27.7172),4326)::geography origin,
                         ST_SetSRID(ST_MakePoint(85.3340,27.7172),4326)::geography nearby,
                         ST_SetSRID(ST_MakePoint(85.3840,27.7172),4326)::geography far) points
        """)).one()
        assert within is True
        assert outside is False
