#!/usr/bin/env python3
"""Create missing ignored native config files from the root .env, without overwriting."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
ANDROID_FILE = ROOT / "Android" / "gradle.properties.local"
IOS_FILE = ROOT / "iOS" / "Local.xcconfig"
ANDROID_KEYS = (
    "ERRNO_API_BASE_URL",
    "ERRNO_GOOGLE_MAPS_ANDROID_API_KEY",
    "ERRNO_PHOTON_ENDPOINT",
    "ERRNO_FIREBASE_AUTH_EMULATOR_HOST",
)
IOS_KEYS = (
    "ERRNO_API_BASE_URL",
    "ERRNO_GOOGLE_MAPS_IOS_API_KEY",
    "ERRNO_PHOTON_ENDPOINT",
)


def read_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def main() -> int:
    if not ENV_FILE.is_file():
        raise SystemExit("Root .env is missing. Copy .env.example to .env and configure it first.")
    values = read_values(ENV_FILE)

    if not ANDROID_FILE.exists():
        lines = ["# Generated from root .env; ignored by Git."]
        lines.extend(f"{key}={values[key]}" for key in ANDROID_KEYS if key in values)
        ANDROID_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("Created Android/gradle.properties.local")
    else:
        print("Preserved existing Android/gradle.properties.local")

    if not IOS_FILE.exists():
        lines = ["// Generated from root .env; ignored by Git."]
        lines.extend(f"{key} = {values[key]}" for key in IOS_KEYS if key in values)
        IOS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("Created iOS/Local.xcconfig")
    else:
        print("Preserved existing iOS/Local.xcconfig")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
