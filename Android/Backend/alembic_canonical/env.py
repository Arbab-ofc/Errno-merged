"""Alembic environment for the canonical ERRNO application schema.

This environment deliberately requires an explicit database URL. Local
disposable PostgreSQL is allowed only with an explicit opt-in and the expected
test database name. Non-local connections always require TLS verify-full and a
CA file.
"""

from logging.config import fileConfig
import os
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url

from db_base import Base
import models  # noqa: F401 - registers only active canonical model tables.

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _database_url() -> str:
    raw_url = os.environ.get("ERRNO_DATABASE_URL")
    if not raw_url:
        raise RuntimeError(
            "Set ERRNO_DATABASE_URL explicitly; this migration environment does not load .env."
        )

    url = make_url(raw_url)
    if url.get_backend_name() not in ("postgresql", "postgres"):
        raise RuntimeError("Canonical migrations require PostgreSQL.")

    is_loopback = url.host in ("localhost", "127.0.0.1", "::1")
    is_explicit_test = (
        is_loopback
        and url.database == "errno_phase22_test"
        and os.environ.get("ERRNO_ALLOW_LOCAL_TEST_DB") == "1"
    )
    if is_explicit_test:
        return raw_url

    if os.environ.get("ERRNO_ALLOW_CANONICAL_MIGRATION") != "1":
        raise RuntimeError(
            "Non-local migrations require explicit ERRNO_ALLOW_CANONICAL_MIGRATION=1 approval."
        )

    ca_path = os.environ.get("ERRNO_PGSSLROOTCERT")
    if not ca_path or not Path(ca_path).is_file():
        raise RuntimeError(
            "Non-local canonical migrations require ERRNO_PGSSLROOTCERT to name a trusted CA file."
        )
    query = dict(url.query)
    query.update(sslmode="verify-full", sslrootcert=str(Path(ca_path).resolve()))
    return url.set(query=query).render_as_string(hide_password=False)


config.set_main_option(
    "sqlalchemy.url", _database_url().replace("%", "%%")
)
target_metadata = Base.metadata


def include_object(object_, name, type_, reflected, compare_to):
    """Keep Supabase-managed and extension objects outside this app baseline."""
    if type_ == "table" and object_.schema not in (None, "public"):
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
