# ERRNO notification system

## Architecture and truth model

Business handlers persist notification inbox rows and outbox rows in the same SQLAlchemy transaction as the business state change. A separately operated worker leases committed outbox records using `FOR UPDATE SKIP LOCKED`, then calls Firebase Admin Messaging. Push is best effort; the PostgreSQL inbox is authoritative. An `accepted_by_fcm` result means Firebase accepted the request, not that a device displayed it or a person saw it. The worker is deliberately not started by Uvicorn.

## Events and recipients

Implemented event integrations:

| Event | Recipient | Trigger |
|---|---|---|
| `booking_created` | Booking owner | Job creation, after validation and before commit |
| `worker_assigned` | Shopkeeper | Assignment decision in the assignment transaction |
| `job_assigned` | Assigned worker | Assignment decision |
| `job_started` | Shopkeeper | Authorized worker start transition |
| `booking_cancelled` | Assigned worker | Authorized cancellation transition |
| `job_completed` | Assigned worker | Shopkeeper completion transition |
| `payment_success` / `payment_failed` | Payer and payee | Verified Razorpay API response or authenticated webhook |
| `kyc_status_changed` | Worker account | Admin manual-review status transition |

No unsupported arrival/en-route status, complaint, payout completion, rating eligibility, or broadcast job-alert event is synthesized. Those require a corresponding committed business transition and, for job alerts, the existing server-side matching criteria. Presence heartbeats never emit notifications. Future integrations should call `queue_notification` with a deterministic event ID inside the business transaction.

Admin event helpers only resolve accounts explicitly provisioned with existing Admin RBAC. Current system has manual KYC review and payment/job records; complaint/dispute triggers remain future integration points.

## Database schema and migration

Canonical additive Alembic revision: `d17a6c90e241`, parent `9f23b6c4d1a8`. It adds `notifications`, `notification_devices`, `notification_outbox`, `notification_delivery_attempts`, `notification_preferences`, and a registration throttle table, with recipient/device foreign keys, unique deduplication and indexes for inbox and dispatch queries. Apply only through the normal reviewed deployment migration process; this implementation does not run a production migration.

Inbox notifications are retained independently from OS permission. Push preferences suppress only push attempts; they do not remove transactional inbox items. Device tokens are AES Fernet encrypted and HMAC-SHA256 hashed. Configure separate high-entropy secrets, and back them up through the existing secret-management process before enabling device registration.

## API

All routes use the existing authenticated Firebase/ERRNO session identity. No client user ID or role is accepted.

* `POST /api/v1/devices/register` — `{platform, deviceId, fcmToken, appVersion}`
* `DELETE /api/v1/devices/{device_id}` — owner-scoped invalidation
* `GET /api/v1/notifications?cursor=&limit=&category=&unread=` — keyset pagination
* `GET /api/v1/notifications/unread-count`
* `PATCH /api/v1/notifications/{id}/read`
* `PATCH /api/v1/notifications/read-all`
* `DELETE /api/v1/notifications/{id}`
* `GET/PATCH /api/v1/notifications/preferences`
* `GET /api/v1/admin/notifications` — `notifications.read`
* `GET /api/v1/admin/notifications/delivery` — `notifications.audit`
* `POST /api/v1/admin/notifications/delivery/{outbox_id}/retry` — `notifications.manage`, audited

There is no public event-ingestion endpoint. Push data contains routing IDs only and must never be treated as authorization.

## Worker and reliability

Run from `Android/Backend` with `python -m services.notification_dispatcher`. It polls the database, leases events, retries retryable errors with capped exponential backoff and jitter, invalidates unregistered tokens and records per-device attempts. Expired `sending` leases can be reclaimed after worker failure. Configure `NOTIFICATION_MAX_ATTEMPTS`, `NOTIFICATION_RETRY_BASE_SECONDS`, `NOTIFICATION_RETRY_MAX_SECONDS`, `NOTIFICATION_LEASE_SECONDS`, `NOTIFICATION_WORKER_POLL_SECONDS`, `NOTIFICATION_RETENTION_DAYS`, and `NOTIFICATION_DELIVERY_LOG_RETENTION_DAYS`. Old attempts and expired inbox/outbox history are cleaned every six hours. Expired notifications are dropped before provider submission. Exhausted or permanent failures are retained as `permanently_failed`; `no_devices` and preference suppression are recorded as terminal queue outcomes. Admin retry resets an eligible queue item and writes an audit log.

For PostgreSQL, the queue claim uses `SKIP LOCKED`. SQLite is suitable only for local development and isolated tests. Provider outages and absent credentials never result in a fabricated accepted state. Delivery attempt/queue status is operational telemetry, not device delivery confirmation.

## FCM configuration

Required backend settings (never commit actual secrets):

```dotenv
NOTIFICATION_WORKER_ENABLED=true
NOTIFICATION_PUSH_ENABLED=false
NOTIFICATION_MAX_ATTEMPTS=6
NOTIFICATION_RETRY_BASE_SECONDS=15
NOTIFICATION_RETRY_MAX_SECONDS=3600
NOTIFICATION_LEASE_SECONDS=120
NOTIFICATION_WORKER_POLL_SECONDS=2
NOTIFICATION_TOKEN_ENCRYPTION_KEY=
NOTIFICATION_TOKEN_HASH_SECRET=
FIREBASE_PROJECT_ID=
GOOGLE_APPLICATION_CREDENTIALS=
```

`NOTIFICATION_TOKEN_ENCRYPTION_KEY` must be a Fernet key generated by the Python `cryptography` package; the hash secret must be at least 32 random bytes. Firebase Admin reuses existing `firebase_auth.firebase_app()` initialization and ADC/service-account file loading. FCM uses the official Firebase Admin SDK (HTTP v1); no legacy server key or mobile credential is used. Push remains disabled until credentials, token protection and project configuration are verified.

## Android

The native app uses Firebase Messaging and an Android `FirebaseMessagingService`; channels are created for Booking Updates, Job Progress, Payments, Account & Verification and Promotions. Background notification payloads are left to Android's FCM handling; the service creates local alerts only in foreground to avoid duplicate background alerts. Android 13+ requires `POST_NOTIFICATIONS` runtime permission; the application should explain the user benefit before requesting permission and must preserve in-app inbox access on denial. The app needs a configured `google-services.json`. Device sync must run after login and token refresh; account logout should call the authenticated device delete route before clearing session credentials.

## iOS / APNs

Use Firebase Messaging with `UserNotifications`, APNs registration, FCM token refresh, and authenticated device registration. Enable Push Notifications capability and Remote notifications background mode only if the app's behavior requires it. Confirm bundle ID and entitlements match Firebase; upload the APNs authentication key in Firebase Console. Do not place APNs or Firebase service credentials in the app. Do not change signing settings until the team configures its Apple account. iOS delivery and background execution are best effort.

## Admin and access control

Admin endpoints use the existing `require_admin` dependency and exact `notifications.read`, `notifications.audit`, and `notifications.manage` permissions. Permissions must be explicitly assigned by an operator. Delivery monitoring distinguishes queue outcomes and `accepted_by_fcm`; it cannot assert device display or receipt. Complaint/dispute alerts await a real ERRNO complaint feature.

## Privacy, retention and preferences

Push text is generic and excludes phone numbers, KYC identifiers/documents, payment credentials and precise addresses. Routing payload keys are allowlisted. Server-side entity APIs continue to enforce authorization after taps. Marketing defaults off. Transactional inbox records remain available when promotional preferences or OS push permission are disabled. A cleanup/retention job is not yet configured; define retention duration with operations before deleting inbox/audit history.

## Tests and SQL review

Backend focused tests: `cd Android/Backend && .venv/bin/pytest tests/test_notifications.py`. Python compile: `python -m compileall -q Android/Backend`. Generate SQL for review without applying it using the canonical Alembic configuration and a disposable PostgreSQL URL:

```sh
cd Android/Backend
  ERRNO_DATABASE_URL='postgresql://review-user:review-password@localhost/errno_phase22_test' \
  ERRNO_ALLOW_LOCAL_TEST_DB=1 \
  .venv/bin/alembic -c alembic_canonical.ini upgrade 9f23b6c4d1a8:d17a6c90e241 --sql
```

Do not use production connection details for SQL generation. Android: `cd Android && ./gradlew :app:testDebugUnitTest :app:assembleDebug`. iOS: `xcodebuild -project iOS/Errno.xcodeproj -scheme Errno -destination 'platform=iOS Simulator,id=...' -derivedDataPath /tmp/errno-derived CODE_SIGNING_ALLOWED=NO -jobs 2 build`. Admin: run the package's test and production build scripts. Gateway: run its package test script. Check `git diff --check` before review.

## Deferred external setup and known integration gaps

Repository code cannot verify Firebase project credentials, APNs key, mobile bundle/package registration, live device token pairing, real push delivery, production database migration, deployed worker, monitoring alerts, or production rollout. Those remain explicitly unverified. This implementation does not deploy, migrate production, commit, or push.

The mobile inboxes and push-tap handling currently route taps to the authenticated inbox; selecting a push does not yet navigate to a specific authorized booking/payment/KYC detail screen. The repository has no committed transition for worker en-route/arrival, complaint/dispute, rating eligibility, payout completion, or a worker matching service, so those events remain future integrations. The worker does not implement scheduled job reminders because no durable scheduler exists. Firebase/APNs credentials, the production migration, live token pairing, real-device push behavior, deployment and operational alert thresholds remain unverified. Firebase Swift Package Manager dependencies resolved successfully (Firebase 11.15.0 and FirebaseMessaging included). The `Errno` iOS Simulator build completed for arm64 and x86_64, and the freshly built app installed and launched to the ERRNO splash screen on the existing iOS 27.1 simulator. The repository UI validation suite passed 5 of 6 tests on its first run; the catalog case initially lacked its local fixture server, then passed when rerun against an isolated in-memory fixture API. This validates simulator launch and app UI regression flows only; it does not validate APNs/FCM delivery or notification permission behavior on a physical iPhone.
