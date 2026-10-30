# ERRNO Mobile Backend Integration Report

**Date:** 2026-10-30
**Scope:** Android, iOS and shared FastAPI workflows. No deployment, commit, production migration or production data write was performed.

## Executive summary

The mobile apps now use the shared FastAPI service for Firebase-backed user profiles, shop owner profiles, job browsing and posting, job applications, shop-owner application decisions, owner job lists and assigned-worker job lists. FastAPI resolves the caller from a verified Firebase UID and persists the records into the existing `users`, `shops`, `jobs` and `applications` models. Neither mobile client connects directly to Supabase.

The previous Android fixed-code OTP bypass has been removed. Both platforms retain their OTP screens but cannot authenticate through OTP until a verified provider exists. The simulated DigiLocker path no longer collects Aadhaar data or reports successful verification. The existing Admin API continues to use the same canonical tables and was not changed in this work.

**Result: Partially integrated and locally verified.** The end-to-end workflow contracts pass against isolated SQLite-backed FastAPI tests. Android debug/unit-test tasks and the iOS simulator build pass. A real Firebase Google sign-in against the configured project and a live Supabase operation were intentionally not run. Payment, ratings, worker application-history presentation, and job completion remain outside the verified persisted path.

## Git and data safety

- Worktree branch remains `feature/admin-production-integration`.
- Existing uncommitted work was preserved. The initial worktree already contained edits under `Admin/` and `Android/Backend/tests/test_admin_api.py`; those were left intact and are not attributed to this implementation.
- No commit, push, deploy, production migration, production Firebase user operation, or production Supabase data operation was performed.
- Integration tests use a per-test in-memory SQLite database. The canonical PostgreSQL integration test was skipped because `ERRNO_TEST_DATABASE_URL` was not set.
- No database migration was required: new endpoints use existing columns and tables.

## Authentication and authorization

### Implemented

- Android and iOS continue to use Google Sign-In through Firebase Authentication.
- Authenticated business API calls carry Firebase ID tokens in `Authorization: Bearer ...`; clients do not persist tokens in application preferences or local storage. Android obtains tokens from Firebase Auth and Firebase handles refresh of expiring tokens; iOS requests tokens from the current Firebase user for protected calls.
- FastAPI verifies Firebase tokens using the existing Firebase Admin verifier, then resolves the persisted user from the verified Firebase UID. Shop and job ownership is derived from that database user, never from caller-supplied phone numbers or owner IDs.
- Existing profile onboarding remains one-time: users can select `worker` or `shop_owner`; clients cannot change an already selected role to another role.
- Logout continues to clear the Firebase session on-device.
- `/auth/send-otp` and `/auth/verify-otp` continue to return HTTP 503 until a real OTP provider is configured. Android’s demo token/code path and both platform fixed-code OTP prompts have been removed.
- DigiLocker is explicitly unavailable. The apps no longer treat a fixed code or local action as identity verification.

### Not verified against production identity services

Tests replace the Firebase token verifier with controlled test identities. No live Google Sign-In, token revocation check, Firebase account provisioning or production Firebase project call was executed in this task.

## Backend changes

### New or expanded contracts

| Method/path | Functionality | Authorization |
| --- | --- | --- |
| `GET /shops/me` | Read caller’s shop; returns JSON `null` when not created and does not create placeholder data | Active `shop_owner` / legacy `shopkeeper` |
| `PUT /shops/me` | Create/update shop name, address and category | Active `shop_owner` / legacy `shopkeeper` |
| `GET /jobs/mine` | Read jobs from the authenticated owner’s shop(s) | Shop owner |
| `GET /jobs/worker/mine` | Read jobs assigned to the authenticated worker | Worker |
| `GET /jobs/applications/me` | Read the caller’s own application records | Worker |
| `GET /jobs/applications/owner` | List applications for owned jobs, returning only applicant name/ID and job/application metadata | Shop owner |
| `GET /jobs/{job_id}/applications` | Read applications for one job after verifying its ownership | Owning shop owner |
| `PATCH /jobs/{job_id}/applications/{application_id}` | Accept/reject a pending application; acceptance assigns its worker, sets the job to `assigned`, and rejects other pending applications in the same transaction | Owning shop owner |

Existing `POST /jobs`, `GET /jobs`, `GET /jobs/{id}`, `POST /jobs/{id}/apply`, profile routes and Admin API remain the shared source of persisted data. Applying to a job now requires it to be `open`. Existing status mutation still uses the lifecycle validator; assigning a worker through that route now requires an accepted application.

Shop/job request schemas now reject unknown fields and validate lengths and positive pay. Shop reads no longer create a default “Rahul General Store” record as a read side effect.

### Persistence

The new endpoint tests verify that users, shops, jobs and applications are persisted and related in the isolated database. The Admin Portal queries these same canonical tables, so records created through these routes will appear through its existing API after deployment and environment configuration are aligned. That Admin reflection was not tested against a live Supabase instance in this task.

## Android integration

### Implemented

- Added [ErrnoMobileApi.kt](Android/app/src/main/java/com/erno/app/data/repository/ErrnoMobileApi.kt), a Firebase-token-authenticated API client for live job reads, owner jobs, worker assigned jobs, posting, applying, shop profile reads/writes, profile reads/writes, owner applications and application decisions.
- Worker marketplace loads open jobs from `GET /jobs?status_filter=open`. Selecting the existing primary action submits `POST /jobs/{id}/apply`; the UI now reports an application submission rather than pretending the worker was hired.
- Shopkeeper job lists and dashboard load from `/jobs/mine`. Posting sends the current UI draft to `POST /jobs` and only navigates to success after the API call succeeds.
- Shopkeeper profile reads `/api/v1/users/me` and `/shops/me`; editing saves the user name and shop fields through authenticated backend calls.
- Applications screen loads real owner applications and sends accept/reject decisions to the API. It no longer silently mutates only local state.
- Loading, retry, and API error messages were added to worker and owner job/application surfaces.
- OTP code/token simulation was removed. The DigiLocker screen no longer accepts or submits Aadhaar data.

### Limitations

- The Android worker’s application list/history screen is not yet hydrated from `/jobs/applications/me`; the application submission itself is persisted. Assigned jobs are loaded from `/jobs/worker/mine`.
- Existing earnings, payment settlement, ratings/reviews, and job-completion UI are still local/demo behavior. No API is represented as completing a payment.
- Owner shop address/category editing is not exposed as editable fields in the current UI; the API supports those fields and existing profile save updates shop details.
- No live API request was made from an Android emulator/device with a real Firebase session.

## iOS integration

### Implemented

- Added Firebase ID token access for protected API calls and expanded `BackendRepository` contracts for owner/worker jobs, applications, profile/shop changes, posting and application decisions.
- The production worker catalog/detail remains backed by `GET /jobs` and `GET /jobs/{id}`. The primary detail action now creates a real worker application and displays API success/errors.
- The shopkeeper job-post wizard now injects `BackendJobService` rather than `MockJobService`. It submits the selected category, pay, duration, schedule and location fields to `POST /jobs`; the returned server ID is used in the local UI cache.
- Shopkeeper dashboard and jobs list refresh from `/jobs/mine`; shopkeeper profile refreshes from `/shops/me` and editing persists the user name and shop profile.
- Shopkeeper applications load through `/jobs/applications/owner`; accept/reject actions use the protected decision endpoint. Applicant API responses do not expose phone or email fields, so the old invented phone-call path was removed.
- Worker “My Jobs” loads assignments from `/jobs/worker/mine` with loading/retry/error behavior.
- Successful Firebase profile data now seeds the local display model with the server’s persisted user UUID, fixing the previous mismatch between local and backend IDs.
- Fixed OTP demos and simulated DigiLocker collection/verification were removed.

### Limitations

- The worker UI does not yet present pending/rejected application history from `/jobs/applications/me`; submitting an application is persisted, and accepted assignments appear in My Jobs.
- Existing payment, earnings, completion, reviews/ratings and other unsupported features remain local/demo-only and are not claimed as persisted.
- No XCTest target exists in the current Xcode project, so no automated iOS unit/UI test suite could be run without adding a separate test target. The simulator build is verified.
- No live iOS Firebase sign-in or API call was executed.

## API documentation

Added [MOBILE_API.md](Android/Backend/MOBILE_API.md) with the shared mobile contracts, auth rules, response/error behavior and persistence expectations. Runtime OpenAPI remains available from FastAPI at `/docs` and `/openapi.json`.

## Tests and build verification

| Check | Command | Result |
| --- | --- | --- |
| Backend isolated workflow/auth/Admin suite | `PYTHONPATH="$PWD/Android/Backend" DATABASE_URL=sqlite:// /tmp/errno-backend-verify/bin/pytest -q Android/Backend/tests` | **27 passed, 1 skipped**. Skip is the optional canonical PostgreSQL integration test because no disposable PostgreSQL URL was provided. |
| Android unit tests and debug build | `bash ./gradlew :app:testDebugUnitTest :app:assembleDebug` from `Android/` | **BUILD SUCCESSFUL**. Existing Gradle/deprecation warnings remain. |
| iOS simulator build | `xcodebuild -quiet -project Errno.xcodeproj -scheme Errno -configuration Debug -destination 'generic/platform=iOS Simulator' -xcconfig Local.xcconfig CODE_SIGNING_ALLOWED=NO build` from `iOS/` | **Exit 0**. |
| Whitespace/diff validation | `git diff --check` | Passed at the time checked. |

Backend tests cover invalid/missing tokens through the verifier dependency, role gates, ownership rejection, shop/job/application creation, application decision/assignment, sensitive-field minimization, role/input validation, persistence counts, and disabled fixed-code OTP routes. These tests use a verifier stub and isolated SQLite, not production Firebase or Supabase.

## Database and migration status

- Existing canonical tables used: `users`, `shops`, `jobs`, `applications`.
- No new tables/columns/indexes were introduced; there are **no migration files to apply** for this change.
- The shop “read” endpoint was made side-effect-free; explicit `PUT /shops/me` performs shop writes.
- No migration was applied and no production Supabase data was changed.
- A disposable PostgreSQL migration/integration test remains desirable because this run exercised the persistence path on SQLite only.

## Preserved Admin integration and mobile compatibility

- No Admin Portal routes, RBAC models or Admin API handlers were changed by this implementation. Existing uncommitted Admin work was preserved.
- Admin dashboard/list endpoints query the same models used by the mobile workflow. An end-to-end UI check of new records in Admin was not performed.
- Android and iOS Firebase login/profile routes and role vocabulary are retained. Both mobile clients use server-generated IDs for remote records. The iOS build and Android debug build passed.
- No production Firebase or Supabase configuration/data was touched.

## Remaining issues and production readiness

### Required before production rollout

1. Configure a stable HTTPS `ERRNO_API_BASE_URL` / iOS `ErrnoAPIBaseURL`; do not rely on an expiring Cloudflare tunnel URL.
2. Run isolated PostgreSQL integration tests against a disposable PostgreSQL instance and verify deployed Supabase schema/constraints before rollout.
3. Perform authorized staging Firebase Google Sign-In tests and verify user creation, token refresh, account disable/revocation and logout behavior.
4. Add worker application-history screens using `/jobs/applications/me` on both platforms.
5. Decide and implement server-backed job completion, payment settlement, ratings/reviews and earnings contracts before presenting those as live features.
6. Add iOS XCTest target and frontend/domain tests; current iOS verification is compile-only.
7. Review deployment CORS origins and mobile API host allowlists for production.

### Verdict

**PARTIALLY INTEGRATED — not production ready.** The core create/list/apply/review/assign persistence flow is implemented and verified through isolated FastAPI/SQLite tests; mobile compilation succeeds. Real Firebase/Supabase end-to-end validation and several non-core/legacy UI features remain unverified or local-only. No production data changes were made.
