# ERRNO Mobile API contract

The Android and iOS applications use the shared FastAPI service. Authenticated calls send the Firebase ID token in `Authorization: Bearer <token>`; the backend verifies the token against project `errno-pvt-ltd` and resolves the persisted `users` row by Firebase UID. The clients do not call Supabase directly.

## Authentication and profile

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| `POST` | `/api/v1/auth/firebase` | Verified Firebase token | Create-or-return the caller's profile; role is not assigned automatically. |
| `GET` | `/api/v1/users/me` | Verified Firebase token | Read the caller's persisted profile. |
| `PATCH` | `/api/v1/users/me` | Verified Firebase token | Update the caller's name and/or perform the one-time `worker` / `shop_owner` onboarding role selection. |
| `POST` | `/api/v1/auth/logout` | Verified Firebase token | Acknowledgement only; clients clear the Firebase session locally. |
| `POST` | `/auth/send-otp`, `/auth/verify-otp` | Public, disabled | Returns `503` until a real OTP provider is configured. |

## Shop owner workflows

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| `GET` | `/shops/me` | Shop owner | Read the current owner's shop. Returns JSON `null` when none exists; performs no writes. |
| `PUT` | `/shops/me` | Shop owner | Create or update shop name, address and category for the authenticated owner. |
| `GET` | `/jobs/mine` | Shop owner | Read jobs belonging to the authenticated owner's shop(s). |
| `POST` | `/jobs` | Shop owner | Create a job associated with the current owner's shop. The server derives ownership from the token. |
| `GET` | `/jobs/applications/owner` | Shop owner | Read applications for owned jobs with only worker ID/name and job ID/title/status. Phone and email are not returned. |
| `GET` | `/jobs/{job_id}/applications` | Owning shop owner | Read application records for one owned job. |
| `PATCH` | `/jobs/{job_id}/applications/{application_id}` | Owning shop owner | Body `{"decision":"accepted"}` or `{"decision":"rejected"}`. Acceptance assigns the worker and rejects other pending applications atomically. |
| `PATCH` | `/jobs/{job_id}/status?new_status=cancelled` | Owning shop owner | Cancel an open or assigned job. Started work cannot be cancelled through this endpoint. |
| `POST` | `/jobs/{job_id}/complete` | Owning shop owner | Confirm completion of an in-progress job and persist `completed_at`. This does not process payment. |

## Worker workflows

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| `GET` | `/jobs?status_filter=open` | Public | Browse open jobs. |
| `GET` | `/jobs/{job_id}` | Public | Read a job detail. |
| `POST` | `/jobs/{job_id}/apply` | Worker | Create an application for an open job. Repeated application is idempotent for the same worker/job pair. |
| `GET` | `/jobs/applications/me?limit=20&offset=0` | Worker | Read paginated application history with job and shop summaries, actual application status, and application date. Returns `{items,total,limit,offset,has_more}`. Statuses are `pending`, `accepted`, `rejected`, and `cancelled`. |
| `DELETE` | `/jobs/{job_id}/applications/me` | Worker | Cancel the caller's pending application. Decided applications cannot be withdrawn. |
| `GET` | `/jobs/worker/mine` | Worker | Read jobs assigned to the caller. |
| `POST` | `/jobs/{job_id}/start` | Assigned worker | Move an assigned job to `in_progress` and persist `started_at`. Other workers and shop owners are forbidden. |

## Lifecycle rules

Canonical job statuses are `open`, `assigned`, `in_progress`, `completed`, and `cancelled`.

```text
open --owner accepts a pending application--> assigned
assigned --the assigned worker starts--> in_progress
in_progress --the owning shop owner confirms--> completed
open or assigned --the shop owner cancels--> cancelled
```

Each operation uses a database row lock where supported and rejects repeated or invalid transitions with HTTP 409. Application acceptance remains atomic: it assigns the worker, sets the job to `assigned`, and rejects the other pending applications. Lifecycle timestamps (`started_at`, `completed_at`, `cancelled_at`) are server-generated. The Admin API may read every resulting status; its management API only permits cancellation of unstarted work, so it cannot impersonate the worker start or owner completion actions.

Application history embeds the associated job title/status/location/pay/schedule and the linked shop name/address/category. Records are newest first. Limits are 1–100; offset is non-negative. Workers see only their own applications.

## Error behavior

Unauthenticated or invalid Firebase tokens return `401`; missing profile and record lookups return `404`; wrong account role or resource ownership returns `403`; conflicts such as applying to a closed job or deciding an already-decided application return `409`; invalid request fields return `422`. The API does not trust client-provided user IDs or phone numbers for authorization.

## Persistence

The contracts use the existing `users`, `shops`, `jobs` and `applications` tables. A new additive canonical migration adds nullable `started_at`, `completed_at`, and `cancelled_at` columns to `jobs`; it does not rewrite existing records. Production migrations and production records were not changed.
