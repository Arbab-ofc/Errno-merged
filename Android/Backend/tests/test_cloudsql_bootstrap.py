from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.cloudsql_bootstrap import assert_empty_initial_database


class CatalogCursor:
    def __init__(self, *, migration_table=None, relations=(), postgis=False):
        self.migration_table = migration_table
        self.relations = list(relations)
        self.postgis = postgis
        self.result = None
        self.statements = []

    def execute(self, statement):
        statement = str(statement)
        self.statements.append(statement)
        if "to_regclass('public.alembic_version')" in statement:
            self.result = [(self.migration_table,)]
        elif "pg_catalog.pg_class" in statement:
            self.result = [(name,) for name in self.relations]
        elif "pg_extension" in statement:
            self.result = [(1,)] if self.postgis else []
        else:
            raise AssertionError("Unexpected database statement in bootstrap guard")

    def fetchone(self):
        return self.result.pop(0) if self.result else None

    def fetchall(self):
        rows, self.result = self.result, []
        return rows


def test_cloudsql_bootstrap_allows_only_an_empty_database():
    cursor = CatalogCursor()

    assert_empty_initial_database(cursor)
    assert len(cursor.statements) == 3


@pytest.mark.parametrize(
    "catalog, message",
    [
        ({"migration_table": "alembic_version"}, "migrations have already started"),
        ({"relations": ("users",)}, "public schema is not empty"),
        ({"postgis": True}, "PostGIS is already installed"),
    ],
)
def test_cloudsql_bootstrap_refuses_existing_schema_state(catalog, message):
    cursor = CatalogCursor(**catalog)

    with pytest.raises(RuntimeError, match=message):
        assert_empty_initial_database(cursor)

    assert all(statement.lstrip().upper().startswith("SELECT") for statement in cursor.statements)
