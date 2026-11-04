# ERRNO DigiLocker and KYC implementation

## Architecture and current readiness

The FastAPI backend owns verification profiles, one-time sessions, purpose-specific consent, status transitions, manual review, audit history, and withdrawal eligibility. Android and iOS ask the backend for status and session creation; they never collect DigiLocker credentials. The Admin Portal uses the existing Firebase-authenticated, persisted permission model.

The official provider adapter is intentionally fail-closed. No approved DigiLocker requester/API Setu developer pack was found in the repository. Supplying client credentials or endpoint environment values alone does not enable an undocumented protocol. `OfficialDigiLockerProvider` currently returns `PROVIDER_SPEC_REQUIRED`; callback routes return the same result and never treat a redirect as proof. No real DigiLocker verification has been performed.

`MockDigiLockerProvider` is available only when explicitly selected with `APP_ENV=test|development|local`, and records method `MOCK_PROVIDER_TEST`. Production refuses mock mode. Do not use this adapter for real worker eligibility.

## Database

Canonical additive migration `9f23b6c4d1a8` follows `5e91c0f4a8d2`. It creates verification profiles, sessions, consent records, verified-document metadata, encrypted manual-review metadata, and audit events. The migration does not alter users, jobs, pricing, payment tables, or wallet ledger entries. It has not been applied to production. Apply it only to an isolated database after reviewing generated SQL.

Document bytes are Fernet-encrypted in a private directory with restrictive permissions. Uploads remain quarantined unless a configured ClamAV socket reports clean; the test-only scanner is unavailable outside test mode. This filesystem adapter requires a shared, persistent encrypted volume across backend instances or replacement with an approved private object-storage adapter before horizontal deployment. Public or permanent object URLs are never generated.

## API

- `GET /api/v1/worker/verification-status`
- `POST /api/v1/worker/verification-sessions`
- `GET /api/v1/worker/verification-sessions/{session_id}`
- `POST /api/v1/worker/verification-sessions/{session_id}/cancel`
- `POST /api/v1/worker/verification/withdraw-consent`
- `POST /api/v1/worker/verification/manual-reviews` (multipart document upload)
- `GET /api/v1/worker/verification/manual-reviews`
- `GET|POST /api/v1/verification/digilocker/callback` (deliberate fail-closed placeholder pending approved protocol)
- `GET /api/v1/admin/kyc/overview`
- `GET /api/v1/admin/kyc/verifications`
- `GET /api/v1/admin/kyc/verifications/{id}`
- `POST /api/v1/admin/kyc/verifications/{id}/review`
- `GET /api/v1/admin/kyc/manual-reviews/{id}/document`
- `GET /api/v1/admin/kyc/audit`
- `GET|POST /api/v1/admin/kyc/me/verification-status|verification-sessions` for staff self-verification
- `POST /api/v1/admin/kyc/retention/cleanup`

Admin permissions: `kyc.read`, `kyc.review`, `kyc.manage`, and `kyc.audit`. They are checked using existing RBAC and are not automatically granted.

## Consent, manual review, privacy

Consent is required per document category and version. Withdrawal cancels active sessions and removes verification metadata while preserving an audit event. Aadhaar aliases are always rejected. Only categories in `KYC_ALLOWED_DOCUMENT_TYPES` are accepted. Manual approvals remain `MANUAL_DOCUMENT_REVIEW`; they are not represented as DigiLocker issuer proof. Sensitive document bytes are available only through the reviewer permission endpoint after a clean malware scan. Configure retention and schedule the admin cleanup task; a retention period of zero means records are not automatically eligible for deletion.

## Withdrawal integration

When `KYC_REQUIRED_FOR_WITHDRAWAL=true`, the existing withdrawal eligibility service requires a current verified internal KYC profile and adds reason `KYC_REQUIRED`. Existing 3 eligible paid completed orders, payout-method verification, balance checks, ledger arithmetic, and Razorpay payment behavior remain in place. Provider-required payout KYC (`WorkerPayoutMethod.kyc_verified`) remains a separate check. Internal manual review does not automatically satisfy a provider's legal requirements.

## Configuration

See repository `.env.digilocker.example`. Generate independent secrets in the deployment secret manager. Do not commit `.env`, encryption keys, provider credentials, or state secrets. Production must set `APP_ENV=production`, use the approved official adapter only after implementation against the provider pack, and configure private encrypted shared storage plus a malware scanner. Never set production provider mode to `mock`.

Key controls include `DIGILOCKER_ENABLED`, `DIGILOCKER_PROVIDER_MODE`, the `DIGILOCKER_*` requester values, `DIGILOCKER_STATE_SECRET`, `KYC_MANUAL_REVIEW_ENABLED`, `KYC_REQUIRED_FOR_WITHDRAWAL`, `KYC_DOCUMENT_RETENTION_DAYS`, `KYC_ALLOWED_DOCUMENT_TYPES`, `KYC_DOCUMENT_ENCRYPTION_KEY`, `KYC_MANUAL_STORAGE_PATH`, and `KYC_ANTIVIRUS_MODE`.

## Official requester onboarding still required

ERRNO must obtain the current approved developer pack and requester approval, then confirm the precise authorization and token endpoints, grant/scopes, PKCE/state/nonce requirements, callback methods and parameters, token/session revocation mechanism, document retrieval endpoints, issuer participation, signed proof format and key rotation, permitted document metadata, sandbox credentials/accounts, registered callback URLs, production credentials, and provider retention/deletion requirements. Implement those details only in the provider adapter and its validation tests. Aadhaar stays disabled until separately authorized and privacy-reviewed.

## Test and deployment notes

Use an isolated test PostgreSQL database for canonical migration tests and an explicit development/test mock mode for deterministic orchestration tests. Do not run the migration against production as part of deployment startup. Add `cryptography` and `python-multipart` from `requirements.txt`. Run backend and Admin checks from their project directories; run Android Gradle and iOS Simulator builds on configured toolchains. No provider sandbox or real-document testing is possible until requester approval and credentials are provided.

Before production activation: approve document categories and consent copy; approve retention policy; provision reviewer RBAC; configure malware scanning and durable private storage; review applicable privacy/legal requirements; apply the migration through the controlled migration process; and complete official provider sandbox plus callback security testing. No DigiLocker account passwords, OTPs, or PINs should ever pass through ERRNO.
