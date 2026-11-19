import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from db_base import Base
from config_env import load_backend_environment

# Process environment has priority; root .env supplies local development values.
load_backend_environment()

DATABASE_URL = os.getenv("DATABASE_URL")

DEFAULT_SUPABASE_CA = Path(__file__).with_name("certs") / "supabase-prod-ca-2021.crt"


def _verified_postgres_url(database_url: str, ca_path: str | None = None):
    """Verify direct PostgreSQL TLS, or trust the attached Cloud SQL connector."""
    url = make_url(database_url)
    if url.get_backend_name() not in ("postgresql", "postgres"):
        raise RuntimeError("DATABASE_URL must use PostgreSQL for verified TLS.")

    cloud_sql_name = os.getenv("CLOUD_SQL_CONNECTION_NAME", "").strip()
    socket_host = url.query.get("host", "")
    cloud_sql_socket = f"/cloudsql/{cloud_sql_name}" if cloud_sql_name else ""
    if socket_host.startswith("/cloudsql/"):
        if not cloud_sql_socket or socket_host != cloud_sql_socket:
            raise RuntimeError("Cloud SQL socket must match CLOUD_SQL_CONNECTION_NAME.")
        # Cloud Run's attached Cloud SQL connector authenticates the instance
        # and encrypts the tunnel. The local Unix socket is the connector's
        # endpoint, so libpq must not attempt a second hostname TLS check.
        query = dict(url.query)
        query.pop("sslrootcert", None)
        query["sslmode"] = "disable"
        return url.set(query=query)

    configured_ca = (
        ca_path
        if ca_path is not None
        else url.query.get("sslrootcert")
        or os.getenv("PGSSLROOTCERT")
        or os.getenv("ERRNO_PGSSLROOTCERT")
        or str(DEFAULT_SUPABASE_CA)
    )
    ca_file = Path(configured_ca).expanduser().resolve()
    if not ca_file.is_file():
        raise RuntimeError("A trusted PostgreSQL CA file is required for verify-full connections.")

    query = dict(url.query)
    query.update(sslmode="verify-full", sslrootcert=str(ca_file))
    return url.set(query=query)


engine = None
if DATABASE_URL and make_url(DATABASE_URL).get_backend_name() in ("postgresql", "postgres"):
    verified_url = _verified_postgres_url(DATABASE_URL)
    pg_engine = create_engine(
        verified_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )
    try:
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        pg_engine.dispose()
        raise RuntimeError(
            "PostgreSQL connection failed; verified TLS is required and SQLite fallback is disabled."
        ) from None
    engine = pg_engine
    print("Connected to PostgreSQL with TLS certificate and hostname verification")

if engine is None:
    if os.getenv("ERRNO_REQUIRE_POSTGRES", "").strip().lower() in {"1", "true", "yes", "on"}:
        raise RuntimeError("This deployment requires a PostgreSQL DATABASE_URL; SQLite fallback is disabled.")
    engine = create_engine("sqlite:///./errno.db", connect_args={"check_same_thread": False})
    print("Connected to SQLite Local Database (errno.db)")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
