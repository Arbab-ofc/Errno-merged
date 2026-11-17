"""Load the repository root .env without overriding process configuration."""

from pathlib import Path

import os

from dotenv import dotenv_values


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ROOT_ENV_FILE = REPOSITORY_ROOT / ".env"


def load_backend_environment() -> None:
    """Apply root local settings only for variables absent from the process."""
    if not ROOT_ENV_FILE.is_file():
        return
    # Empty template entries mean "unset". Skipping them keeps safe defaults
    # available and avoids masking explicit test/developer defaults.
    for key, value in dotenv_values(ROOT_ENV_FILE, interpolate=False).items():
        if value not in (None, "") and key not in os.environ:
            os.environ[key] = value
