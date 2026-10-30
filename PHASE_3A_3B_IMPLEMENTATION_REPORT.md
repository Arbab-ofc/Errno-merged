# ERRNO Phase 3A + 3B Implementation Report

**Scope:** Worker application history and role-authorized job lifecycle across FastAPI, Android, iOS, and Admin visibility.

## Executive summary

Implemented a real, paginated worker application history endpoint and surfaced it in Android and iOS with job/shop details, actual application status, details views, pending-application cancellation, loading, empty, error, retry, and pagination states.

Implemented canonical job transitions: `open → assigned → in_progress → completed`, with owner cancellation from `open` or `assigned`. Application acceptance remains the operation that assigns a worker. Only the assigned worker can start work; only the owning shop owner can confirm completion. Server-generated lifecycle timestamps are returned to mobile clients and the Admin API. Generic Admin status management was narrowed to cancellation of unstarted work so administrators cannot impersonate the assigned worker or shop owner. Admin authentication and permission resolution were not changed.

**Implementation status: Complete for the requested API and UI paths.** Local backend tests, both mobile builds, Admin tests/build, and an isolated migration smoke test passed. No live Firebase session, production data access, production migration, or deployment was performed.

## Changes made

### Backend and schema

- `GET /jobs/applications/me?limit=20&offset=0` now returns a page with total count, continuation flag, actual application status and creation timestamp. Each item embeds job title/status/location/pay/schedule and shop name/address/category.
- `DELETE /jobs/{job_id}/applications/me` cancels the authenticated worker’s pending application. It returns 404 for a missing application and 409 for an already decided/cancelled application.
- `POST /jobs/{job_id}/start` permits only the assigned worker to transition an assigned job to `in_progress`.
- `POST /jobs/{job_id}/complete` permits only the owning shop owner to confirm an in-progress job, and requires an assigned worker.
- `PATCH /jobs/{job_id}/status?new_status=cancelled` is limited to the owning shop owner cancelling an open or assigned job.
- Every mutation uses a row lock where supported, validates the current status and rejects duplicate/invalid transitions with HTTP 409. Role and ownership violations return HTTP 403.
- `JobResponse` includes `created_at`, `started_at`, `completed_at`, and `cancelled_at`. All lifecycle times are set by the backend in UTC.
- Admin job reads include those lifecycle timestamps. The Admin status API only permits cancellation before work starts; assignment, start, and completion remain tied to their designated business actors.
- Updated [`MOBILE_API.md`](Android/Backend/MOBILE_API.md) with the response contract, paging, lifecycle rules, and access requirements.

### Mobile clients

- Android’s Firebase-token API client calls history, pending application cancellation, start, completion, and cancellation routes. `WorkerMyJobsScreen` now includes Applications, Upcoming, Ongoing, and Completed sections. Application rows show backend status, job and shop context, date and pay; selecting a row opens a detail dialog. Pending entries can be cancelled. Pagination and load/retry/empty/error states are wired to screen state.
- Android worker assigned jobs retain their actual backend state instead of being forced into “Ongoing”. Assigned jobs can be started by the worker. Shop owners can confirm in-progress completion or cancel an unstarted job from the existing job list, with a confirmation prompt.
- iOS `BackendRepository` now provides paginated worker applications and lifecycle operations. `WorkerMyJobsView` presents the same application history and lifecycle sections, with a detail sheet, pending cancellation, pagination, retry, refresh and loading/empty/error states. Assigned jobs link to detail and can be started from the worker’s existing detail flow.
- iOS shopkeeper job details call the backend to confirm completion or cancel an unstarted job. The local store is updated only from the server response. The completion action explicitly does not process payment.
- Admin status labels remain driven by the real job status. Admin controls now offer only transitions supported by its authorization boundary.

## API and lifecycle matrix

| Operation | Endpoint | Authorized actor | Persisted result |
|---|---|---|---|
| Worker application history | `GET /jobs/applications/me?limit=&offset=` | Worker | Page of own applications, job and shop context |
| Withdraw pending application | `DELETE /jobs/{job_id}/applications/me` | Applying worker | Application status becomes `cancelled` |
| Accept application | Existing `PATCH /jobs/{job_id}/applications/{application_id}` | Owning shop owner | Application accepted, job assigned, other pending applications rejected |
| Start work | `POST /jobs/{job_id}/start` | Assigned worker only | Job becomes `in_progress`, `started_at` set |
| Confirm completion | `POST /jobs/{job_id}/complete` | Owning shop owner only | Job becomes `completed`, `completed_at` set |
| Cancel unstarted job | `PATCH /jobs/{job_id}/status?new_status=cancelled` | Owning shop owner; Admin may cancel open/assigned work with `jobs.manage` | Job becomes `cancelled`, `cancelled_at` set |
| Admin job read | Existing `GET /api/v1/admin/jobs` and detail | Admin with `jobs.read` | Returns current lifecycle status and timestamps |

Allowed mobile business transitions:

```text
open --owner accepts a pending application--> assigned
assigned --assigned worker starts--> in_progress
in_progress --owner confirms completion--> completed
open or assigned --owner cancels--> cancelled
```

Pending application cancellation is independent of job status. Accepted and rejected applications cannot be cancelled.

## Database and migration

The existing `users`, `shops`, `jobs`, and `applications` tables remain the source of truth. The migration adds three nullable columns to `jobs`:

- `started_at TIMESTAMPTZ NULL`
- `completed_at TIMESTAMPTZ NULL`
- `cancelled_at TIMESTAMPTZ NULL`

Migration: [`34d6bcf1a902_add_job_lifecycle_timestamps.py`](Android/Backend/alembic_canonical/versions/34d6bcf1a902_add_job_lifecycle_timestamps.py), chained after `8fa2137c5d20`. Existing records are not rewritten. Downgrade removes only these metadata columns and therefore discards lifecycle timestamp values while preserving jobs/statuses.

The canonical Alembic graph reports `34d6bcf1a902` as its head. The additive migration was exercised using a disposable SQLite schema for upgrade and downgrade. This is a migration operation smoke test, not a substitute for applying it against a disposable PostgreSQL instance. It was **not applied** to production or any configured Supabase database.

## Regression tests and verification

| Check | Command / environment | Result |
|---|---|---|
| Backend suite | `PYTHONPATH="$PWD/Android/Backend" DATABASE_URL=sqlite:// /tmp/errno-backend-verify/bin/pytest -q Android/Backend/tests` | **29 passed, 1 skipped.** Write paths use in-memory SQLite. The optional canonical PostgreSQL test remains skipped without a designated disposable PostgreSQL URL. Existing Pydantic/Starlette deprecation warnings remain. |
| New worker history coverage | `test_mobile_shop_job_application_persists_and_enforces_owner_scope`, `test_worker_application_history_pagination_and_pending_cancellation` | Embedded job/shop/date data, pagination metadata, pending cancellation, duplicate cancellation conflict, and role denial verified. |
| New lifecycle coverage | `test_job_lifecycle_authorization_timestamps_and_idempotency` | Assigned-worker-only start, owner-only completion, timestamps, duplicate start/completion rejection, started-job cancellation rejection, persisted status, and Admin read visibility verified. |
| Android unit tests + debug build | `bash ./gradlew :app:testDebugUnitTest :app:assembleDebug` from `Android/` | **BUILD SUCCESSFUL.** Existing Android Gradle/Kotlin deprecation warnings remain. |
| iOS simulator build | `xcodebuild -quiet -project Errno.xcodeproj -scheme Errno -configuration Debug -destination 'generic/platform=iOS Simulator' -xcconfig Local.xcconfig CODE_SIGNING_ALLOWED=NO build` from `iOS/` | **Exit 0.** The Xcode project has no XCTest target. |
| Admin frontend tests | `npm test -- --run` from `Admin/` | **4 test files, 21 tests passed.** Updated job management test verifies supported cancellation action. |
| Admin production bundle | `npm run build` from `Admin/` | **Build succeeded.** |
| Migration operation smoke | In-memory SQLite schema; migration `upgrade()` and `downgrade()` through Alembic `Operations` | **PASS.** Three columns added then removed as expected. |
| Canonical migration graph | `/tmp/errno-backend-verify/bin/alembic -c alembic_canonical.ini heads` | `34d6bcf1a902 (head)`. |

## Security, compatibility, and limits

- The routes use the existing verified Firebase identity and server-resolved user role/ownership dependency. Client-supplied worker or owner IDs are not used for authorization.
- PostgreSQL `FOR UPDATE` locks serialize competing decisions/transitions on PostgreSQL. SQLite ignores row locks; concurrency semantics were not tested against PostgreSQL.
- Application acceptance behavior is preserved. No payment, earnings, review or rating persistence was added.
- Admin authentication and permission checks were not altered. Admins can still read lifecycle results. Their generic status mutation was constrained so it cannot create an assignment without application acceptance or impersonate start/completion.
- Real Firebase sign-in and mobile live API sessions were not exercised. No production records, Firebase users or permissions were changed.
- The migration has not been tested against a disposable PostgreSQL server; perform that before rollout. Review any legacy noncanonical status values before deployment.
- iOS compiles successfully but has no automated XCTest target. The actual platform UI flows were compile-verified, not automated on device.
- A mobile client deployed before the migration will fail when it reads lifecycle fields from new backend schemas; deploy the additive migration before enabling the updated backend/mobile version.

## Files changed by this phase

**Backend:** `Android/Backend/models/__init__.py`, `Android/Backend/schemas.py`, `Android/Backend/job_lifecycle.py`, `Android/Backend/routers/jobs.py`, `Android/Backend/routers/admin.py`, `Android/Backend/tests/test_mobile_workflows.py`, `Android/Backend/tests/test_admin_api.py`, and the new canonical migration.

**Android:** `Android/app/src/main/java/com/erno/app/data/model/JobModels.kt`, `data/repository/ErrnoMobileApi.kt`, worker screen/ViewModel files, `ShopkeeperViewModel.kt`, and `navigation/NavGraph.kt`.

**iOS:** `Services/Backend/BackendModels.swift`, `Models/Job.swift`, `Services/LocalMarketplaceStore.swift`, worker history/detail/root views, and `Views/Shopkeeper/ShopkeeperJobsView.swift`.

**Admin/API docs/report:** `Admin/src/pages/JobsPage.jsx`, its job page test, `Android/Backend/MOBILE_API.md`, and this report.

The repository already had unrelated uncommitted work before this phase. It was preserved; no commit or push was performed.

## Final status

**Implemented and locally verified:** worker application history and details, pending withdrawal, authorized job start/completion/cancellation, lifecycle timestamps, Admin status read visibility, Android/iOS UI wiring and backend authorization tests.

**Still required before production:** apply and verify the additive migration in a disposable PostgreSQL environment, then run staging PostgreSQL/Firebase end-to-end validation. No production migration or data change was performed.
