#!/usr/bin/env python3
"""Validate and synchronize ERRNO local configuration from root .env.

Only explicitly allowlisted public client settings are emitted to Android,
iOS, and Admin configuration. Backend secrets stay in root .env and are read
directly by FastAPI. Existing local values are migrated only into empty root
entries; conflicting values stop synchronization without changing files. The
one-time API URL adoption option is a separate explicit conflict resolution.
"""

from __future__ import annotations

import argparse
import os
import re
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from dotenv import dotenv_values
from dotenv.parser import parse_stream


ROOT = Path(__file__).resolve().parents[1]
ROOT_ENV = ".env"
EXAMPLE_ENV = ".env.example"
MANAGED_MARKER = "# Managed by scripts/sync_native_configs.py; edit root .env instead."
IOS_MANAGED_MARKER = "// Managed by scripts/sync_native_configs.py; edit root .env instead."

ANDROID = {
    "ERRNO_API_BASE_URL": "http://localhost:8000",
    "ERRNO_GOOGLE_MAPS_ANDROID_API_KEY": "",
    "ERRNO_PHOTON_ENDPOINT": "https://photon.komoot.io",
    "ERRNO_FIREBASE_AUTH_EMULATOR_HOST": "",
}
IOS = {
    "ERRNO_API_BASE_URL": "http://localhost:8000",
    "ERRNO_GOOGLE_MAPS_IOS_API_KEY": "",
    "ERRNO_PHOTON_ENDPOINT": "https://photon.komoot.io",
}
ADMIN = {
    "VITE_API_BASE_URL": "http://localhost:8000",
    "VITE_FIREBASE_API_KEY": "",
    "VITE_FIREBASE_AUTH_DOMAIN": "",
    "VITE_FIREBASE_PROJECT_ID": "",
    "VITE_FIREBASE_APP_ID": "",
}
GATEWAY = {
    "LOG_LEVEL": "info",
    "WHATSAPP_GATEWAY_INTERNAL_AUTH_SECRET": "",
    "WHATSAPP_GATEWAY_BIND": "127.0.0.1",
    "WHATSAPP_GATEWAY_PORT": "8787",
    "WHATSAPP_GATEWAY_SESSION_PATH": "./session",
    "WHATSAPP_GATEWAY_AUTOCONNECT": "true",
    "WHATSAPP_GATEWAY_QR_TTL_SECONDS": "60",
}
TARGET_FILES = {
    "android": ("Android/gradle.properties.local", ANDROID, "properties"),
    "ios": ("iOS/Local.xcconfig", IOS, "xcconfig"),
    "admin": ("Admin/.env.local", ADMIN, "dotenv"),
    "gateway": ("WhatsAppGateway/.env.local", GATEWAY, "dotenv"),
}
LOCAL_MIGRATION_FILES = (
    ("Android/Backend/.env", "dotenv"),
    ("Admin/.env.local", "dotenv"),
    ("WhatsAppGateway/.env.local", "dotenv"),
    ("Android/gradle.properties.local", "properties"),
    ("iOS/Local.xcconfig", "xcconfig"),
)
LOCAL_KEY_MIGRATIONS = {
    "Android/gradle.properties.local": {"ERRNO_API_BASE_URL": "ERRNO_API_BASE_URL_ANDROID"},
    "iOS/Local.xcconfig": {"ERRNO_API_BASE_URL": "ERRNO_API_BASE_URL_IOS"},
}
BACKEND_ONLY_PREFIXES = (
    "CLOUDINARY_", "RAZORPAY_", "DATABASE_", "ERRNO_DATABASE_", "PGSSL",
    "ERRNO_PGSSL", "JWT_", "FIREBASE_ADMIN_", "GOOGLE_APPLICATION_CREDENTIALS",
    "WHATSAPP_", "DIGILOCKER_", "KYC_", "NOTIFICATION_TOKEN_",
)


class ConfigError(Exception):
    """Configuration validation error with safe, value-free details."""


@dataclass(frozen=True)
class ConfigResult:
    root_values: dict[str, str]
    local_values: dict[str, dict[str, str]]
    migrations: dict[str, str]
    conflicts: tuple[str, ...]


def _read_dotenv(path: Path) -> dict[str, str]:
    try:
        with path.open(encoding="utf-8") as stream:
            parsed = list(parse_stream(stream))
    except OSError as exc:
        raise ConfigError(f"Cannot read {path}: {exc.strerror or 'I/O error'}") from None
    keys = [binding.key for binding in parsed if binding.key]
    malformed = [str(binding.original.line) for binding in parsed if binding.error]
    if malformed:
        raise ConfigError(f"Invalid dotenv syntax in {path} at line(s): {', '.join(malformed)}")
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        raise ConfigError(f"Duplicate variable names in {path}: {', '.join(duplicates)}")
    try:
        values = dotenv_values(path, interpolate=False, encoding="utf-8")
    except Exception as exc:
        raise ConfigError(f"Cannot parse {path}: {type(exc).__name__}") from None
    return {key: "" if value is None else str(value) for key, value in values.items()}


def _unescape_properties(value: str) -> str:
    output: list[str] = []
    escaped = False
    mapping = {"t": "\t", "n": "\n", "r": "\r", "f": "\f"}
    for char in value:
        if escaped:
            output.append(mapping.get(char, char))
            escaped = False
        elif char == "\\":
            escaped = True
        else:
            output.append(char)
    if escaped:
        output.append("\\")
    return "".join(output)


def _read_native(path: Path, fmt: str) -> dict[str, str]:
    if not path.exists():
        return {}
    if fmt == "dotenv":
        return _read_dotenv(path)
    values: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//")):
            continue
        if fmt == "properties":
            match = re.match(r"^\s*([^:=\s]+)\s*(?:=|:)\s*(.*)$", line)
            if not match:
                continue
            key, value = match.groups()
            value = _unescape_properties(value.strip())
        else:
            match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$", line)
            if not match:
                continue
            key, value = match.groups()
            value = value.replace("\\#", "#").replace("\\ ", " ").replace("\\\\", "\\")
        if key in values:
            raise ConfigError(f"Duplicate variable {key} in {path}:{number}")
        values[key] = value
    return values


def inspect_configuration(root: Path) -> ConfigResult:
    root_file = root / ROOT_ENV
    if not root_file.is_file():
        raise ConfigError(f"Missing {ROOT_ENV}; copy {EXAMPLE_ENV} before syncing.")
    root_values = _read_dotenv(root_file)
    example_file = root / EXAMPLE_ENV
    if example_file.is_file():
        example = _read_dotenv(example_file)
        missing = sorted(set(example) - set(root_values))
        if missing:
            raise ConfigError(f"Root .env is missing supported names from {EXAMPLE_ENV}: {', '.join(missing)}")

    local_values: dict[str, dict[str, str]] = {}
    conflicts: set[str] = set()
    candidates: dict[str, list[tuple[str, str]]] = {}
    for relative, fmt in LOCAL_MIGRATION_FILES:
        path = root / relative
        values = _read_native(path, fmt)
        local_values[relative] = values
        if path.exists():
            marker = IOS_MANAGED_MARKER if fmt == "xcconfig" else MANAGED_MARKER
            legacy_marker = "# Legacy local settings retained; FastAPI reads root .env instead."
            file_text = path.read_text(encoding="utf-8")
            if marker in file_text or (relative == "Android/Backend/.env" and legacy_marker in file_text):
                continue
        for key, value in values.items():
            if not value:
                continue
            destination = LOCAL_KEY_MIGRATIONS.get(relative, {}).get(key, key)
            root_value = root_values.get(destination, "")
            if root_value and root_value != value:
                conflicts.add(f"{destination} ({relative})")
            elif not root_value:
                candidates.setdefault(destination, []).append((relative, value))

    migrations: dict[str, str] = {}
    for key, entries in candidates.items():
        unique_values = {value for _, value in entries}
        if len(unique_values) > 1:
            conflicts.update(f"{key} ({relative})" for relative, _ in entries)
        elif not root_values.get(key, ""):
            migrations[key] = entries[0][1]
    return ConfigResult(root_values, local_values, migrations, tuple(sorted(conflicts)))


def _dotenv_quote(value: str) -> str:
    if value == "":
        return ""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
    return f'"{escaped}"'


def _properties_escape(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")
    for char in " :=#!":
        escaped = escaped.replace(char, "\\" + char)
    return escaped


def _xcconfig_escape(value: str) -> str:
    if "\n" in value or "\r" in value:
        raise ConfigError("Newlines are not supported in iOS build settings.")
    return value.replace("\\", "\\\\").replace("#", "\\#").replace(" ", "\\ ")


def _render_managed(path: Path, values: dict[str, str], fmt: str) -> str:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    managed = set(values)
    kept: list[str] = []
    for line in existing.splitlines():
        stripped = line.strip()
        if stripped in {MANAGED_MARKER, IOS_MANAGED_MARKER}:
            continue
        if fmt == "dotenv":
            match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
        else:
            match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:=|:)\s*", line)
        if match and match.group(1) in managed:
            continue
        kept.append(line)
    if kept and kept[-1].strip():
        kept.append("")
    marker = IOS_MANAGED_MARKER if fmt == "xcconfig" else MANAGED_MARKER
    kept.append(marker)
    for key, value in values.items():
        if fmt == "properties":
            kept.append(f"{key}={_properties_escape(value)}")
        elif fmt == "xcconfig":
            kept.append(f"{key} = {_xcconfig_escape(value)}")
        else:
            kept.append(f"{key}={_dotenv_quote(value)}")
    return "\n".join(kept).rstrip() + "\n"


def _atomic_write(path: Path, content: str, *, mode: int | None = None) -> bool:
    encoded = content.encode("utf-8")
    if path.exists() and path.read_bytes() == encoded:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    old_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        os.fchmod(fd, mode if mode is not None else min(old_mode, 0o600))
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
        return True
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _migrate_root(root: Path, migrations: dict[str, str]) -> bool:
    if not migrations:
        return False
    path = root / ROOT_ENV
    content = path.read_text(encoding="utf-8")
    for key, value in migrations.items():
        pattern = re.compile(rf"^(\s*{re.escape(key)}\s*=).*$", re.MULTILINE)
        replacement = lambda match, serialized=_dotenv_quote(value): match.group(1) + serialized
        if pattern.search(content):
            content = pattern.sub(replacement, content, count=1)
        else:
            content = content.rstrip() + f"\n{key}={_dotenv_quote(value)}\n"
    return _atomic_write(path, content)


def _adopt_local_api_urls(root: Path) -> tuple[str, ...]:
    """Apply an explicit one-time choice to keep existing client API URLs."""
    sources = (
        ("Android/gradle.properties.local", "properties", "ERRNO_API_BASE_URL", "ERRNO_API_BASE_URL_ANDROID"),
        ("iOS/Local.xcconfig", "xcconfig", "ERRNO_API_BASE_URL", "ERRNO_API_BASE_URL_IOS"),
        ("Admin/.env.local", "dotenv", "VITE_API_BASE_URL", "VITE_API_BASE_URL"),
    )
    updates: dict[str, str] = {}
    for relative, fmt, source_name, root_name in sources:
        value = _read_native(root / relative, fmt).get(source_name, "")
        if value:
            updates[root_name] = value
    if not updates:
        return ()
    path = root / ROOT_ENV
    _read_dotenv(path)  # Validate syntax and duplicate names before any write.
    content = path.read_text(encoding="utf-8")
    for key, value in updates.items():
        pattern = re.compile(rf"^(\s*{re.escape(key)}\s*=).*$", re.MULTILINE)
        replacement = lambda match, serialized=_dotenv_quote(value): match.group(1) + serialized
        if pattern.search(content):
            content = pattern.sub(replacement, content, count=1)
        else:
            content = content.rstrip() + f"\n{key}={_dotenv_quote(value)}\n"
    _atomic_write(path, content)
    return tuple(sorted(updates))


def _mark_legacy_backend_env(root: Path) -> None:
    path = root / "Android/Backend/.env"
    if not path.is_file():
        return
    content = path.read_text(encoding="utf-8")
    marker = "# Legacy local settings retained; FastAPI reads root .env instead."
    if marker not in content:
        _atomic_write(path, marker + "\n" + content)


def _check_required(values: dict[str, str], target: str) -> list[str]:
    required = {
        "android": ("ERRNO_API_BASE_URL_ANDROID", "ERRNO_API_BASE_URL"),
        "ios": ("ERRNO_API_BASE_URL_IOS", "ERRNO_API_BASE_URL"),
        "admin": ("VITE_API_BASE_URL",),
        "backend": (),
        "gateway": (),
    }
    if target in {"android", "ios"}:
        platform_key, shared_key = required[target]
        return [] if values.get(platform_key, "").strip() or values.get(shared_key, "").strip() else [platform_key]
    return [key for key in required[target] if not values.get(key, "").strip()]


def _target_values(target: str, root_values: dict[str, str]) -> dict[str, str]:
    _, mapping, _ = TARGET_FILES[target]
    values = {key: root_values.get(key, default) for key, default in mapping.items()}
    if target == "android":
        values["ERRNO_API_BASE_URL"] = root_values.get("ERRNO_API_BASE_URL_ANDROID", "") or root_values.get("ERRNO_API_BASE_URL", "http://localhost:8000")
    elif target == "ios":
        values["ERRNO_API_BASE_URL"] = root_values.get("ERRNO_API_BASE_URL_IOS", "") or root_values.get("ERRNO_API_BASE_URL", "http://localhost:8000")
    return values


def _validate_secret_allowlist(target: str, values: dict[str, str]) -> list[str]:
    if target == "admin":
        return sorted(key for key in values if key.startswith("VITE_") and key not in ADMIN)
    if target in {"android", "ios"}:
        mapping = ANDROID if target == "android" else IOS
        return sorted(key for key in mapping if any(key.startswith(prefix) for prefix in BACKEND_ONLY_PREFIXES))
    return []


def run(root: Path, *, mode: str, targets: Iterable[str], adopt_local_urls: bool = False) -> int:
    if mode == "sync" and adopt_local_urls:
        names = _adopt_local_api_urls(root)
        if names:
            print("Adopted existing client API URLs into root .env: " + ", ".join(names))
    result = inspect_configuration(root)
    if result.conflicts:
        print("Configuration conflicts require resolution before synchronization:", file=sys.stderr)
        for item in result.conflicts:
            print(f"  {item}", file=sys.stderr)
        return 2

    selected = tuple(targets)
    if mode == "check":
        if result.migrations:
            names = ", ".join(sorted(result.migrations))
            print(f"local values need initial migration into root .env: {names}", file=sys.stderr)
            return 2
        for target in selected:
            missing = _check_required(result.root_values, target)
            if missing:
                print(f"{target}: missing required values: {', '.join(missing)}", file=sys.stderr)
                return 2
            if target in TARGET_FILES:
                relative, mapping, fmt = TARGET_FILES[target]
                path = root / relative
                expected = _target_values(target, result.root_values)
                current = _read_native(path, fmt)
                stale = [key for key, value in expected.items() if current.get(key) != value]
                if target == "admin":
                    stale.extend(sorted(key for key in current if key.startswith("VITE_") and key not in ADMIN))
                if stale:
                    print(f"{target}: stale or missing generated names: {', '.join(stale)}", file=sys.stderr)
                    return 2
            print(f"{target}: configuration is consistent")
        return 0

    if result.migrations:
        _migrate_root(root, result.migrations)
        print("Migrated existing local values into root .env: " + ", ".join(sorted(result.migrations)))
        result = inspect_configuration(root)
        if result.conflicts:
            raise ConfigError("Conflicts appeared after local migration; no target files were synchronized.")
    # Validate every selected target before changing any generated output.
    for target in selected:
        missing = _check_required(result.root_values, target)
        if missing:
            raise ConfigError(f"{target}: missing required variable names: {', '.join(missing)}")
        if target in TARGET_FILES:
            disallowed = _validate_secret_allowlist(target, result.root_values)
            if target == "admin":
                existing_admin = _read_native(root / TARGET_FILES[target][0], "dotenv")
                disallowed.extend(sorted(key for key in existing_admin if key.startswith("VITE_") and key not in ADMIN))
            if disallowed:
                raise ConfigError(f"{target}: unapproved frontend/mobile variable names: {', '.join(sorted(set(disallowed)))}")
    _mark_legacy_backend_env(root)
    for target in selected:
        if target == "backend":
            print("backend: FastAPI reads root .env directly; production process environment remains higher priority")
            continue
        relative, mapping, fmt = TARGET_FILES[target]
        values = _target_values(target, result.root_values)
        path = root / relative
        content = _render_managed(path, values, fmt)
        changed = _atomic_write(path, content)
        print(f"{target}: {'synchronized' if changed else 'already current'} ({', '.join(values)})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--check", action="store_true", help="validate without writing files")
    operation.add_argument("--sync", action="store_true", help="migrate safe local values and synchronize targets")
    parser.add_argument("--target", choices=("android", "ios", "admin", "backend", "gateway", "all"), default="all")
    parser.add_argument("--adopt-local-urls", action="store_true", help="one-time explicit choice to move current app API URLs into root .env")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.check and args.adopt_local_urls:
        parser.error("--adopt-local-urls is available only with --sync")
    targets = ("android", "ios", "admin", "backend", "gateway") if args.target == "all" else (args.target,)
    try:
        return run(args.root.resolve(), mode="check" if args.check else "sync", targets=targets, adopt_local_urls=args.adopt_local_urls)
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
