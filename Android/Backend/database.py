import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from db_base import Base

load_dotenv(Path(__file__).with_name(".env"))

DATABASE_URL = os.getenv("DATABASE_URL")

DEFAULT_SUPABASE_CA = Path(__file__).with_name("certs") / "supabase-prod-ca-2021.crt"


def _verified_postgres_url(database_url: str, ca_path: str | None = None):
    """Force libpq to verify both the PostgreSQL certificate and hostname."""
    url = make_url(database_url)
    if url.get_backend_name() not in ("postgresql", "postgres"):
        raise RuntimeError("DATABASE_URL must use PostgreSQL for verified TLS.")

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
    engine = create_engine("sqlite:///./errno.db", connect_args={"check_same_thread": False})
    print("Connected to SQLite Local Database (errno.db)")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
