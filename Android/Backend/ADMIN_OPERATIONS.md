# ERRNO administrator access operations

Admin API access is an explicit database permission keyed by a Firebase UID. A Firebase account, verified email, Google provider, frontend role, or mobile app role does not grant Admin API access by itself.

## Prerequisites

- Apply the reviewed Alembic migration to the intended database before provisioning. Use a disposable database for rehearsal. Production migration and access changes require the normal operator change review and are never run by application startup.
- Configure the backend's Firebase project as `errno-pvt-ltd` and provide Firebase Admin credentials only to the backend process through the deployment's secret manager or `GOOGLE_APPLICATION_CREDENTIALS`.
- In the Firebase console, verify the target UID, Google provider linkage, and verified email. Verify the operator UID independently. The CLI checks both Firebase records before changing permissions.
- Connect the CLI only to the database intended for the change. Do not put credentials in command arguments, shell history, or this document.

## Initial administrator bootstrap

An authorized operator chooses and verifies a specific Firebase UID out of band, records a change ticket as the reason, and runs the CLI from `Android/Backend`. Replace the example placeholders locally; do not commit them.

```sh
python tools/provision_admin.py grant \
  --firebase-uid '<verified-target-uid>' \
  --actor-uid '<verified-operator-uid>' \
  --confirm-target '<verified-target-uid>' \
  --bootstrap \
  --permission dashboard.read \
  --permission users.read \
  --permission users.manage \
  --permission jobs.read \
  --permission jobs.manage \
  --reason '<approved change ticket>'
```

`--bootstrap` is accepted only while the database contains no active administrator. It is not a public API and the command requires Firebase verification of the target and operator. Repeated grants with the same active permissions are idempotent. Later grants or permission changes require an already active operator; omit `--bootstrap`.

## Revocation

An active operator can revoke access. The record is deactivated rather than deleted, and a server-timestamped audit event is written in the same transaction.

```sh
python tools/provision_admin.py revoke \
  --firebase-uid '<target-uid>' \
  --actor-uid '<active-operator-uid>' \
  --confirm-target '<target-uid>' \
  --reason '<approved change ticket>'
```

Revocation causes subsequent admin API requests to receive HTTP 403. It does not delete or disable the person's Firebase account. Record only a ticket or concise operational reason; do not include personal data, credentials, or tokens.

## Audit and migration notes

Successful grants, permission updates, revocations, and admin data mutations write `admin_audit_logs` records transactionally with the corresponding database mutation. Invalid job transition attempts are logged server-side as denied outcomes; no authentication token is logged. Preserve audit records under the organization's retention policy.

The migration adds `admin_permissions` and `admin_audit_logs`. Downgrade removes those two tables and therefore removes their authorization and audit history; export/retain audit records according to policy before any rollback. No migration is applied automatically at startup.
