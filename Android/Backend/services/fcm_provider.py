"""Official Firebase Admin SDK push transport. No success is synthesized."""
from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from typing import Any

from firebase_admin import messaging
from firebase_admin.exceptions import FirebaseError

from firebase_auth import firebase_app
from services.notification_service import decrypt_token

logger = logging.getLogger("errno.notifications.fcm")


@dataclass(frozen=True)
class PushResult:
    accepted: bool
    provider_message_id: str | None = None
    error_code: str | None = None
    retryable: bool = False
    invalid_token: bool = False


def _enabled() -> bool:
    return os.getenv("NOTIFICATION_PUSH_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def send_to_device(device: Any, payload: dict[str, Any]) -> PushResult:
    if not _enabled():
        return PushResult(False, error_code="PUSH_DISABLED", retryable=True)
    try:
        app = firebase_app()
        token = decrypt_token(device.encrypted_token)
        data = {str(k): str(v) for k, v in (payload.get("data") or {}).items()}
        data.setdefault("notification_id", str(payload.get("notification_id", "")))
        message = messaging.Message(
            token=token,
            notification=messaging.Notification(
                title=str(payload.get("title", "ERRNO"))[:180],
                body=str(payload.get("body", ""))[:500],
            ),
            data=data,
            android=messaging.AndroidConfig(
                priority="high" if payload.get("priority") == "high" else "normal",
                notification=messaging.AndroidNotification(channel_id={
                    "booking": "errno_bookings", "job": "errno_progress", "payment": "errno_payments",
                    "account": "errno_account", "verification": "errno_account", "marketing": "errno_promotions",
                }.get(str(payload.get("category", "booking")), "errno_bookings")),
            ),
            apns=messaging.APNSConfig(headers={"apns-priority": "10" if payload.get("priority") == "high" else "5"}),
        )
        message_id = messaging.send(message, app=app)
        if not message_id:
            return PushResult(False, error_code="EMPTY_PROVIDER_RESPONSE", retryable=True)
        logger.info("fcm_accepted device_id=%s message_id=%s", device.id, message_id)
        return PushResult(True, provider_message_id=message_id)
    except (ValueError, UnicodeError):
        return PushResult(False, error_code="TOKEN_DECRYPTION_FAILED", retryable=False)
    except Exception as exc:
        code = getattr(exc, "code", None) or getattr(exc, "error_code", None) or type(exc).__name__
        code_text = str(code).upper().replace(" ", "_")[:80]
        invalid = any(term in code_text for term in ("UNREGISTERED", "INVALID_ARGUMENT", "SENDER_ID_MISMATCH"))
        retryable = not invalid and (isinstance(exc, FirebaseError) or code_text in {
            "SERVICE_UNAVAILABLE", "INTERNAL", "QUOTA_EXCEEDED", "UNAVAILABLE", "INTERNAL_SERVER_ERROR",
            "PUSH_DISABLED", "DEFAULTCREDENTIALERROR", "GOOGLEAUTHERROR",
        })
        logger.warning("fcm_rejected device_id=%s error_code=%s retryable=%s", device.id, code_text, retryable)
        return PushResult(False, error_code=code_text, retryable=retryable, invalid_token=invalid)
