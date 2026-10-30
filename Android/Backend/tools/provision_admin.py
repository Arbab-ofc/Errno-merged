"""Explicit operator CLI for granting or revoking Admin API access.

Never run this tool against production without the reviewed production runbook.
Firebase user lookups verify the target and operator UIDs. Database authorization
is stored in admin_permissions; possession of an ID token alone grants nothing.
"""
import argparse
import sys

from firebase_admin import auth

from database import SessionLocal
from firebase_auth import firebase_app
from models import AdminAuditLog, AdminPermission

PERMISSIONS = {
    "dashboard.read", "users.read", "users.manage", "jobs.read", "jobs.manage",
}


def apply_admin_change(db, *, action: str, target_uid: str, target_email: str | None,
                      actor_uid: str, reason: str, permissions: list[str], bootstrap: bool) -> bool:
    """Apply an authorized UID grant/revoke and its audit row in one transaction."""
    if action not in {"grant", "revoke"} or not reason.strip():
        raise ValueError("A supported action and non-empty reason are required")
    if any(permission not in PERMISSIONS for permission in permissions):
        raise ValueError("Unknown permission")
    active_admins = db.query(AdminPermission).filter(AdminPermission.active.is_(True)).count()
    if active_admins:
        actor = db.query(AdminPermission).filter_by(firebase_uid=actor_uid, active=True).first()
        if actor is None:
            raise ValueError("Operator UID is not an active administrator")
    elif action != "grant" or not bootstrap:
        raise ValueError("No active administrator; initial grant requires bootstrap")

    record = db.query(AdminPermission).filter_by(firebase_uid=target_uid).with_for_update().first()
    before = None
    if action == "grant":
        normalized = sorted(set(permissions))
        if record is not None and record.active and sorted(record.permissions or []) == normalized:
            return False
        if record is None:
            record = AdminPermission(firebase_uid=target_uid, email=target_email,
                                     permissions=normalized, active=True,
                                     granted_by_uid=actor_uid, reason=reason)
            db.add(record)
            event = "admin.access_granted"
        else:
            before = {"active": record.active, "permissions": record.permissions or []}
            record.email = target_email
            record.permissions = normalized
            record.active = True
            record.granted_by_uid = actor_uid
            record.reason = reason
            event = "admin.access_updated"
        after = {"active": True, "permissions": normalized}
    else:
        if record is None or not record.active:
            return False
        before = {"active": record.active, "permissions": record.permissions or []}
        record.active = False
        record.reason = reason
        record.granted_by_uid = actor_uid
        event = "admin.access_revoked"
        after = {"active": False, "permissions": record.permissions or []}

    db.flush()
    db.add(AdminAuditLog(
        administrator_uid=actor_uid,
        action=event,
        resource_type="admin_permission",
        resource_id=target_uid,
        outcome="success",
        change_metadata={"target_uid": target_uid, "reason": reason, "before": before, "after": after},
    ))
    db.commit()
    return True


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Manage ERRNO Admin API permissions")
    parser.add_argument("action", choices=("grant", "revoke"))
    parser.add_argument("--firebase-uid", required=True, help="Verified target Firebase UID")
    parser.add_argument("--actor-uid", required=True, help="Firebase UID of the operator")
    parser.add_argument("--reason", required=True, help="Ticket or reason, stored in the audit record")
    parser.add_argument("--permission", action="append", default=[], choices=sorted(PERMISSIONS),
                        help="Permission to grant; repeat for multiple permissions")
    parser.add_argument("--bootstrap", action="store_true",
                        help="Explicitly permit initial grant only when no active admin exists")
    parser.add_argument("--confirm-target", required=True,
                        help="Must exactly match --firebase-uid to confirm operator intent")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.confirm_target != args.firebase_uid:
        print("Confirmation UID does not match target.", file=sys.stderr)
        return 2
    if args.action == "grant" and not args.permission:
        print("Grant requires at least one --permission.", file=sys.stderr)
        return 2
    if args.action == "revoke" and args.permission:
        print("Revoke does not accept --permission.", file=sys.stderr)
        return 2

    app = firebase_app()
    try:
        target = auth.get_user(args.firebase_uid, app=app)
        operator = auth.get_user(args.actor_uid, app=app)
    except Exception:
        print("Could not verify target and operator Firebase accounts.", file=sys.stderr)
        return 1
    for record in (target, operator):
        if not record.email_verified or not any(provider.provider_id == "google.com" for provider in record.provider_data):
            print("Target and operator must have verified Google-linked Firebase accounts.", file=sys.stderr)
            return 1

    db = SessionLocal()
    try:
        changed = apply_admin_change(
            db, action=args.action, target_uid=target.uid, target_email=target.email,
            actor_uid=args.actor_uid, reason=args.reason, permissions=args.permission,
            bootstrap=args.bootstrap,
        )
        if not changed:
            print("Administrator access is already in the requested state; no change made.")
            return 0
        print(f"Admin permission {args.action} completed for verified UID {target.uid}.")
        return 0
    except Exception:
        db.rollback()
        print("Permission change failed; transaction rolled back.", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
