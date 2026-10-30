# ERRNO Admin Portal Phase 1 + 2 Implementation Report

**Date:** 2026-10-30  
**Scope:** Admin authentication and authorization, backend security hardening, live dashboard, shop-owner/worker/job management, audit logging, isolated verification.  
**Repository state:** Work remains uncommitted on the backup branch identified below.

## 1. Executive summary

The Admin Portal is now integrated as a React/Vite application using the shared FastAPI backend. The operational frontend replaces demo login with Firebase Google Sign-In code, Firebase ID-token observation/refresh, and backend verification at `/api/v1/admin/me`. Admin APIs resolve the verified Firebase UID to a persisted server-side permission record; client-supplied role data is not consulted. Dashboard, shop-owner, worker, and job pages call live API services and expose loading, empty, failure, retry, pagination, and mutation feedback states. Successful admin mutations and access changes write audit records transactionally.

Backend security changes disable the legacy fixed-code/fallback-token OTP behavior, require verified Firebase identity for registration/profile updates, constrain CORS, sanitize health failures, and validate job status transitions. The new schema was upgraded/downgraded/re-upgraded on a disposable local PostgreSQL cluster without losing a pre-existing user row. Backend, frontend, and Android verification passed; iOS simulator build also passed. No production Firebase or Supabase resource was used.

**Verdict: Partially integrated; not production-ready yet.** Code paths and automated tests are implemented, but a real Firebase web configuration, provisioned administrator, deployed migration, and live end-to-end verification are not present. The existing mobile phone-OTP path will now return a deliberate 503 until a real OTP provider is configured; this closes the bypass but is a known mobile workflow compatibility limitation.

## 2. Git safety and backup information

- Work began with existing uncommitted changes from the prior merge. Those changes were preserved; no reset, clean, commit, or push was performed.
- A timestamped backup branch was created from the starting HEAD: `backup/admin-phase12-20261030-172235`.
- Current branch remains that backup branch. All changes in this report are uncommitted.
- Existing temporary local tunnel configuration was preserved in ignored local config. Admin local environment configuration is also ignored (`Admin/.env.local`); no URL or credential value is reproduced here. `.env.example` files contain placeholders only.
- The junior developer’s source directory was not modified. Production Firebase and Supabase were not accessed.

## 3. Authentication architecture

### Admin browser flow

1. Firebase Web SDK initializes only from Vite environment configuration and requires Firebase project ID `errno-pvt-ltd`.
2. Google popup sign-in is provided through `GoogleAuthProvider`.
3. `onIdTokenChanged` restores the Firebase session and tracks token refreshes.
4. Protected UI requests an ID token from the current Firebase user and sends it as `Authorization: Bearer` to the shared API. The token is not stored in localStorage/sessionStorage.
5. FastAPI verifies the token through the existing Firebase Admin verifier, resolves its UID against `admin_permissions`, and checks active state and required permission.
6. Missing/invalid/revoked Firebase identity returns 401; valid identity without an active matching permission returns 403.
7. A 401 triggers one forced token refresh/retry in the API client. Logout calls Firebase `signOut`; unauthorized UI offers a retry/sign-out path.

Frontend Google sign-in is implemented and unit-tested with mocks. It has not been tested against the live Firebase project because actual web client configuration and an authorized test administrator were not provided in the repository/runtime.

## 4. Admin authorization design and provisioning

`AdminPermission` persists Firebase UID, email, permission set, active state, grant actor, reason, and timestamps. Runtime access is UID-based and permission-scoped. An existing application `User.is_active == false`, if present, also denies admin access. No user is automatically promoted and there is no public registration or self-promotion endpoint.

Permissions currently supported: `dashboard.read`, `users.read`, `users.manage`, `jobs.read`, and `jobs.manage`. Owner/worker records share users scopes; job actions require job scopes.

`Android/Backend/tools/provision_admin.py` implements explicit grant/revoke operations. It verifies target and operator Firebase records, requires Google-linked verified email, requires exact target confirmation and a reason, and supports bootstrap only when no active admin exists. The database mutation and audit record are committed together. The utility was unit-tested but not run against a real Firebase account or any non-disposable database.

Operator steps and example commands (with placeholders) are in [ADMIN_OPERATIONS.md](Android/Backend/ADMIN_OPERATIONS.md). Revocation sets `active=false`, preserves history, and causes subsequent admin requests to be denied. Do not use example placeholders as real identities.

## 5. Backend security fixes

- **Legacy OTP:** `/auth/send-otp` and `/auth/verify-otp` no longer emit/accept a fixed OTP or fallback bearer token. Both return 503 until a real provider is configured. This is safer than silently retaining demo behavior, but affects any mobile flow still using OTP.
- **Registration:** `/auth/register` requires a verified Firebase identity, verifies the phone against the Firebase phone claim, safely links only an unclaimed matching legacy phone account, disallows arbitrary extra fields, and does not overwrite an established role/identity. Only supported onboarding roles are accepted.
- **CORS:** explicit localhost development origins and `https://admin.errno.in` by default; deployment can set an explicit comma-separated allowlist. Wildcard + credentials is not used.
- **Health:** existing `/health` remains public and operational. Database errors are logged server-side and returned as sanitized 503 details.
- **Job lifecycle:** existing owner job status operations now validate supported states and allowed transitions while retaining ownership checks. Admin updates use the same lifecycle validation plus permission and audit requirements.
- **Admin auth:** reusable `require_admin` dependency enforces verified identity, persisted active permission, optional scope, and disabled-user denial.
- **Input and object access:** list pagination is bounded, search/filter inputs are validated, profile/detail queries are scoped to the target record, and mutations expose only supported fields.

## 6. Database schema changes and migration

Canonical existing tables remain `users`, `otps`, `shops`, `jobs`, and `applications`. Added:

- `admin_permissions`: unique indexed Firebase UID, JSON permission set, active flag, grant metadata and timestamps.
- `admin_audit_logs`: administrator UID, action, resource type/ID, outcome, JSON change metadata, server timestamp and indexes.

Migration: `Android/Backend/alembic_canonical/versions/8fa2137c5d20_add_admin_access_and_audit.py`, chained after the existing canonical revision. It is additive; downgrade drops only the two new tables. Downgrade therefore removes admin permission and audit history, so retain/export audit records before rollback. No production migration was applied.

**Migration verification:** PostgreSQL 16 disposable cluster; baseline migration, inserted existing user, upgrade to head, verified both new tables and original user, downgrade one revision, re-upgrade to head. All steps passed. The PostgreSQL-dependent existing pytest is still skipped unless `ERRNO_TEST_DATABASE_URL` is explicitly supplied; test suite used SQLite in-memory for ordinary API tests.

## 7. Admin API endpoint inventory

All `/api/v1/admin/*` endpoints require a Firebase bearer token and the named server-side permission.

| Method and endpoint | Permission | Request / response summary | Frontend use |
|---|---|---|---|
| `GET /api/v1/admin/me` | active admin | Firebase identity; returns server-side admin ID, UID, email, permissions, active state | Auth context / route guard |
| `GET /api/v1/admin/dashboard` | `dashboard.read` | Query aggregates, recent registrations/jobs, daily series; no request body | Dashboard |
| `GET /api/v1/admin/shop-owners` | `users.read` | Search, active filter, bounded limit/offset; records and pagination metadata | Owner list/search/filter |
| `GET /api/v1/admin/shop-owners/{user_id}` | `users.read` | Owner profile plus associated shops and jobs | Owner detail |
| `PATCH /api/v1/admin/shop-owners/{user_id}` | `users.manage` | Supported active-state update; updated record | Suspend/reactivate owner |
| `GET /api/v1/admin/workers` | `users.read` | Search, active filter, bounded limit/offset; records and pagination metadata | Worker list/search/filter |
| `GET /api/v1/admin/workers/{user_id}` | `users.read` | Worker profile and paginated application history | Worker detail/history |
| `PATCH /api/v1/admin/workers/{user_id}` | `users.manage` | Supported active-state update; updated record | Suspend/reactivate worker |
| `GET /api/v1/admin/jobs` | `jobs.read` | Search, supported status filter, bounded limit/offset | Job list/search/filter |
| `GET /api/v1/admin/jobs/{job_id}` | `jobs.read` | Job, shop/owner summary, applications | Job detail |
| `PATCH /api/v1/admin/jobs/{job_id}/status` | `jobs.manage` | Status transition request; updated job | Authorized audited status change |
| `GET /health` | Public | Database health status; sanitized failure response | System Health page |

List endpoints return server-side paginated data. Dashboard counts and daily series are SQL aggregates; records are not loaded wholesale to compute counts. Successful mutations record before/after supported fields in the same transaction as the change. Rejected mutations are written to server diagnostics without copying tokens or personal data; they are not inserted into the durable mutation audit table.

## 8. Frontend integration and feature inventory

The supplied portal was a React/Vite application whose page/component source was unavailable; its original large `Admin/src/main.js` bundle is preserved but is no longer the operational entry. `index.html` now loads a maintainable JSX entry with lazy-loaded route modules and shared services/components while preserving the visual styling and the existing 13 routes.

| Route/feature | Status | Data/action behavior |
|---|---|---|
| Login | Implemented; live Firebase config unverified | Google popup, auth state, server permission check; no demo credential path |
| Dashboard | Implemented and API-tested | Real aggregate/series; loading, empty/error/retry/refresh states; no mock fallback |
| Shop owners | Implemented and API-tested | Server search/filter/pagination, profile with shops/jobs, audited active-state change |
| Workers | Implemented and API-tested | Server search/filter/pagination, profile/application history, audited active-state change |
| Jobs | Implemented and API-tested | Server search/filter/pagination, details, validated audited status mutation |
| System health | Implemented | Calls public `/health`, reports actual API status |
| Bookings | Preserved; phase 3 unavailable | Visible unavailable state, no fake mutations |
| Categories | Preserved; phase 3 unavailable | Visible unavailable state, no fake mutations |
| Attendance | Preserved; phase 3 unavailable | Visible unavailable state, no fake mutations |
| Ratings | Preserved; phase 3 unavailable | Visible unavailable state, no fake mutations |
| Reports/disputes | Preserved; phase 3 unavailable | Visible unavailable state, no fake mutations |
| Notifications | Preserved; phase 3 unavailable | Visible unavailable state, no fake mutations |
| Settings | Implemented as local-only preferences/status | No server setting mutation is implied |

Feature counts: **6 live/functional paths** (login code, dashboard, owners, workers, jobs, health), **6 unavailable/demo-only module screens**, and **1 local-only settings screen**. The login UI flow is not live-project validated.

## 9. API integration matrix

The Admin API service centralizes bearer token injection, one forced refresh/retry after 401, status-aware errors (401/403/404/409/422/500), network failure handling, and `credentials: omit`.

| Frontend caller | Backend path | Data source/result |
|---|---|---|
| Auth context | `GET /api/v1/admin/me` | Verified Firebase identity + persisted admin permission |
| Dashboard page | `GET /api/v1/admin/dashboard` | Aggregates from users, shops, jobs, applications |
| Owner list/detail/action | `GET /api/v1/admin/shop-owners[/{id}]`, `PATCH /api/v1/admin/shop-owners/{id}` | Existing users/shops/jobs; active state only |
| Worker list/detail/action | `GET /api/v1/admin/workers[/{id}]`, `PATCH /api/v1/admin/workers/{id}` | Existing users/applications; active state only |
| Jobs list/detail/action | `GET /api/v1/admin/jobs[/{id}]`, `PATCH /api/v1/admin/jobs/{id}/status` | Existing jobs/shops/users/applications; valid transitions only |
| Health page | `GET /health` | Existing shared FastAPI health endpoint |

There is no direct Firebase database or Supabase client access from the Admin frontend. Android and iOS continue to use the existing shared backend/mobile endpoints.

## 10. Automated test and build results

Commands/results:

- Backend: `DATABASE_URL=sqlite:// PYTHONPATH=<repo>/Android/Backend /tmp/errno-backend-verify/bin/pytest -q <repo>/Android/Backend/tests` — **24 passed, 1 skipped**. Skip is the existing test requiring explicit disposable PostgreSQL test URL. Warnings include existing Pydantic/Starlette deprecations.
- Migration: isolated PostgreSQL 16 init + canonical upgrade + preserved-row assertion + admin table assertion + downgrade/re-upgrade — **passed**.
- Admin: `npm test` — **3 files, 17 tests passed**.
- Admin production build: `npm run build` — **passed**, Vite 8.3.4; lazy route chunks emitted. `npm audit` — **0 vulnerabilities**.
- Android: `bash gradlew :app:assembleDebug` — **BUILD SUCCESSFUL** (39 tasks; Gradle emitted existing deprecation notices).
- iOS: `xcodebuild -quiet -project Errno.xcodeproj -scheme Errno -configuration Debug -destination 'generic/platform=iOS Simulator' -xcconfig Local.xcconfig CODE_SIGNING_ALLOWED=NO build` — **passed**.

Firebase/Auth and API tests use mocks/local test data; no real Firebase sign-in, real admin token, tunnel/API deployment, or Supabase connection was tested. Thus automated authorization tests establish backend behavior under mocked verified claims, not production Firebase integration. The PostgreSQL migration test was local/disposable only.

## 11. Android and iOS compatibility

Android debug and iOS simulator builds pass. Existing Google Sign-In implementations and routes were not rewritten. Existing shared job ownership operations remain present and now reject invalid lifecycle values/transitions. Registration now requires Firebase verified identity, so unauthenticated legacy registration calls are rejected by design.

The OTP endpoints now return 503 until a real OTP provider is configured. Any Android/iOS screens still invoking these legacy endpoints will show an error rather than authenticate through the old demo fixed-code behavior. This needs an approved provider implementation before enabling phone OTP again. No mobile source flow was removed.

## 12. Remaining security issues and limitations

1. **High — no production administrator provisioned or live-tested.** This is intentional; an authorized operator must use the documented CLI after reviewed migration and change approval.
2. **High — live Firebase web configuration absent.** Admin `.env.example` has placeholders; configure the authorized public web app identifiers and Firebase authorized domains before deployment. Service-account credentials remain server-side.
3. **High — OTP provider unavailable.** Legacy OTP routes fail closed with 503; implement and test a real provider before relying on phone OTP mobile flows.
4. **Medium — migration not deployed.** Admin routes require the additive migration before use. Apply via the deployment migration process after review and backup.
5. **Medium — production CORS/proxy configuration pending.** Set the exact production/admin origins and ensure forwarded HTTPS/proxy settings are correct for deployment.
6. **Medium — operational policy needs review.** Confirm least-privilege scopes, admin audit retention/monitoring, user suspension semantics, and approval/ticket process.
7. **Low — dependency/toolchain deprecation warnings.** Backend tests report existing Pydantic v2, Starlette/httpx and `from_orm` deprecations; Android Gradle reports deprecated Android plugin APIs.
8. Phase 3 modules remain intentionally unavailable until canonical contracts are designed: bookings, categories, attendance, ratings, reports/disputes, notifications.

## 13. Deployment readiness

**`admin.errno.in`: Not ready to publish yet.** Required: production build artifact; Firebase Web app config for existing project `errno-pvt-ltd`; authorized domain and Google provider configuration; `VITE_API_BASE_URL` pointing at deployed `api.errno.in`; HTTPS; exact CORS allowlist; deployment secrets not embedded in frontend; and a provisioned admin after migration.

**`api.errno.in`: Not ready for admin traffic yet.** Required: reviewed migration applied; Firebase Admin credentials/project configured in server secret management; DB connectivity/backup; `ERRNO_CORS_ALLOWED_ORIGINS` exact allowlist; TLS/reverse proxy; health monitoring; operator audit/retention policy; OTP provider decision; and staging authorization verification.

Environment variable names (values omitted):

- Admin: `VITE_API_BASE_URL`, `VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_AUTH_DOMAIN`, `VITE_FIREBASE_PROJECT_ID`, `VITE_FIREBASE_APP_ID`.
- Backend (existing/deployment-specific): `DATABASE_URL`, Firebase Admin credential configuration (prefer workload identity/secret manager; `GOOGLE_APPLICATION_CREDENTIALS` only as a server-side option), `ERRNO_CORS_ALLOWED_ORIGINS`.

The temporary tunnel URL is local development configuration only and is not embedded in tracked frontend files or this report.

## 14. Files added and modified

**Added:** `Admin/.env.example`, Admin React auth/API/app/components/hooks/pages/tests/config/readme files; `Android/Backend/ADMIN_OPERATIONS.md`; `Android/Backend/alembic_canonical/versions/8fa2137c5d20_add_admin_access_and_audit.py`; `Android/Backend/cors_config.py`; `Android/Backend/job_lifecycle.py`; `Android/Backend/routers/admin.py`; `Android/Backend/routers/health.py`; `Android/Backend/tests/test_admin_api.py`; `Android/Backend/tools/provision_admin.py`; this report.

**Modified:** `.gitignore`; `Admin/index.html`; `Admin/package.json` and lockfile; `Admin/src/styles.css`; `Android/Backend/firebase_auth.py`; `Android/Backend/main.py`; `Android/Backend/models/__init__.py`; `Android/Backend/routers/auth.py`; `Android/Backend/routers/jobs.py`; `Android/Backend/schemas.py`; `Android/app/build.gradle.kts` (preserved local API configuration handling); prior `ADMIN_INTEGRATION_REPORT.md` remains in the worktree from the earlier merge.

No tracked file was intentionally removed. Generated `Admin/node_modules` and `Admin/dist`, local env files, and caches are ignored/excluded.

## 15. Final verdict and remaining tasks

**Classification: Partially integrated.** The admin UI and shared backend contracts are implemented, the permission boundary is enforced and tested, phase 2 data pages use real SQL-backed endpoints, audits/migrations are in place, and local builds/tests pass. Acceptance remains incomplete until an operator supplies real Firebase Web config, applies the reviewed migration to the target environment, provisions a verified administrator, validates live Firebase/API behavior in staging, and a real OTP provider is implemented if phone OTP remains a supported mobile flow. Phase 3 modules are deliberately not implemented.

Before production:

1. Configure Firebase web client values for the existing project and exact authorized origins.
2. Apply migration to a backed-up staging database, then follow normal production review.
3. Provision the first administrator using a verified UID and approved change ticket; verify 401/403/200 behavior end-to-end and revoke test access afterward.
4. Decide and implement the OTP provider or formally retire OTP mobile flow.
5. Run staging UI/API and mobile regression checks with real Firebase identities and reviewed data.
6. Confirm operational audit retention, alerting, backup, and rollback plan.
