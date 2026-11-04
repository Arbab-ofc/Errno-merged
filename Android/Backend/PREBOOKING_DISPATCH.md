# Four-hour pre-booking dispatch

## Lifecycle and timing

`CURRENT` bookings continue through the existing job workflow. `PRE_BOOKING` rows are saved with an orthogonal dispatch lifecycle and remain `jobs.status = open`; worker-facing job listings and detail/application endpoints hide them until dispatch succeeds.

The backend stores the scheduled instant and dispatch instant as timezone-aware UTC timestamps:

```text
dispatch_at = scheduled_at - 4 hours
```

The mobile apps present India-facing times in `Asia/Kolkata`. A pre-booking more than four hours ahead remains `SCHEDULED`; one created at or inside the four-hour window is dispatched synchronously as part of booking creation. Past pre-booking times are rejected.

Dispatch states are `SCHEDULED`, `DISPATCHING`, `DISPATCHED`, `NO_ELIGIBLE_WORKERS`, `FAILED_RETRYABLE`, `FAILED`, and `CANCELLED`. `DISPATCHED` means worker invitations were transactionally queued in the existing notification outbox; FCM delivery remains independently retried by the notification worker. Workers receive an invitation and then use the existing job review/apply and shopkeeper accept/reject flow. The backend does not fabricate worker applications.

Cancellation changes a pending pre-booking to `CANCELLED`. Rescheduling requires a fresh active pricing quote, increments `prebooking_schedule_version`, recalculates dispatch time, and clears old-generation lease/attempt data. The dispatcher rechecks version, job state, and schedule while holding the job row lock. Once dispatch completes, the existing job cancellation rules apply and rescheduling is rejected.

## Migration

Use the canonical Alembic configuration and the normal deployment database URL:

```sh
cd Android/Backend
alembic -c alembic_canonical.ini upgrade head
```

The new migration is `fb4a6c90d112`, following `eb72a31c4890`. It adds lifecycle columns, checks, and a due-dispatch index; legacy jobs default to `CURRENT` and keep their existing status and assignment data.

## Runtime processes

The API process does not own an in-memory timer. Run one or more supervised dispatcher processes next to the API, all pointed at the same PostgreSQL database:

```sh
cd Android/Backend
python -m services.prebooking_dispatcher
```

Required configuration is the same database configuration used by the API (`DATABASE_URL` and, when TLS is enabled, the existing PostgreSQL certificate settings). Optional dispatcher settings:

| Variable | Default | Purpose |
|---|---:|---|
| `PREBOOKING_DISPATCH_POLL_SECONDS` | `1` | Idle database polling interval |
| `PREBOOKING_DISPATCH_LEASE_SECONDS` | `120` | Claim lease before another worker may recover a crashed claim |
| `PREBOOKING_NO_WORKER_RETRY_SECONDS` | `300` | Retry interval when no eligible workers match |
| `PREBOOKING_WORKER_RADIUS_KM` | `5` | Maximum distance for jobs with coordinates |
| `PREBOOKING_LOCATION_MAX_AGE_SECONDS` | `300` | Required freshness for worker coordinates when the job has coordinates |

Use the deployment's process supervisor (for example, a dedicated systemd unit or container command) with automatic restart enabled. Keep the existing notification outbox worker running separately with `python -m services.notification_dispatcher`; it performs FCM delivery and retries. API/mobile startup alone does not start either worker.

`deploy/errno-prebooking-dispatcher.service.example` is a systemd unit template. Adjust its service user, virtualenv, application path, and environment-file path for the deployment, install it as `/etc/systemd/system/errno-prebooking-dispatcher.service`, then run `systemctl daemon-reload`, `systemctl enable --now errno-prebooking-dispatcher`, and inspect it with `systemctl status` / `journalctl -u errno-prebooking-dispatcher`. Do not put secrets directly in the unit file.

## Durability, retries, and operations

The dispatcher selects due rows with PostgreSQL `FOR UPDATE SKIP LOCKED`, commits a time-limited claim, then re-locks the booking to validate its current version and state. Multiple instances can run concurrently. If a process stops after claiming work, an expired lease becomes reclaimable. If notification queueing fails, a retryable state with exponential backoff is recorded. Invitations use a deterministic job/version/worker deduplication key, so retries do not create duplicate inbox/outbox events. FCM retries are handled by the existing outbox worker.

When no workers qualify, the booking is `NO_ELIGIBLE_WORKERS`, remains hidden from workers, and is retried until its scheduled start. Eligibility is recalculated for each attempt from active worker accounts, unexpired foreground available presence, preferred skills, and (when job coordinates exist) a fresh worker location inside the configured radius. Manual-address bookings do not invent coordinates and use availability/skill eligibility without a spatial filter.

Useful operational checks:

```sql
SELECT id, scheduled_at, dispatch_at, prebooking_dispatch_status,
       prebooking_dispatch_attempts, prebooking_dispatch_worker_count,
       prebooking_dispatch_failure_code, prebooking_next_attempt_at
FROM jobs
WHERE booking_type = 'PRE_BOOKING'
ORDER BY dispatch_at;
```

Watch `errno.prebooking.dispatcher` logs for `prebooking_dispatch`, `prebooking_dispatch_failed`, and `prebooking_dispatch_loop_error`; inspect `notification_outbox` separately for FCM delivery status. Alert on old `DISPATCHING` leases, repeated retryable failures, and `NO_ELIGIBLE_WORKERS` near the service start.

## Development verification examples

- **Scheduled:** start at 10:00 India time, created at 01:00 → `dispatch_at` 06:00, `SCHEDULED`, no worker notifications before 06:00.
- **Late creation:** start at 10:00, created at 07:00 → dispatch immediately if eligible workers exist.
- **Cancelled:** cancel before 06:00 → `CANCELLED`; dispatcher skips it.
- **Rescheduled:** move the 10:00 booking to 14:00 → version increases, dispatch moves to 10:00, old due generation is ignored.
- **Dispatched:** eligible workers receive an idempotent invitation at dispatch; normal apply/accept/reject remains unchanged.
- **No match/failure:** no eligible workers produces `NO_ELIGIBLE_WORKERS` and a retry time; a transient database/queue error produces `FAILED_RETRYABLE`.

For staging, apply the migration, start the API, dispatcher, and existing notification worker under supervision, create a disposable pre-booking more than four hours ahead, and inspect the job and notification/outbox rows before and after its dispatch instant. Use a test clock or direct dispatcher invocation for automated tests; do not alter production rows to simulate time.
