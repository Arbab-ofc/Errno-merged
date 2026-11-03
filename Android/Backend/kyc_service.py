"""DigiLocker/KYC orchestration with explicit provider fail-closed behavior.

No HTTP protocol is implemented for the official provider until ERRNO supplies
the approved requester API specification. The mock adapter is test/development
only and is rejected when APP_ENV is production or unspecified.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException


AADHAAR_ALIASES = {"AADHAAR", "AADHAR", "UIDAI", "UID"}


def environment() -> str:
    return os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "")).strip().lower()


def feature_enabled(name: str, default: bool = False) -> bool:
    return os.getenv(name, "true" if default else "false").strip().lower() in {"1", "true", "yes", "on"}


def allowed_document_types() -> set[str]:
    values = os.getenv("KYC_ALLOWED_DOCUMENT_TYPES", "")
    return {value.strip().upper() for value in values.split(",") if value.strip()} - AADHAAR_ALIASES


def consent_version() -> str:
    return os.getenv("KYC_CONSENT_VERSION", "v1").strip()


def ttl_seconds() -> int:
    return max(60, min(1800, int(os.getenv("DIGILOCKER_SESSION_TTL_SECONDS", "600"))))


def retention_days() -> int:
    return max(0, min(3650, int(os.getenv("KYC_DOCUMENT_RETENTION_DAYS", "0"))))


def _state_secret() -> bytes:
    value = os.getenv("DIGILOCKER_STATE_SECRET", "")
    if len(value) < 32:
        raise HTTPException(503, detail={"code": "PROVIDER_NOT_CONFIGURED", "message": "Identity verification is not configured. You can request manual review."})
    return value.encode()


def digest(value: str, *, keyed: bool = False) -> str:
    raw = value.encode()
    if keyed:
        return hmac.new(_state_secret(), raw, hashlib.sha256).hexdigest()
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class ProviderSession:
    provider: str
    authorization_url: str | None
    state: str
    nonce: str
    test_completion_token: str | None = None


class DisabledProvider:
    name = "disabled"

    def create_authorization(self, state: str, nonce: str, document_types: list[str]) -> ProviderSession:
        raise HTTPException(503, detail={"code": "PROVIDER_NOT_CONFIGURED", "message": "DigiLocker verification is unavailable. Request manual review instead."})


class OfficialDigiLockerProvider:
    name = "digilocker"

    def create_authorization(self, state: str, nonce: str, document_types: list[str]) -> ProviderSession:
        required = ("DIGILOCKER_CLIENT_ID", "DIGILOCKER_CLIENT_SECRET", "DIGILOCKER_REDIRECT_URI",
                    "DIGILOCKER_ALLOWED_SCOPES", "DIGILOCKER_API_BASE_URL", "DIGILOCKER_AUTHORIZATION_URL",
                    "DIGILOCKER_TOKEN_URL")
        missing = [name for name in required if not os.getenv(name, "").strip()]
        if missing:
            raise HTTPException(503, detail={"code": "PROVIDER_NOT_CONFIGURED", "message": "DigiLocker requester credentials and approved endpoints are not configured."})
        # Configuration alone is not protocol authority. Do not guess scope,
        # PKCE, token exchange, document fetch, or issuer-proof semantics.
        raise HTTPException(503, detail={"code": "PROVIDER_SPEC_REQUIRED", "message": "The approved DigiLocker requester API specification is required before authorization can start."})


class MockDigiLockerProvider:
    name = "mock"

    def create_authorization(self, state: str, nonce: str, document_types: list[str]) -> ProviderSession:
        if environment() not in {"test", "development", "local"}:
            raise HTTPException(503, detail={"code": "MOCK_PROVIDER_FORBIDDEN", "message": "Mock identity verification is disabled outside test and development environments."})
        return ProviderSession(self.name, None, state, nonce, secrets.token_urlsafe(32))


def provider() -> DisabledProvider | OfficialDigiLockerProvider | MockDigiLockerProvider:
    mode = os.getenv("DIGILOCKER_PROVIDER_MODE", "disabled").strip().lower()
    env = environment()
    if env == "production" and mode == "mock":
        raise HTTPException(503, detail={"code": "MOCK_PROVIDER_FORBIDDEN", "message": "Production cannot use mock identity verification."})
    if mode == "mock":
        if env not in {"test", "development", "local"}:
            raise HTTPException(503, detail={"code": "MOCK_PROVIDER_FORBIDDEN", "message": "Set APP_ENV to test, development, or local to use the mock provider."})
        return MockDigiLockerProvider()
    if mode == "official" and feature_enabled("DIGILOCKER_ENABLED"):
        return OfficialDigiLockerProvider()
    return DisabledProvider()


def ensure_provider_enabled() -> DisabledProvider | OfficialDigiLockerProvider | MockDigiLockerProvider:
    if not feature_enabled("DIGILOCKER_ENABLED"):
        raise HTTPException(503, detail={"code": "PROVIDER_NOT_CONFIGURED", "message": "DigiLocker is not enabled. Request manual review instead."})
    return provider()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def expiry() -> datetime:
    return now_utc() + timedelta(seconds=ttl_seconds())


def ensure_document_types(values: list[str]) -> list[str]:
    allowed = allowed_document_types()
    normalized = sorted({value.strip().upper() for value in values if value.strip()})
    if not normalized:
        raise HTTPException(422, detail={"code": "DOCUMENT_TYPE_REQUIRED", "message": "Select an approved document category."})
    if any(value in AADHAAR_ALIASES for value in normalized):
        raise HTTPException(422, detail={"code": "AADHAAR_DISABLED", "message": "Aadhaar collection is disabled."})
    unsupported = [value for value in normalized if value not in allowed]
    if unsupported:
        raise HTTPException(422, detail={"code": "DOCUMENT_TYPE_UNAVAILABLE", "message": "One or more requested document categories are not enabled for ERRNO."})
    return normalized


def valid_state(state: str, expected_hash: str) -> bool:
    if not state or not expected_hash:
        return False
    return hmac.compare_digest(digest(state, keyed=True), expected_hash)
