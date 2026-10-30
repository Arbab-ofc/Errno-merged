from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import _verified_postgres_url  # noqa: E402


def test_postgres_url_forces_verify_full_and_trusted_ca(tmp_path):
    ca_file = tmp_path / "trusted-root.crt"
    ca_file.write_text("test CA placeholder")

    url = _verified_postgres_url(
        "postgresql+psycopg2://example.test/postgres",
        str(ca_file),
    )

    assert url.query["sslmode"] == "verify-full"
    assert url.query["sslrootcert"] == str(ca_file.resolve())


def test_postgres_url_rejects_missing_ca_file(tmp_path):
    with pytest.raises(RuntimeError, match="trusted PostgreSQL CA"):
        _verified_postgres_url(
            "postgresql+psycopg2://example.test/postgres",
            str(tmp_path / "missing.crt"),
        )
