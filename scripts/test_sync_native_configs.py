from __future__ import annotations

import importlib.util
import os
import stat
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).with_name("sync_native_configs.py")
spec = importlib.util.spec_from_file_location("sync_native_configs", SCRIPT)
sync = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = sync
spec.loader.exec_module(sync)


def make_root(tmp_path: Path, env: str, example: str | None = None) -> Path:
    (tmp_path / ".env").write_text(env)
    if example is not None:
        (tmp_path / ".env.example").write_text(example)
    return tmp_path


def test_dotenv_parsing_quoted_values_comments_and_special_characters(tmp_path):
    root = make_root(tmp_path, 'EMPTY=\nQUOTED="value # with spaces" # trailing\nSPECIAL="a$\\\\b\\\"c"\n')
    values = sync._read_dotenv(root / ".env")
    assert values == {"EMPTY": "", "QUOTED": "value # with spaces", "SPECIAL": 'a$\\b"c'}


def test_dotenv_duplicate_names_fail_without_values_in_error(tmp_path):
    root = make_root(tmp_path, "TOKEN=first\nTOKEN=second\n")
    with pytest.raises(sync.ConfigError, match="Duplicate variable names.*TOKEN"):
        sync._read_dotenv(root / ".env")


def test_initial_migration_fills_only_empty_root_values_and_preserves_local(tmp_path):
    root = make_root(tmp_path, "DATABASE_URL=\nKEEP=original\n", "DATABASE_URL=\nKEEP=\n")
    backend = root / "Android/Backend/.env"
    backend.parent.mkdir(parents=True)
    backend.write_text('DATABASE_URL="postgresql://local:pass@localhost/db"\nEXTRA=kept\n')
    result = sync.inspect_configuration(root)
    assert set(result.migrations) == {"DATABASE_URL", "EXTRA"}
    assert sync._migrate_root(root, result.migrations)
    assert sync._read_dotenv(root / ".env")["DATABASE_URL"] == "postgresql://local:pass@localhost/db"
    assert sync._read_dotenv(root / ".env")["EXTRA"] == "kept"
    assert "EXTRA=kept" in backend.read_text()
    assert sync.inspect_configuration(root).conflicts == ()


def test_root_local_conflict_is_reported_by_name_without_secret_values(tmp_path):
    root = make_root(tmp_path, "VITE_API_BASE_URL=https://root.invalid\n", "VITE_API_BASE_URL=\n")
    admin = root / "Admin/.env.local"
    admin.parent.mkdir()
    admin.write_text("VITE_API_BASE_URL=https://local.invalid\n")
    result = sync.inspect_configuration(root)
    assert result.conflicts == ("VITE_API_BASE_URL (Admin/.env.local)",)


def test_mobile_api_urls_migrate_to_platform_specific_root_names(tmp_path):
    root = make_root(tmp_path, "ERRNO_API_BASE_URL=\n", "ERRNO_API_BASE_URL=\n")
    android = root / "Android/gradle.properties.local"
    ios = root / "iOS/Local.xcconfig"
    android.parent.mkdir()
    ios.parent.mkdir()
    android.write_text("ERRNO_API_BASE_URL=http\\://android.invalid\n")
    ios.write_text("ERRNO_API_BASE_URL = https://ios.invalid\n")
    result = sync.inspect_configuration(root)
    assert result.conflicts == ()
    assert set(result.migrations) == {"ERRNO_API_BASE_URL_ANDROID", "ERRNO_API_BASE_URL_IOS"}


def test_empty_optional_variables_do_not_block_backend_target(tmp_path):
    root = make_root(tmp_path, "CLOUDINARY_API_SECRET=\n")
    assert sync.run(root, mode="check", targets=("backend",)) == 0


def test_required_api_value_is_checked_per_client_target(tmp_path, capsys):
    root = make_root(tmp_path, "ERRNO_API_BASE_URL=\n")
    assert sync.run(root, mode="check", targets=("android",)) != 0
    assert "ERRNO_API_BASE_URL" in capsys.readouterr().err


def test_android_mapping_uses_only_allowlisted_public_keys(tmp_path):
    root = make_root(tmp_path, "ERRNO_API_BASE_URL=https://api.invalid\nERRNO_GOOGLE_MAPS_ANDROID_API_KEY=public-map\nCLOUDINARY_API_SECRET=must-not-leak\n")
    target = root / "Android/gradle.properties.local"
    content = sync._render_managed(target, {key: sync._read_dotenv(root / ".env").get(key, default) for key, default in sync.ANDROID.items()}, "properties")
    assert "ERRNO_API_BASE_URL=https\\://api.invalid" in content
    assert "CLOUDINARY_API_SECRET" not in content
    assert "must-not-leak" not in content


def test_xcconfig_escaping_covers_backslash_hash_and_spaces():
    assert sync._xcconfig_escape(r"key# part\name") == r"key\#\ part\\name"


def test_admin_allowlist_rejects_unapproved_vite_setting(tmp_path):
    root = make_root(tmp_path, "VITE_API_BASE_URL=https://api.invalid\nVITE_PRIVATE_TOKEN=not-allowed\n")
    assert sync._validate_secret_allowlist("admin", sync._read_dotenv(root / ".env")) == ["VITE_PRIVATE_TOKEN"]


def test_atomic_write_is_idempotent_private_and_preserves_existing_mode(tmp_path, monkeypatch):
    path = tmp_path / "local.env"
    replacements = []
    original_replace = sync.os.replace

    def record_replace(source, destination):
        replacements.append((Path(source).parent, Path(destination)))
        original_replace(source, destination)

    monkeypatch.setattr(sync.os, "replace", record_replace)
    assert sync._atomic_write(path, "TOKEN=synthetic\n")
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert replacements == [(tmp_path, path)]
    assert not sync._atomic_write(path, "TOKEN=synthetic\n")
    assert list(tmp_path.glob("*.tmp")) == []
    path.chmod(0o640)
    sync._atomic_write(path, "TOKEN=changed\n")
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_sync_preserves_unrelated_local_entries_and_is_idempotent(tmp_path):
    root = make_root(tmp_path, "ERRNO_API_BASE_URL=https://api.invalid\n")
    target = root / "Android/gradle.properties.local"
    target.parent.mkdir()
    target.write_text("# custom local comment\nUNRELATED=value\n")
    values = {key: sync._read_dotenv(root / ".env").get(key, default) for key, default in sync.ANDROID.items()}
    first = sync._render_managed(target, values, "properties")
    assert sync._atomic_write(target, first)
    assert not sync._atomic_write(target, sync._render_managed(target, values, "properties"))
    assert "UNRELATED=value" in target.read_text()
    assert "# custom local comment" in target.read_text()


def test_check_mode_does_not_modify_stale_file(tmp_path):
    root = make_root(tmp_path, "ERRNO_API_BASE_URL=https://new.invalid\n")
    android = root / "Android/gradle.properties.local"
    android.parent.mkdir()
    android.write_text("ERRNO_API_BASE_URL=https://old.invalid\n")
    before = android.read_bytes()
    assert sync.run(root, mode="check", targets=("android",)) != 0
    assert android.read_bytes() == before


def test_sync_mode_reports_names_only_and_excludes_backend_secrets(tmp_path, capsys):
    root = make_root(tmp_path, "ERRNO_API_BASE_URL=https://api.invalid\nCLOUDINARY_API_SECRET=synthetic-secret\n")
    assert sync.run(root, mode="sync", targets=("android",)) == 0
    output = capsys.readouterr().out
    generated = (root / "Android/gradle.properties.local").read_text()
    assert "ERRNO_API_BASE_URL" in output
    assert "synthetic-secret" not in output + generated
    assert "CLOUDINARY_API_SECRET" not in generated


def test_unrelated_local_config_is_not_rewritten_by_migration(tmp_path):
    root = make_root(tmp_path, "DATABASE_URL=\n", "DATABASE_URL=\n")
    local = root / "Android/Backend/.env"
    local.parent.mkdir(parents=True)
    original = "DATABASE_URL=postgresql://local/db\nCUSTOM=untouched\n"
    local.write_text(original)
    result = sync.inspect_configuration(root)
    sync._migrate_root(root, result.migrations)
    assert local.read_text() == original


def test_backend_process_environment_wins_over_root_dotenv(tmp_path, monkeypatch):
    backend_dir = Path(__file__).parents[1] / "Android/Backend"
    sys.path.insert(0, str(backend_dir))
    try:
        import config_env
        monkeypatch.setattr(config_env, "ROOT_ENV_FILE", tmp_path / ".env")
        (tmp_path / ".env").write_text("ERRNO_TEST_PRECEDENCE=root-value\n")
        monkeypatch.setenv("ERRNO_TEST_PRECEDENCE", "process-value")
        config_env.load_backend_environment()
        assert os.environ["ERRNO_TEST_PRECEDENCE"] == "process-value"
    finally:
        sys.path.remove(str(backend_dir))


def test_backend_root_dotenv_supplies_missing_process_setting(tmp_path, monkeypatch):
    backend_dir = Path(__file__).parents[1] / "Android/Backend"
    sys.path.insert(0, str(backend_dir))
    try:
        import config_env
        monkeypatch.setattr(config_env, "ROOT_ENV_FILE", tmp_path / ".env")
        (tmp_path / ".env").write_text("ERRNO_TEST_PRECEDENCE=root-value\n")
        monkeypatch.delenv("ERRNO_TEST_PRECEDENCE", raising=False)
        config_env.load_backend_environment()
        assert os.environ["ERRNO_TEST_PRECEDENCE"] == "root-value"
    finally:
        sys.path.remove(str(backend_dir))


def test_backend_empty_root_setting_does_not_mask_application_default(tmp_path, monkeypatch):
    backend_dir = Path(__file__).parents[1] / "Android/Backend"
    sys.path.insert(0, str(backend_dir))
    try:
        import config_env
        monkeypatch.setattr(config_env, "ROOT_ENV_FILE", tmp_path / ".env")
        (tmp_path / ".env").write_text("ERRNO_TEST_PRECEDENCE=\n")
        monkeypatch.delenv("ERRNO_TEST_PRECEDENCE", raising=False)
        config_env.load_backend_environment()
        assert "ERRNO_TEST_PRECEDENCE" not in os.environ
    finally:
        sys.path.remove(str(backend_dir))


def test_explicit_local_url_adoption_keeps_android_and_ios_distinct(tmp_path):
    root = make_root(
        tmp_path,
        "ERRNO_API_BASE_URL=https://shared.invalid\nVITE_API_BASE_URL=https://root-admin.invalid\n",
    )
    android = root / "Android/gradle.properties.local"
    ios = root / "iOS/Local.xcconfig"
    admin = root / "Admin/.env.local"
    for path in (android, ios, admin):
        path.parent.mkdir(parents=True, exist_ok=True)
    android.write_text("ERRNO_API_BASE_URL=https\\://android.invalid\n")
    ios.write_text("ERRNO_API_BASE_URL = https://ios.invalid\n")
    admin.write_text("VITE_API_BASE_URL=https://admin.invalid\n")
    names = sync._adopt_local_api_urls(root)
    values = sync._read_dotenv(root / ".env")
    assert names == ("ERRNO_API_BASE_URL_ANDROID", "ERRNO_API_BASE_URL_IOS", "VITE_API_BASE_URL")
    assert values["ERRNO_API_BASE_URL_ANDROID"] == "https://android.invalid"
    assert values["ERRNO_API_BASE_URL_IOS"] == "https://ios.invalid"
    assert values["VITE_API_BASE_URL"] == "https://admin.invalid"


def test_admin_output_does_not_include_arbitrary_root_variables(tmp_path):
    root = make_root(tmp_path, "VITE_API_BASE_URL=https://api.invalid\nCLOUDINARY_API_SECRET=private\nDATABASE_URL=postgresql://private/db\n")
    content = sync._render_managed(root / "Admin/.env.local", sync.ADMIN, "dotenv")
    assert "CLOUDINARY" not in content
    assert "DATABASE_URL" not in content
    assert "private" not in content


def test_gateway_output_contains_only_gateway_allowlist(tmp_path):
    root = make_root(
        tmp_path,
        "WHATSAPP_GATEWAY_INTERNAL_AUTH_SECRET=gateway-secret\nCLOUDINARY_API_SECRET=cloudinary-secret\nDATABASE_URL=postgresql://private/db\n",
    )
    root_values = sync._read_dotenv(root / ".env")
    content = sync._render_managed(
        root / "WhatsAppGateway/.env.local",
        {key: root_values.get(key, default) for key, default in sync.GATEWAY.items()},
        "dotenv",
    )
    assert "WHATSAPP_GATEWAY_INTERNAL_AUTH_SECRET" in content
    assert "gateway-secret" in content
    assert "CLOUDINARY" not in content
    assert "DATABASE_URL" not in content
    assert "cloudinary-secret" not in content
    assert "postgresql://private/db" not in content


def test_check_fails_for_missing_root_example_names(tmp_path):
    root = make_root(tmp_path, "KNOWN=value\n", "KNOWN=value\nEXPECTED=\n")
    with pytest.raises(sync.ConfigError, match="EXPECTED"):
        sync.inspect_configuration(root)


def test_admin_sync_does_not_require_backend_only_catalog_names(tmp_path):
    root = make_root(
        tmp_path,
        "VITE_API_BASE_URL=http://localhost:8000\n",
        "VITE_API_BASE_URL=http://localhost:8000\nWHATSAPP_GATEWAY_CA_BUNDLE=\nWHATSAPP_GATEWAY_MANAGEMENT_ENABLED=false\n",
    )

    assert sync.run(root, mode="sync", targets=("admin",)) == 0
    generated = root / "Admin/.env.local"
    assert generated.is_file()
    assert "WHATSAPP_GATEWAY" not in generated.read_text()

    with pytest.raises(sync.ConfigError, match="WHATSAPP_GATEWAY_CA_BUNDLE"):
        sync.inspect_configuration(root)


def test_android_sync_does_not_require_backend_only_catalog_names(tmp_path):
    root = make_root(
        tmp_path,
        "ERRNO_API_BASE_URL_ANDROID=https://api.invalid\n",
        "ERRNO_API_BASE_URL_ANDROID=\nWHATSAPP_GATEWAY_CA_BUNDLE=\nWHATSAPP_GATEWAY_MANAGEMENT_ENABLED=false\n",
    )

    assert sync.run(root, mode="sync", targets=("android",)) == 0
    generated = root / "Android/gradle.properties.local"
    assert generated.is_file()
    assert "ERRNO_API_BASE_URL=https\\://api.invalid" in generated.read_text()
    assert "WHATSAPP_GATEWAY" not in generated.read_text()

    with pytest.raises(sync.ConfigError, match="WHATSAPP_GATEWAY_CA_BUNDLE"):
        sync.inspect_configuration(root)


def test_cli_rejects_nonexclusive_modes():
    with pytest.raises(SystemExit) as error:
        sync.main(["--check", "--sync"])
    assert error.value.code == 2


def test_cli_rejects_local_adoption_in_check_mode():
    with pytest.raises(SystemExit) as error:
        sync.main(["--check", "--adopt-local-urls"])
    assert error.value.code == 2
