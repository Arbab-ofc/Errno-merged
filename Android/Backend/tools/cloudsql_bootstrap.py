"""Initialize a new beta Cloud SQL database with the least-privilege app role.

Run this only as a one-off Cloud Run Job attached to the target Cloud SQL
instance. PostgreSQL admin credentials are injected from Secret Manager; this
script does not emit credentials or accept arbitrary SQL from the environment.
"""

import os
import sys

import psycopg2
from psycopg2 import sql

CANONICAL_BASELINE_REVISION = "1c64eb87a321"


def assert_empty_initial_database(cursor) -> None:
    """Refuse to bootstrap over any existing schema or PostGIS installation."""
    cursor.execute("SELECT to_regclass('public.alembic_version')")
    if cursor.fetchone()[0] is not None:
        raise RuntimeError("Refusing bootstrap because canonical migrations have already started.")

    cursor.execute(
        """
        SELECT relation.relname
        FROM pg_catalog.pg_class AS relation
        JOIN pg_catalog.pg_namespace AS namespace ON namespace.oid = relation.relnamespace
        WHERE namespace.nspname = 'public'
          AND relation.relkind IN ('r', 'p', 'v', 'm', 'f', 'S')
        """
    )
    if cursor.fetchall():
        raise RuntimeError("Refusing bootstrap because the public schema is not empty.")

    cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'postgis'")
    if cursor.fetchone() is not None:
        raise RuntimeError("Refusing bootstrap because PostGIS is already installed; no extension will be removed.")


def main() -> None:
    host = os.environ["PGHOST"]
    password = os.environ["PGPASSWORD"]
    database_name = os.environ["APP_DB_NAME"]
    app_user = os.environ["APP_DB_USER"]
    port = int(os.environ.get("PGPORT", "5432"))

    admin = psycopg2.connect(
        dbname="postgres", user="postgres", password=password, host=host, port=port
    )
    admin.autocommit = True
    try:
        with admin.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database_name,))
            exists = cursor.fetchone() is not None
            if not exists:
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
            else:
                cursor.execute(
                    "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = %s",
                    (database_name,),
                )
                if cursor.fetchone()[0] not in {"postgres", app_user}:
                    raise RuntimeError("Existing beta database has an unexpected owner.")
    finally:
        admin.close()

    admin = psycopg2.connect(
        dbname=database_name, user="postgres", password=password, host=host, port=port
    )
    admin.autocommit = True
    try:
        with admin.cursor() as cursor:
            if len(sys.argv) > 1 and sys.argv[1] == "--enable-postgis":
                cursor.execute("SELECT version_num FROM public.alembic_version")
                versions = [row[0] for row in cursor.fetchall()]
                if versions != [CANONICAL_BASELINE_REVISION]:
                    raise RuntimeError("PostGIS setup requires exactly the canonical baseline revision.")
                cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis")
                print("PostGIS extension enabled after the canonical baseline migration.")
                return

            assert_empty_initial_database(cursor)
            cursor.execute(
                sql.SQL("GRANT CONNECT, CREATE, TEMPORARY ON DATABASE {} TO {}").format(
                    sql.Identifier(database_name), sql.Identifier(app_user)
                )
            )
            cursor.execute(
                sql.SQL("GRANT USAGE, CREATE ON SCHEMA public TO {}").format(sql.Identifier(app_user))
            )
    finally:
        admin.close()
    print("Cloud SQL beta database access is initialized.")


if __name__ == "__main__":
    main()
