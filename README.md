# ERRNO

ERRNO is a two-sided workforce marketplace. Shopkeepers post and manage shifts; workers discover jobs, apply, and complete assigned work. The repository contains native Android and iOS applications, a shared FastAPI backend, an Admin web portal, and a private WhatsApp message gateway.

The repository is the source of truth for implementation. Historical reports and per-component guides were consolidated here; where old documentation disagreed with current code, this README describes the code and calls out unresolved or unverified behavior.

## Contents

- [Architecture and project layout](#architecture-and-project-layout)
- [Implementation status](#implementation-status)
- [Marketplace and booking workflows](#marketplace-and-booking-workflows)
- [Maps and location](#maps-and-location)
- [Authentication and security](#authentication-and-security)
- [Backend API](#backend-api)
- [Database and migrations](#database-and-migrations)
- [Notifications](#notifications)
- [Payments and wallet](#payments-and-wallet)
- [KYC and DigiLocker](#kyc-and-digilocker)
- [Admin portal](#admin-portal)
- [WhatsApp gateway](#whatsapp-gateway)
- [Environment setup](#environment-setup)
- [Owner credentials checklist](#owner-credentials-checklist)
- [Local development](#local-development)
- [Build and test commands](#build-and-test-commands)
- [Deployment operations](#deployment-operations)
- [Troubleshooting](#troubleshooting)
- [Security and privacy](#security-and-privacy)
- [Known limitations and audit findings](#known-limitations-and-audit-findings)

## Architecture and project layout

| Component | Location | Technology | Role |
|---|---|---|---|
| Android app | `Android/app/` | Kotlin, Jetpack Compose, Maps Compose | Shopkeeper and worker mobile clients |
| iOS app | `iOS/Errno.xcodeproj` | SwiftUI, Google Maps SDK for iOS | Shopkeeper and worker mobile clients |
| Backend | `Android/Backend/` | FastAPI, SQLAlchemy, Alembic | Authentication, marketplace, pricing, dispatch, location, payments, KYC, notifications |
| Admin portal | `Admin/` | React, Vite, Firebase Web Auth | Permission-gated operations and monitoring |
| WhatsApp gateway | `WhatsAppGateway/` | Node.js, Express, Baileys | Private QR-paired WhatsApp message transport |

Android and iOS are separate applications. They share the backend APIs and data contracts; neither mobile app connects directly to the database. The backend owns identity resolution, authorization, pricing snapshots, job lifecycle, and persisted coordinates.

## Implementation status

Status labels below describe repository evidence. External provider credentials and production deployment state are not inferred from source code.

| Area | Status | Notes |
|---|---|---|
| Native Android and iOS maps | Implemented; credentials/runtime need setup | Native SDK maps, shop pins, worker/shop markers, foreground location support, and external directions are present. |
| Job posting, applications, and lifecycle | Implemented | Shop owner creates jobs; workers apply; owner accepts/rejects; assigned worker starts; owner confirms completion. |
| Nearby workers and live tracking | Implemented in code; PostGIS/runtime verification required | Nearby discovery uses PostGIS and worker presence. Assigned-worker tracking uses authenticated HTTP and WebSocket APIs. |
| Instant/current booking | Implemented | Uses the current job lifecycle and server-generated pricing quote. |
| Four-hour pre-booking dispatch | Implemented in code; requires supervised dispatcher | Durable dispatch state and worker invitations are separate from FCM delivery. |
| Firebase sign-in and persisted identity | Implemented | Backend verifies Firebase ID tokens and loads the persisted user. Admin access requires an explicit database permission. |
| Notification inbox and outbox | Implemented in code; delivery needs credentials/operations | PostgreSQL inbox is authoritative. FCM is best effort and push is disabled by default. |
| Razorpay checkout and ledger | Implemented in code; provider credentials and financial operations need setup | Checkout verification, webhooks, wallet ledger, refunds, and cash confirmation exist. External payouts are not automatically transferred. |
| DigiLocker | Partially implemented, fail-closed | Consent, sessions, manual review, and storage controls exist. The official provider adapter is disabled pending an approved requester specification and credentials. |
| WhatsApp OTP | Implemented in code; gateway must be paired and privately networked | Backend owns challenges and sessions; gateway transports messages but does not verify OTPs. Baileys uses the unofficial WhatsApp Web protocol. |
| Commercial pricing configuration | Implemented as a configurable system; production values unapproved | Draft examples are proposals only. They are not active commercial settings. |

The old Android README described a custom Canvas map and some feature claims that no longer matched the app. Current code uses the native Google Maps SDK. No source-backed guarantee of placing a worker within 15 minutes was found; availability depends on matching and eligible workers.

## Marketplace and booking workflows

### Shopkeeper

Shopkeepers complete onboarding, maintain a shop profile, choose an address and optional map coordinates, request an authoritative pricing quote, post a job, review applications, accept or reject workers, and manage job status. The server derives job ownership from the authenticated user and shop relationship.

Job coordinates are optional and must be supplied as a latitude/longitude pair. Manually entered addresses remain usable without GPS or a map key. Selected coordinates are stored in the existing job fields; the map conversion does not require a new database migration.

### Worker

Workers browse open jobs, review job and shop details, choose a duration/pay option where applicable, and apply. Applications are idempotent per worker/job pair. The shop owner accepts one pending application atomically; the backend assigns that worker and rejects other pending applications. The assigned worker starts the job; the owning shopkeeper confirms completion.

Canonical job statuses are `open`, `assigned`, `in_progress`, `completed`, and `cancelled`. Invalid or repeated lifecycle transitions return a conflict. Completion does not itself process a payment.

### Instant/current booking

`CURRENT` jobs follow the standard job/application flow. Pricing is quoted by the backend and the posted job uses the server-held quote snapshot rather than trusting a client-entered amount.

### Four-hour pre-booking dispatch

`PRE_BOOKING` jobs remain hidden from workers until dispatch succeeds. The backend stores `scheduled_at` and `dispatch_at = scheduled_at - 4 hours` as timezone-aware timestamps. A booking more than four hours ahead is `SCHEDULED`; creation within the four-hour window attempts dispatch immediately. Past scheduled times are rejected.

The durable dispatch states are `SCHEDULED`, `DISPATCHING`, `DISPATCHED`, `NO_ELIGIBLE_WORKERS`, `FAILED_RETRYABLE`, `FAILED`, and `CANCELLED`. `DISPATCHED` means invitations were queued to the notification outbox, not that a push reached a device. Workers still use the normal job review/apply flow, and shopkeepers still accept/reject applications. The dispatcher is a separate supervised process:

```sh
cd Android/Backend
python -m services.prebooking_dispatcher
```

Cancellation and rescheduling apply only according to the job/dispatch state. Rescheduling uses a fresh quote and increments the schedule version so stale dispatcher claims cannot send old invitations. Run the notification dispatcher separately; API startup does not start either worker.

## Maps and location

- Android renders maps using Google Maps SDK through Maps Compose.
- iOS renders maps with Google Maps SDK for iOS through a SwiftUI/UIKit wrapper.
- Shopkeepers can select/edit a map pin, search using Photon, use foreground GPS, and manually edit the address. Photon reverse lookup updates the address after a pin change; failures retain manual editing.
- Worker screens display the saved shop pin and, where authorized data is available, nearby/assigned worker markers. Location sharing is foreground-only and permission-gated.
- Nearby-worker discovery remains a backend PostGIS operation. Worker availability and location freshness are checked server-side.
- Assigned-worker live tracking uses the existing location APIs and authenticated WebSocket. No Google Routes API or Navigation SDK is used in Phase 1.
- After acceptance/assignment, directions open an external HTTPS Google Maps URL. The URL can resolve to the Google Maps app or a browser; ERRNO does not provide turn-by-turn navigation in-app.
- Photon remains the non-Google address search/reverse lookup service. The backend OSRM route endpoint remains for API compatibility; native clients no longer request its geometry or ETA.

### Google Maps keys

Use two separate restricted keys and enable billing plus only the Maps SDK for Android and Maps SDK for iOS in the owner-controlled Google Cloud project.

| Key | Application restriction | API restriction | Root setting |
|---|---|---|---|
| Android | Package `com.erno.app` plus every applicable signing certificate SHA-1 | Maps SDK for Android | `ERRNO_GOOGLE_MAPS_ANDROID_API_KEY` |
| iOS | Bundle ID `com.errno.app` | Maps SDK for iOS | `ERRNO_GOOGLE_MAPS_IOS_API_KEY` |

Add the Play App Signing certificate fingerprint for Play builds. Keep dev and production keys separate where practical. Set quotas and billing alerts; alerts are not hard spending caps. Google Maps URLs do not need a Maps API key. Do not enable Places, Google Geocoding, Routes, or Navigation for this release. No real key belongs in this repository.

## Authentication and security

### Firebase

The backend verifies Firebase ID tokens against project `errno-pvt-ltd` using Firebase Admin and resolves users by Firebase UID. It does not trust client-supplied user IDs. Login creates/retrieves the profile; a user selects `worker` or `shop_owner` once during onboarding. An email match does not automatically link accounts.

Backend credentials use `GOOGLE_APPLICATION_CREDENTIALS` or Application Default Credentials. A service-account file or runtime identity belongs only on the backend. Mobile Firebase client configuration files remain separate platform inputs and are not replaced by `.env.example`.

OTP compatibility routes under `/auth/send-otp` and `/auth/verify-otp` are disabled until a real provider is configured. Fabricated legacy OTP tokens do not authenticate protected routes.

### WhatsApp OTP

FastAPI creates and verifies challenges and issues opaque revocable sessions. The gateway only sends messages. Session tokens are returned once, stored hashed, and accepted by the normal backend authentication dependency. Rate limits apply per phone and IP. A gateway send acknowledgement is not proof of delivery.

### Admin access

Admin APIs require explicit persisted permissions keyed by Firebase UID. A Firebase account, verified email, Google provider, frontend role, or mobile role does not grant admin access. Grants/revocations and data mutations are audited. The bootstrap CLI is allowed only when there is no active admin; later permission changes require an active operator.

Provisioning must be performed by an authorized operator against the intended database after verifying target and operator UIDs out of band. Use a ticket as the reason and never place database credentials, tokens, or personal data in command arguments:

```sh
cd Android/Backend
python tools/provision_admin.py grant \
  --firebase-uid '<verified-target-uid>' \
  --actor-uid '<verified-operator-uid>' \
  --confirm-target '<verified-target-uid>' \
  --bootstrap \
  --permission dashboard.read --permission users.read \
  --permission users.manage --permission jobs.read \
  --permission jobs.manage --reason '<approved change ticket>'
```

Revocation deactivates the permission record and audits the action; it does not disable the Firebase account. See `tools/provision_admin.py --help` for additional permissions and options.

## Backend API

Authenticated routes accept a Firebase ID token or valid ERRNO WhatsApp session in the `Authorization: Bearer` header. Ownership and roles are checked by the backend.

### Authentication, shops, and jobs

| Method and path | Access / purpose |
|---|---|
| `POST /api/v1/auth/firebase` | Verified Firebase token; create or retrieve profile |
| `GET`, `PATCH /api/v1/users/me` | Read/update profile and one-time role selection |
| `POST /api/v1/auth/logout` | Acknowledgement; clients clear local Firebase session |
| `GET`, `PUT /shops/me` | Owner reads/updates shop name, address, category |
| `GET /jobs`, `GET /jobs/{job_id}` | Public open-job discovery/detail; undispatched pre-bookings are hidden |
| `GET /jobs/mine` | Shop owner reads owned jobs |
| `POST /jobs` | Shop owner posts a quoted job; ownership comes from token |
| `POST /jobs/{job_id}/apply` | Worker applies idempotently to an open job |
| `GET /jobs/applications/me` | Worker paginated application history |
| `DELETE /jobs/{job_id}/applications/me` | Worker cancels a pending application |
| `GET /jobs/applications/owner` | Owner reads minimal applicant summaries |
| `GET /jobs/{job_id}/applications` | Owner reads applications for owned job |
| `PATCH /jobs/{job_id}/applications/{application_id}` | Owner accepts/rejects; acceptance assignment is atomic |
| `POST /jobs/{job_id}/start` | Assigned worker starts work |
| `POST /jobs/{job_id}/complete` | Owning shopkeeper confirms completion; does not charge payment |
| `PATCH /jobs/{job_id}/status?new_status=cancelled` | Owner cancels eligible unstarted work |

Application history contains job/shop summaries and actual application status. Typical errors are 401 unauthenticated, 403 wrong role/owner, 404 missing resource, 409 lifecycle conflict, and 422 invalid request.

### Pricing, presence, and maps

- Pricing/presence mobile routes include `GET /api/v1/pricing/durations`, `POST /api/v1/pricing/quotes`, quote/job pricing reads, worker payout reads, `POST /api/v1/presence/heartbeat`, `POST /api/v1/presence/offline`, and `PATCH /api/v1/workers/me/availability`.
- Admin pricing routes cover duration/settings/time/demand/area rules, previews, audit, and presence summaries. Edits are drafts until an explicitly authorized admin activates them.
- `PUT /api/v1/workers/me/location` records foreground available-worker location.
- `GET /jobs/{job_id}/nearby-workers?radius_km=5` is restricted to the owning shopkeeper, a geocoded open job, PostGIS, eligible active workers, fresh location, and foreground available presence. Default radius is 5 km; maximum is 50 km.
- `PUT /jobs/{job_id}/tracking/location` accepts the assigned worker's active-job location.
- `GET /jobs/{job_id}/tracking/location` and `WS /ws/jobs/{job_id}/tracking` are owner-authorized. WebSocket clients authenticate with a Bearer header and send text heartbeats. Online/stale/disconnected/ended states are represented.
- `GET /jobs/{job_id}/route` retains OSRM-backed route geometry for API compatibility. It is not live traffic ETA and is not requested by the native apps.

### Payments and wallet

Payment routes include:

- `POST /api/v1/bookings/{booking_id}/payment-order`
- `POST /api/v1/payments/verify`
- `GET /api/v1/payments/{payment_id}` and `GET /api/v1/bookings/{booking_id}/payment-status`
- `POST /api/v1/webhooks/razorpay`
- Worker wallet/payout methods/withdrawals under `/api/v1/worker/wallet`, `/api/v1/worker/payout-methods`, and `/api/v1/worker/withdrawals`
- Cash collection and confirmation under `/api/v1/bookings/{booking_id}/cash-collection` and `/api/v1/cash-collections/{collection_id}/confirm`
- Finance, refunds, and reconciliation under `/api/v1/admin/finance`, `/api/v1/admin/refunds`, and `/api/v1/admin/reconciliation`

The immutable job quote is the financial authority. Amounts are converted to integer paise and checked for balance. Checkout callback signatures are checked and independently verified with Razorpay; webhooks are idempotent. The append-only ledger tracks worker earnings, platform commission, and refunds. Cash remains outside Razorpay until reconciled. Payout-method verification and external transfers require finance operations; no automated bank transfer is implied.

### WhatsApp, KYC, notifications

- WhatsApp mobile routes: `POST /api/v1/auth/whatsapp/send-otp`, `resend-otp`, `verify-otp`, and `logout`. Admin gateway routes are under `/api/v1/admin/whatsapp` and require explicit permissions.
- Worker KYC routes include verification status/sessions, session cancellation, consent withdrawal, manual-review uploads/status, and the DigiLocker callback placeholder. Admin KYC routes include overview, reviews, documents, audit, and retention cleanup under `/api/v1/admin/kyc`.
- Device registration: `POST /api/v1/devices/register`; owner-scoped deletion: `DELETE /api/v1/devices/{device_id}`.
- Notification inbox: `GET /api/v1/notifications`, unread count, read/read-all, delete, and preferences. Admin delivery/retry routes are under `/api/v1/admin/notifications`.

## Database and migrations

The backend uses SQLAlchemy and PostgreSQL. Location discovery uses PostGIS geography and `ST_DWithin`/`ST_Distance`; worker coordinates and job coordinates are stored with latitude/longitude contracts. `DATABASE_URL` PostgreSQL connections require `sslmode=verify-full` and a trusted CA. The default CA path is `Android/Backend/certs/supabase-prod-ca-2021.crt`; `PGSSLROOTCERT` or `ERRNO_PGSSLROOTCERT` can select another CA. SQLite is a local/dev fallback and cannot validate PostGIS behavior.

The repository contains legacy and canonical Alembic configurations and documented ORM/schema history. The legacy user model and runtime UUID model have had schema drift. Inspect the actual deployed schema, Alembic heads/current revision, primary-key types, and foreign keys before selecting a migration path. Do not assume a revision is applied because code exists. App startup does not call `create_all` or apply migrations. Production changes require a reviewed, backed-up, staged migration process; no migration should be run from onboarding instructions blindly.

Canonical feature revisions documented in the source history include location tracking (`eb72a31c4890`), four-hour dispatch (`fb4a6c90d112`), payments (`5e91c0f4a8d2`), DigiLocker/KYC (`9f23b6c4d1a8`), and notifications (`d17a6c90e241`), alongside earlier pricing/presence/admin/WhatsApp revisions. Parent chains and deployed state must be verified using the canonical configuration before any real upgrade/downgrade. Downgrades can remove audit/authorization/payment/verification data. Do not perform them casually.

For canonical migrations, `ERRNO_DATABASE_URL` is explicit. A loopback test migration is allowed only for the expected `errno_phase22_test` database with `ERRNO_ALLOW_LOCAL_TEST_DB=1`. Non-local migration requires explicit `ERRNO_ALLOW_CANONICAL_MIGRATION=1` and a trusted `ERRNO_PGSSLROOTCERT`. Never set these against production as a shortcut; use the deployment change process.

## Notifications

Business handlers write inbox and outbox records in the same SQL transaction as the business change. A separately supervised dispatcher claims outbox rows (`FOR UPDATE SKIP LOCKED` on PostgreSQL), retries transient failures with capped exponential backoff/jitter, invalidates unregistered tokens, and records attempts. Run it with:

```sh
cd Android/Backend
python -m services.notification_dispatcher
```

Implemented event integrations include booking created, worker assigned/job assigned, job started, booking cancelled, job completed, verified payment success/failure, and KYC review status changed. Unsupported arrival/en-route, complaint/dispute, payout-completion, rating-eligibility, or broad job-alert events are not fabricated.

Push is best effort; the PostgreSQL inbox is authoritative. `accepted_by_fcm` only means Firebase accepted a request, not that a device displayed or a person read it. Push preference does not erase transactional inbox items. Data payloads contain routing IDs, not authority. Android 13+ notification permission and iOS/APNs delivery require runtime setup. Current push taps route to the authenticated inbox rather than a specific authorized business detail.

Notification device tokens are encrypted and HMAC hashed. Configure independent high-entropy `NOTIFICATION_TOKEN_ENCRYPTION_KEY` (Fernet) and `NOTIFICATION_TOKEN_HASH_SECRET` values before enabling push. Mobile Firebase/APNs credentials remain platform-side; Firebase Admin credentials stay on the backend. Retention cleanup and operational alerts require deployment configuration.

## Payments and wallet

Configure Razorpay in Test Mode first. The backend requires server-only key ID, key secret, and an independent webhook secret. Register `/api/v1/webhooks/razorpay` for `payment.captured`, `payment.failed`, and `refund.processed`. Never put the key secret/webhook secret in Android, iOS, or Admin JavaScript.

Razorpay orders are created only for a job with canonical `completed` status and `completed_at`. A checkout close does not mean payment failure. Refund requests remain pending until provider confirmation; a provider timeout becomes `PROVIDER_UNKNOWN` for reconciliation rather than a blind duplicate. Three eligible provider-paid completed jobs are required before withdrawal. Pending cash blocks withdrawal. A static QR is not proof of payment.

Cash settlement/cancellation/refund policies remain unconfigured business decisions. RazorpayX/Payout authorization is not assumed. Admin finance permissions (for example `payments.read`, `payments.refund`, `payments.manage`, `wallet.read`, `withdrawals.manage`, and reconciliation permissions) must be explicitly provisioned. A finance queue approval is not an external transfer.

## KYC and DigiLocker

The backend supports consent-versioned verification sessions, status transitions, manual review, audit, encrypted document storage, and withdrawal eligibility integration. Manual approval is recorded as `MANUAL_DOCUMENT_REVIEW`, not DigiLocker issuer proof. Aadhaar aliases are rejected; accepted categories are controlled by `KYC_ALLOWED_DOCUMENT_TYPES`.

The official DigiLocker adapter intentionally fails closed with `PROVIDER_SPEC_REQUIRED`; callback routes do not treat a redirect as proof. No approved requester/API Setu pack or real verification is included. Supplying client ID/secret/endpoints alone does not enable it. Mock verification is restricted to explicit test/development/local modes and must never be used in production.

Documents are Fernet-encrypted in a private directory and remain quarantined until ClamAV reports clean. Production needs private durable shared storage, a malware scanner, approved retention, reviewer RBAC, consent/legal review, and provider sandbox/callback security testing. A retention period of zero disables automatic deletion eligibility. Internal worker KYC is distinct from payout-provider KYC.

## Admin portal

The React/Vite app uses Firebase Web Sign-In and the shared FastAPI API. Firebase login alone grants no admin API access. Dashboard, people, jobs, pricing/presence, finance, KYC, notification, and WhatsApp gateway surfaces are present in current source; the backend enforces the corresponding persisted permissions. Review the page and endpoint implementation for operational availability—UI presence does not bypass missing data contracts or RBAC.

Firebase Web settings use `VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_AUTH_DOMAIN`, `VITE_FIREBASE_PROJECT_ID`, and `VITE_FIREBASE_APP_ID`. These are public client identifiers, not service-account credentials. Never expose a Firebase Admin service account in Vite variables. The Admin app reads the root `.env` and keeps existing `Admin/.env.local` overrides; only `VITE_` variables are bundled for browser use.

## WhatsApp gateway

The gateway runs privately and has no published port in `WhatsAppGateway/compose.yaml`. It expects the external Docker network `errno-private`, a shared internal secret of at least 32 random characters, and a private persistent session volume. FastAPI should reach it at `http://whatsapp-gateway:8787` on that network. For local development, use loopback. Do not expose the gateway port to the public internet or use this transport for bulk messages.

Baileys implements the unofficial WhatsApp Web protocol. WhatsApp can disconnect or restrict a paired account; authentication fails closed if the gateway is unavailable. A send acknowledgement is not a delivery receipt. Gateway session data is sensitive account state; protect and back it up only through approved secret storage.

## Environment setup

There is one tracked environment example: root `.env.example`. It contains safe placeholders/defaults for backend, Admin, gateway, Android, and iOS settings. Copy it to ignored root `.env`, replace placeholders in your local copy/secret manager, and do not commit it:

```sh
cp .env.example .env
```

For shell-launched local services, export its entries without printing them:

```sh
set -a
. ./.env
set +a
```

The backend loads `Android/Backend/.env` first and then reads the root `.env` for unset values; component-local values therefore retain precedence. Vite reads root `.env` while preserving existing Admin-local overrides. Docker Compose receives it explicitly with `--env-file .env`.

Android Gradle and Xcode do not parse dotenv files directly. For a clean checkout, generate ignored native configuration files from root `.env`:

```sh
python3 scripts/sync_native_configs.py
```

The helper creates either missing target (`Android/gradle.properties.local` and/or `iOS/Local.xcconfig`) and refuses to overwrite an existing file. If a private file already exists, preserve it and manually add/update the required setting in that local file. Xcode loads the tracked, non-secret `iOS/NativeEnvironment.xcconfig`, which optionally includes ignored `Local.xcconfig`. `google-services.json` and `GoogleService-Info.plist` are separate Firebase platform inputs and are not generated from `.env`.

### Variable groups and defaults

The root `.env.example` is the full variable catalog. Empty values mean the deployment must provide the setting before enabling that integration. Do not set migration safety flags in a general production runtime environment.

| Group | Variables / defaults | Notes |
|---|---|---|
| Runtime/database | `APP_ENV=development`, `ENVIRONMENT=development`, `LOG_LEVEL=info`, `DATABASE_URL=` | No PostgreSQL URL uses local SQLite for development. PostgreSQL requires verified TLS. |
| Database CA/migrations | `PGSSLROOTCERT=`, `ERRNO_PGSSLROOTCERT=`, `ERRNO_DATABASE_URL=`, `ERRNO_TEST_DATABASE_URL=`, `ERRNO_ALLOW_LOCAL_TEST_DB=`, `ERRNO_ALLOW_CANONICAL_MIGRATION=` | Explicit CA and migration/test opt-ins; blank by default. |
| Backend/Firebase | `FIREBASE_PROJECT_ID=errno-pvt-ltd`, `GOOGLE_APPLICATION_CREDENTIALS=`, `ERRNO_CORS_ALLOWED_ORIGINS=` | Server credentials are backend-only. CORS is a comma-separated origin allowlist. |
| Android/iOS | `ERRNO_API_BASE_URL=http://localhost:8000`, both `ERRNO_GOOGLE_MAPS_*_API_KEY`, `ERRNO_FIREBASE_AUTH_EMULATOR_HOST=`, `ERRNO_PHOTON_ENDPOINT=https://photon.komoot.io` | Android emulator commonly needs `http://10.0.2.2:8000`; maps keys are distinct/restricted. |
| Route compatibility | `ERRNO_OSRM_ENDPOINT=https://router.project-osrm.org/route/v1/driving` | Legacy backend route endpoint only; mobile maps do not request route geometry/ETA. |
| Admin web | `VITE_API_BASE_URL=http://localhost:8000`, `VITE_FIREBASE_API_KEY=`, `VITE_FIREBASE_AUTH_DOMAIN=errno-pvt-ltd.firebaseapp.com`, `VITE_FIREBASE_PROJECT_ID=errno-pvt-ltd`, `VITE_FIREBASE_APP_ID=` | Web Firebase values are public client configuration. Never put service credentials here. |
| Notifications | `NOTIFICATION_WORKER_ENABLED=true`, `NOTIFICATION_PUSH_ENABLED=false`, `NOTIFICATION_MAX_ATTEMPTS=6`, `NOTIFICATION_RETRY_BASE_SECONDS=15`, `NOTIFICATION_RETRY_MAX_SECONDS=3600`, `NOTIFICATION_LEASE_SECONDS=120`, `NOTIFICATION_WORKER_POLL_SECONDS=2`, `NOTIFICATION_RETENTION_DAYS=365`, `NOTIFICATION_DELIVERY_LOG_RETENTION_DAYS=180`, `NOTIFICATION_TOKEN_ENCRYPTION_KEY=`, `NOTIFICATION_TOKEN_HASH_SECRET=` | Configure encryption/hash secrets before push. Worker is a separate process. |
| Razorpay | `RAZORPAY_KEY_ID=rzp_test_replace-me`, `RAZORPAY_KEY_SECRET=`, `RAZORPAY_WEBHOOK_SECRET=`, `RAZORPAY_ENVIRONMENT=test`, `RAZORPAY_API_TIMEOUT_SECONDS=10` | Secrets are server-side. Use Test Mode first. |
| Payment policy controls | `ERRNO_PAYOUT_METHOD_VERIFICATION_ENABLED=false`, `ERRNO_CASH_SETTLEMENT_POLICY=unconfigured`, `ERRNO_CANCELLATION_REFUND_POLICY=unconfigured` | Business/provider operations remain gated; do not invent policy. |
| DigiLocker/KYC | `DIGILOCKER_ENABLED=false`, `DIGILOCKER_PROVIDER_MODE=disabled`, `DIGILOCKER_CLIENT_ID=`, `DIGILOCKER_CLIENT_SECRET=`, `DIGILOCKER_REDIRECT_URI=`, `DIGILOCKER_ALLOWED_SCOPES=`, `DIGILOCKER_API_BASE_URL=`, `DIGILOCKER_AUTHORIZATION_URL=`, `DIGILOCKER_TOKEN_URL=`, `DIGILOCKER_SESSION_TTL_SECONDS=600`, `DIGILOCKER_HTTP_TIMEOUT_SECONDS=15`, `DIGILOCKER_STATE_SECRET=`, `KYC_MANUAL_REVIEW_ENABLED=false`, `KYC_REQUIRED_FOR_WITHDRAWAL=true`, `KYC_DOCUMENT_RETENTION_DAYS=0`, `KYC_CONSENT_VERSION=v1`, `KYC_ALLOWED_DOCUMENT_TYPES=`, `KYC_DOCUMENT_ENCRYPTION_KEY=`, `KYC_MANUAL_STORAGE_PATH=`, `KYC_ANTIVIRUS_MODE=quarantine`, `KYC_CLAMAV_UNIX_SOCKET=` | Official provider remains disabled/fail-closed. The old DigiLocker example also named `DIGILOCKER_DOCUMENT_RETENTION_DAYS`; current code reads `KYC_DOCUMENT_RETENTION_DAYS`. The old name is included as a blank compatibility note in the example but is not consumed by current code. |
| Pre-booking dispatcher | `PREBOOKING_DISPATCH_POLL_SECONDS=1`, `PREBOOKING_DISPATCH_LEASE_SECONDS=120`, `PREBOOKING_NO_WORKER_RETRY_SECONDS=300`, `PREBOOKING_WORKER_RADIUS_KM=5`, `PREBOOKING_LOCATION_MAX_AGE_SECONDS=300` | Separate supervised process, same backend database. |
| WhatsApp backend | `WHATSAPP_GATEWAY_ENABLED=false`, `WHATSAPP_GATEWAY_INTERNAL_URL=http://whatsapp-gateway:8787`, `WHATSAPP_GATEWAY_INTERNAL_AUTH_SECRET=`, `WHATSAPP_GATEWAY_TIMEOUT_SECONDS=35`, `WHATSAPP_OTP_HASH_SECRET=`, `WHATSAPP_OTP_LENGTH=6`, `WHATSAPP_OTP_TTL_SECONDS=300`, `WHATSAPP_OTP_RESEND_SECONDS=30`, `WHATSAPP_OTP_MAX_ATTEMPTS=5`, `WHATSAPP_OTP_PHONE_LIMIT_PER_HOUR=5`, `WHATSAPP_OTP_IP_LIMIT_PER_HOUR=20`, `WHATSAPP_SESSION_TTL_SECONDS=2592000`, `WHATSAPP_SESSION_MAX_ACTIVE=5` | Use independent high-entropy secrets. |
| WhatsApp gateway process | `WHATSAPP_GATEWAY_BIND=127.0.0.1`, `WHATSAPP_GATEWAY_PORT=8787`, `WHATSAPP_GATEWAY_SESSION_PATH=./session`, `WHATSAPP_GATEWAY_AUTOCONNECT=true`, `WHATSAPP_GATEWAY_QR_TTL_SECONDS=60` | In Docker the bind and session path are set by Compose; protect the persistent volume. |

`DIGILOCKER_DOCUMENT_RETENTION_DAYS` remains listed to avoid silently dropping a name from the old template; it is not currently read. Set `KYC_DOCUMENT_RETENTION_DAYS` for runtime behavior.

## Owner credentials checklist

Before enabling a provider or publishing a client build, the accountable owner should verify these items in the intended environment. Store values in an approved secret manager or protected local config; this checklist deliberately contains no credential values.

- [ ] Google Cloud project: Maps SDK for Android and Maps SDK for iOS enabled; billing account active; quotas and alerts reviewed; Android key restricted to `com.erno.app` plus release/debug SHA-1 fingerprints; iOS key restricted to `com.errno.app`.
- [ ] Firebase: Android and iOS client files belong to the intended Firebase project; web client identifiers are configured; backend Admin identity uses ADC/managed identity or a protected service credential; FCM/APNs settings and device permissions verified.
- [ ] PostgreSQL: intended database and PostGIS extension confirmed; TLS CA and `verify-full` checked; schema/revision and backups reviewed before any migration.
- [ ] Razorpay: test credentials and webhook secret configured first; production activation, refund/cash policies, reconciliation, payout verification, and operator access separately approved.
- [ ] Notifications: token encryption/hash secrets generated independently; outbox worker supervised; retention and delivery monitoring set; push remains disabled until provider setup is verified.
- [ ] WhatsApp: gateway shared secret is high entropy; private network and persistent session storage secured; paired account owner has approved its use; gateway port is not public.
- [ ] KYC/DigiLocker: legal consent, official requester/provider specification, sandbox, callback security, document storage, malware scanning, reviewer permissions, and retention approved. The current provider remains disabled/fail-closed.
- [ ] Deployment: runtime secrets are not included in images, mobile bundles, command arguments, source control, or public logs; rotation and incident contacts are known.

## Local development

### Backend

```sh
cd Android/Backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn main:app --reload
```

Root `.env` supplies local settings. For a PostgreSQL development database, provide a trusted CA file and verified connection details. With no `DATABASE_URL`, the backend may use a local SQLite file for development; SQLite is not a PostGIS substitute. API health routes are defined in `Android/Backend/routers/health.py`.

### Android

Provide the private Firebase `google-services.json`, populate root `.env`, and generate native configuration if absent. Open the `Android/` project in Android Studio or run the Gradle wrapper. Emulator API origin: `http://10.0.2.2:8000`; real devices need a reachable development backend URL.

### iOS

Open `iOS/Errno.xcodeproj` in Xcode, resolve Swift packages, and use a compatible iOS 17+ simulator/device target. Provide the private Firebase `GoogleService-Info.plist` and native local config. For local simulator backend access use a host-reachable API URL.

### Admin

```sh
cd Admin
npm ci
npm run dev
```

Vite reads the root environment file. `VITE_API_BASE_URL` should point to the backend. The authenticated Admin UID must also have persisted backend permissions.

### WhatsApp gateway

Local process (after exporting root `.env`):

```sh
cd WhatsAppGateway
npm ci
npm start
```

For Docker, create the external private network once if it does not exist, then run from the repository root:

```sh
docker network create errno-private
docker compose --env-file .env -f WhatsAppGateway/compose.yaml up -d --build
```

The network creation command will report an error if the named network already exists; do not remove a shared network just to rerun it.

## Build and test commands

Run commands from the indicated component directory. These commands do not apply database migrations.

| Component | Command |
|---|---|
| Android debug build and unit tests | `cd Android && bash gradlew :app:assembleDebug :app:testDebugUnitTest` |
| Android signing fingerprints | `cd Android && bash gradlew signingReport` |
| iOS dependency resolution | `xcodebuild -resolvePackageDependencies -project iOS/Errno.xcodeproj -scheme Errno` |
| iOS simulator build | `xcodebuild -project iOS/Errno.xcodeproj -scheme Errno -sdk iphonesimulator -configuration Debug CODE_SIGNING_ALLOWED=NO` |
| iOS tests | The current `Errno` scheme contains only the app target; no XCTest target is listed. |
| Backend suite | `cd Android/Backend && .venv/bin/python -m pytest -q` |
| Backend maps/booking focus | `cd Android/Backend && .venv/bin/python -m pytest tests/test_maps.py tests/test_mobile_workflows.py -q` |
| PostgreSQL/PostGIS integration | Set `ERRNO_TEST_DATABASE_URL` to a dedicated disposable test database only, then run the relevant integration tests. Never use production. |
| Admin tests/build | `cd Admin && npm test && npm run build` |
| WhatsApp gateway tests | `cd WhatsAppGateway && npm test` |
| Python syntax check | `python3 -m compileall -q Android/Backend` |
| Patch whitespace | `git diff --check` |

Backend tests import the database module. Use a dedicated disposable database and correct TLS settings for PostGIS integration tests. Do not infer that tests passed when a database-dependent test was skipped or blocked.

## Deployment operations

- Build and deploy each service through the organization's reviewed process. No repository command deploys the system automatically.
- Put database, Firebase Admin, Razorpay, notification encryption, WhatsApp, and DigiLocker secrets in the deployment secret manager. Do not bake them into images or mobile bundles.
- Configure PostgreSQL TLS verification and trusted CA paths. Use managed runtime identity/ADC where possible for Firebase Admin.
- Apply only the verified migration chain for the actual deployed schema, after backup, generated-SQL review, staging rehearsal, and change approval. Never use app startup to migrate.
- Run `services.prebooking_dispatcher` and `services.notification_dispatcher` as separate supervised processes with restart/health monitoring. The API process does not start them.
- Keep the WhatsApp gateway private on `errno-private`, protect its persistent session volume, and do not publish its port.
- Restrict and monitor Google Maps keys, set quotas and billing alerts, enable only the two Maps SDKs, and verify both application identifiers/signers.
- Before enabling payment, push, KYC, or WhatsApp features, validate provider credentials, webhook/callback registration, network reachability, permissions, retention, and rollback plans in a non-production environment.

`Android/Backend/deploy/errno-prebooking-dispatcher.service.example` is a systemd unit starting point. Adjust service user, virtualenv, application path, and environment-file path before installing it. Keep secrets out of the unit file.

## Troubleshooting

| Symptom | Checks |
|---|---|
| PostgreSQL connection fails | Confirm `DATABASE_URL`, CA path, hostname/certificate chain, and `sslmode=verify-full`. The app deliberately does not fall back to SQLite for a failed PostgreSQL connection. |
| PostGIS/nearby-worker features unavailable | Use PostgreSQL with PostGIS and the required canonical schema; SQLite cannot validate spatial queries. Confirm job coordinates and fresh foreground worker presence. |
| Android map blank | Verify the Android SDK key, package and signing SHA-1 restrictions, Maps SDK activation, billing, network, and generated `Android/gradle.properties.local`. |
| iOS map blank | Verify the iOS SDK key, `com.errno.app` restriction, Maps SDK activation/billing, and generated `iOS/Local.xcconfig`; the key is loaded at app launch. |
| Address lookup unavailable | Photon requires network access. Manual address editing and coordinate pin selection remain available; do not add Google Places/Geocoding as a workaround without a product decision. |
| Android Firebase sign-in fails | Check private `google-services.json`, Firebase package/OAuth registration, and debug/release SHA fingerprints. |
| iOS Firebase/sign-in fails | Check private `GoogleService-Info.plist`, bundle ID, URL scheme, signing and Firebase registration. |
| FCM is queued but not delivered | Verify separate notification worker, push flag, Firebase Admin credentials, token registration, APNs setup, device permission, and provider delivery status. Queue acceptance is not device receipt. |
| Admin login succeeds but API returns 403 | Verify the Firebase UID and explicit active admin permission records; login alone grants no role. |
| WhatsApp OTP is unavailable | Check paired session, private network, gateway secret (minimum 32 random characters), backend enable flag, rate limits, and gateway logs. A transport acknowledgement is not proof of delivery. |
| DigiLocker returns `PROVIDER_SPEC_REQUIRED` | Expected until requester approval and the official provider protocol are implemented and validated. Do not use mock mode in production. |

## Security and privacy

- Never commit `.env`, `Android/Backend/.env`, `.env.local`, `Android/gradle.properties.local`, `iOS/Local.xcconfig`, Firebase service-account JSON, mobile Firebase configuration files, private signing material, API secrets, tokens, or KYC documents.
- `.env.example` contains placeholders only. Keep separate secrets per environment; restrict and rotate credentials if exposed.
- Firebase Admin, Razorpay key secrets/webhook secret, WhatsApp shared secrets, notification encryption/hash keys, DigiLocker credentials/state secret, database credentials, and KYC encryption keys are server-side secrets.
- Android/iOS Google Maps keys are embedded in apps at build/runtime and therefore are not private server credentials. Restrict them to their application and Maps SDK, monitor usage, and rotate if abused.
- Do not pass passwords or secrets as CLI arguments or shell history. Prefer secret managers and protected local files.
- Firebase authentication does not replace resource-level authorization. Backend routes resolve persisted identity and enforce ownership/permissions.
- Exact location is sensitive. Worker location is foreground-only and visible only through authorized job/presence flows. KYC documents must remain encrypted, quarantined until scanned, access-controlled, and subject to an approved retention policy.
- Push payloads must not include phone numbers, KYC identifiers/documents, payment credentials, or precise addresses. Clients must re-fetch authorized records after notification taps.
- Treat all migrations as data changes. Do not apply, downgrade, or test against production without a separately reviewed change process and backup.

## Known limitations and audit findings

- Native map display requires correctly configured, billing-enabled Google Maps SDK keys. Build success alone does not verify map tiles or app restrictions on a real device.
- Photon is an external address search/reverse-lookup dependency and can be unavailable or rate limited. Manual address entry is the fallback.
- Worker GPS and location sharing require permission and foreground app use. Nearby discovery requires PostGIS and fresh worker presence.
- OSRM remains only as a backend compatibility endpoint; native UI does not provide route geometry, live traffic ETA, or in-app navigation.
- The canonical and legacy Alembic/model histories have documented schema drift. Confirm deployed schema before choosing an upgrade path. No production migration status is asserted here.
- Pricing examples in historical notes are drafts/proposals, not approved or active prices, commissions, multipliers, or effective dates. Admin activation requires explicit permissions and configured rules.
- Pre-booking dispatch requires a supervised dispatcher and the notification outbox worker. Worker invitations are not applications and FCM is independently retried.
- FCM/APNs delivery, real device token pairing, APNs entitlement/key configuration, and notification tap-to-business-detail navigation are not verified by repository builds.
- Razorpay payment verification code does not settle outstanding business policy for cancellations, no-shows, refund eligibility, cash ownership, partial refunds, or provider fee responsibility. External payout completion is manual/externally evidenced.
- Official DigiLocker access, sandbox credentials, issuer proof validation, callback protocol, and production retention/storage operations remain pending. Mock mode is for tests/development only.
- WhatsApp gateway relies on Baileys' unofficial protocol; account restrictions/disconnections are possible. Keep it private and do not use for bulk messaging.
- Admin UI routes may be visible even where a canonical business contract or operational setup is incomplete. Backend RBAC remains authoritative.

### Configuration audit summary

The native map migration is present on `main`. Android uses package `com.erno.app`; iOS uses bundle ID `com.errno.app`. No Google Routes/Navigation SDK dependency is part of Phase 1. Backend PostGIS, nearby discovery, dispatch, WebSocket tracking, FCM, and existing coordinate contracts remain in the application. Photon is still used for search/reverse lookup and OSRM remains in the backend for compatibility. Maps SDK activation, restricted keys, billing/quota review, device runtime verification, and production database schema state remain owner/operator responsibilities.
