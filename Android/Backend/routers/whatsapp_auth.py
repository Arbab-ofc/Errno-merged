"""WhatsApp OTP authentication and permission-checked gateway operations."""
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from database import get_db
from firebase_auth import require_admin
from models import (AdminAuditLog, BackendAuthSession, Shop, User,
                    WhatsAppGatewayAudit, WhatsAppOTPChallenge)
from schemas import WhatsAppOTPRequest, WhatsAppOTPResendRequest, WhatsAppOTPVerifyRequest

router = APIRouter(prefix="/api/v1", tags=["WhatsApp authentication"])
admin_router = APIRouter(prefix="/api/v1/admin/whatsapp", tags=["WhatsApp gateway administration"])
logger = logging.getLogger(__name__)
PHONE_RE = re.compile(r"^\+[1-9][0-9]{7,14}$")
ROLES = {"WORKER": "worker", "worker": "worker", "SHOPKEEPER": "shop_owner", "shopkeeper": "shop_owner", "shop_owner": "shop_owner"}


def _settings():
    return {
        "otp_length": int(os.getenv("WHATSAPP_OTP_LENGTH", "6")),
        "ttl": int(os.getenv("WHATSAPP_OTP_TTL_SECONDS", "300")),
        "resend": int(os.getenv("WHATSAPP_OTP_RESEND_SECONDS", "30")),
        "attempts": int(os.getenv("WHATSAPP_OTP_MAX_ATTEMPTS", "5")),
        "phone_limit": int(os.getenv("WHATSAPP_OTP_PHONE_LIMIT_PER_HOUR", "5")),
        "ip_limit": int(os.getenv("WHATSAPP_OTP_IP_LIMIT_PER_HOUR", "20")),
    }


def _canonical_role(role: str) -> str:
    return ROLES.get(role, "")


def _hash_secret() -> bytes:
    secret = os.getenv("WHATSAPP_OTP_HASH_SECRET", "")
    if len(secret) < 32:
        raise HTTPException(status_code=503, detail={"code": "OTP_NOT_CONFIGURED", "message": "WhatsApp authentication is not configured."})
    return secret.encode()


def _otp_digest(request_id: str, phone: str, role: str, otp: str) -> str:
    message = f"{request_id}:{phone}:{role}:{otp}".encode()
    return hmac.new(_hash_secret(), message, hashlib.sha256).hexdigest()


def _ip_digest(ip: str | None) -> str | None:
    if not ip:
        return None
    return hmac.new(_hash_secret(), ip.encode(), hashlib.sha256).hexdigest()


def _gateway(method: str, path: str, body: dict | None = None) -> dict:
    base = os.getenv("WHATSAPP_GATEWAY_INTERNAL_URL", "").rstrip("/")
    secret = os.getenv("WHATSAPP_GATEWAY_INTERNAL_AUTH_SECRET", "")
    if os.getenv("WHATSAPP_GATEWAY_ENABLED", "false").lower() != "true" or not base or len(secret) < 32:
        raise HTTPException(status_code=503, detail={"code": "WHATSAPP_GATEWAY_UNAVAILABLE", "message": "WhatsApp delivery is temporarily unavailable."})
    payload = b"" if method == "GET" else json.dumps(body or {}, separators=(",", ":")).encode()
    timestamp = str(int(time.time()))
    nonce = secrets.token_urlsafe(18)
    signature = hmac.new(secret.encode(), b"\n".join([timestamp.encode(), method.encode(), path.encode(), payload]), hashlib.sha256).hexdigest()
    request = urllib.request.Request(base + path, data=payload if method != "GET" else None, method=method, headers={
        "Content-Type": "application/json", "X-ERRNO-Timestamp": timestamp,
        "X-ERRNO-Signature": signature, "X-ERRNO-Nonce": nonce,
    })
    try:
        timeout = max(5, min(60, int(os.getenv("WHATSAPP_GATEWAY_TIMEOUT_SECONDS", "35"))))
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode() or "{}")
            if response.status >= 300:
                raise ValueError("gateway rejected request")
            return data
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
        logger.warning("whatsapp_gateway_request_failed method=%s path=%s", method, path)
        raise HTTPException(status_code=503, detail={"code": "WHATSAPP_GATEWAY_UNAVAILABLE", "message": "WhatsApp delivery is temporarily unavailable."}) from None


def _audit(db: Session, event: str, outcome: str, phone: str | None = None, message_id: str | None = None, details=None):
    db.add(WhatsAppGatewayAudit(event_type=event, outcome=outcome, message_id=message_id,
                                destination_suffix=(phone or "")[-4:] or None, details=details or {}))


def _rate_check(db: Session, phone: str, ip_digest: str | None, now: datetime):
    config = _settings()
    since = now - timedelta(hours=1)
    by_phone = db.query(WhatsAppOTPChallenge).filter(WhatsAppOTPChallenge.phone_number == phone,
        WhatsAppOTPChallenge.created_at >= since).count()
    by_ip = db.query(WhatsAppOTPChallenge).filter(WhatsAppOTPChallenge.request_ip_hash == ip_digest,
        WhatsAppOTPChallenge.created_at >= since).count() if ip_digest else 0
    if by_phone >= config["phone_limit"] or by_ip >= config["ip_limit"]:
        _audit(db, "otp_rate_limited", "rejected", phone)
        db.commit()
        raise HTTPException(status_code=429, detail={"code": "OTP_RATE_LIMITED", "message": "Please wait before requesting another code."})


def _issue(body: WhatsAppOTPRequest, request: Request, db: Session, old_id: str | None = None):
    if not PHONE_RE.fullmatch(body.phone):
        raise HTTPException(status_code=422, detail="Phone must be in E.164 format")
    role = _canonical_role(body.role)
    if not role:
        raise HTTPException(status_code=422, detail="Unsupported account role")
    config = _settings()
    if config["otp_length"] != 6 or config["ttl"] < 60 or config["resend"] < 1 or config["attempts"] < 1:
        raise HTTPException(status_code=503, detail={"code": "OTP_POLICY_INVALID", "message": "WhatsApp authentication policy is invalid."})
    now = datetime.now(timezone.utc)
    ip_hash = _ip_digest(request.client.host if request.client else None)
    if old_id:
        previous = db.query(WhatsAppOTPChallenge).filter(WhatsAppOTPChallenge.id == old_id).with_for_update().first()
        if previous is None or previous.phone_number != body.phone or previous.role != role:
            raise HTTPException(status_code=404, detail="OTP request not found")
    else:
        previous = db.query(WhatsAppOTPChallenge).filter(WhatsAppOTPChallenge.phone_number == body.phone,
            WhatsAppOTPChallenge.consumed_at.is_(None)).order_by(WhatsAppOTPChallenge.created_at.desc()).with_for_update().first()
    latest_for_phone = db.query(WhatsAppOTPChallenge).filter(WhatsAppOTPChallenge.phone_number == body.phone,
        WhatsAppOTPChallenge.consumed_at.is_(None)).order_by(WhatsAppOTPChallenge.created_at.desc()).with_for_update().first()
    if latest_for_phone is not None:
        previous = latest_for_phone
    if previous is not None:
        resend_after = previous.resend_after if previous.resend_after.tzinfo else previous.resend_after.replace(tzinfo=timezone.utc)
        if resend_after > now:
            _audit(db, "otp_rate_limited", "rejected", body.phone)
            db.commit()
            raise HTTPException(status_code=429, detail={"code": "RESEND_COOLDOWN", "message": "Please wait before requesting another code."})
    _rate_check(db, body.phone, ip_hash, now)
    db.query(WhatsAppOTPChallenge).filter(WhatsAppOTPChallenge.phone_number == body.phone,
        WhatsAppOTPChallenge.consumed_at.is_(None)).update(
            {WhatsAppOTPChallenge.consumed_at: now}, synchronize_session=False)
    request_id = secrets.token_urlsafe(24)
    otp = f"{secrets.randbelow(1_000_000):06d}"
    challenge = WhatsAppOTPChallenge(id=request_id, phone_number=body.phone, role=role,
        otp_digest=_otp_digest(request_id, body.phone, role, otp), expires_at=now + timedelta(seconds=config["ttl"]),
        resend_after=now + timedelta(seconds=config["resend"]), request_ip_hash=ip_hash,
        delivery_status="pending")
    db.add(challenge)
    db.flush()
    try:
        result = _gateway("POST", "/internal/whatsapp/send", {
            "requestId": request_id, "phone": body.phone, "messageType": "otp", "otp": otp,
            "expiresInSeconds": config["ttl"],
        })
    except HTTPException:
        challenge.delivery_status = "failed"
        _audit(db, "otp_send", "failed", body.phone)
        db.commit()
        raise
    challenge.delivery_status = "accepted" if result.get("accepted") else "failed"
    challenge.gateway_message_id = result.get("messageId")
    _audit(db, "otp_send", challenge.delivery_status, body.phone, challenge.gateway_message_id)
    if challenge.delivery_status != "accepted":
        db.commit()
        raise HTTPException(status_code=503, detail={"code": "WHATSAPP_DELIVERY_FAILED", "message": "WhatsApp could not accept the verification message."})
    db.commit()
    return {"success": True, "requestId": request_id, "expiresInSeconds": config["ttl"],
            "resendAfterSeconds": config["resend"], "deliveryStatus": "accepted"}


@router.post("/auth/whatsapp/send-otp")
def send_otp(body: WhatsAppOTPRequest, request: Request, db: Session = Depends(get_db)):
    return _issue(body, request, db)


@router.post("/auth/whatsapp/resend-otp")
def resend_otp(body: WhatsAppOTPResendRequest, request: Request, db: Session = Depends(get_db)):
    return _issue(body, request, db, body.requestId)


@router.post("/auth/whatsapp/verify-otp")
def verify_otp(body: WhatsAppOTPVerifyRequest, db: Session = Depends(get_db)):
    role = _canonical_role(body.role)
    challenge = db.query(WhatsAppOTPChallenge).filter(WhatsAppOTPChallenge.id == body.requestId).with_for_update().first()
    if challenge is None or challenge.phone_number != body.phone or challenge.role != role:
        _audit(db, "otp_verify", "failed", body.phone)
        db.commit()
        raise HTTPException(status_code=400, detail={"code": "OTP_INVALID", "message": "The code is invalid or expired."})
    now = datetime.now(timezone.utc)
    expiry = challenge.expires_at if challenge.expires_at.tzinfo else challenge.expires_at.replace(tzinfo=timezone.utc)
    if challenge.consumed_at is not None or expiry <= now or challenge.delivery_status != "accepted":
        _audit(db, "otp_verify", "failed", body.phone)
        db.commit()
        raise HTTPException(status_code=400, detail={"code": "OTP_INVALID", "message": "The code is invalid or expired."})
    config = _settings()
    challenge.attempt_count += 1
    if challenge.attempt_count > config["attempts"]:
        challenge.consumed_at = now
        db.commit()
        raise HTTPException(status_code=429, detail={"code": "OTP_ATTEMPTS_EXCEEDED", "message": "Too many attempts. Request a new code."})
    supplied = _otp_digest(body.requestId, body.phone, role, body.otp)
    if not hmac.compare_digest(supplied, challenge.otp_digest):
        _audit(db, "otp_verify", "failed", body.phone)
        db.commit()
        raise HTTPException(status_code=400, detail={"code": "OTP_INVALID", "message": "The code is invalid or expired."})
    challenge.consumed_at = now
    user = db.query(User).filter(User.phone_number == body.phone).with_for_update().first()
    if user is not None and user.role not in (None, role):
        db.commit()
        raise HTTPException(status_code=400, detail={"code": "OTP_INVALID", "message": "The code is invalid or expired."})
    if user is None:
        full_name = body.fullName.strip() if body.fullName else None
        user = User(phone_number=body.phone, full_name=full_name or None, role=role, is_active=True, is_phone_verified=True)
        db.add(user)
        db.flush()
        if role == "shop_owner":
            db.add(Shop(owner_id=user.id, shop_name="My Store"))
    else:
        if not user.is_active:
            db.commit()
            raise HTTPException(status_code=400, detail={"code": "OTP_INVALID", "message": "The code is invalid or expired."})
        user.is_phone_verified = True
        if user.role is None:
            user.role = role
        if user.full_name is None and body.fullName:
            user.full_name = body.fullName.strip() or None
    token = "errno_" + secrets.token_urlsafe(40)
    lifetime = int(os.getenv("WHATSAPP_SESSION_TTL_SECONDS", str(60 * 60 * 24 * 30)))
    if not 300 <= lifetime <= 60 * 60 * 24 * 365:
        db.rollback()
        raise HTTPException(status_code=503, detail="Session policy is invalid")
    max_sessions = int(os.getenv("WHATSAPP_SESSION_MAX_ACTIVE", "5"))
    if not 1 <= max_sessions <= 50:
        db.rollback()
        raise HTTPException(status_code=503, detail="Session limit policy is invalid")
    active_sessions = db.query(BackendAuthSession).filter(
        BackendAuthSession.user_id == user.id, BackendAuthSession.revoked_at.is_(None),
        BackendAuthSession.expires_at > now,
    ).order_by(BackendAuthSession.created_at.desc(), BackendAuthSession.id.desc()).with_for_update().all()
    for old_session in active_sessions[max_sessions - 1:]:
        old_session.revoked_at = now
    session = BackendAuthSession(user_id=user.id, token_digest=hashlib.sha256(token.encode()).hexdigest(),
                                expires_at=now + timedelta(seconds=lifetime))
    db.add(session)
    _audit(db, "otp_verify", "success", body.phone)
    db.commit()
    db.refresh(user)
    return {"success": True, "accessToken": token, "expiresInSeconds": lifetime,
            "user": {"id": user.id, "name": user.full_name, "phone_number": user.phone_number, "role": user.role,
                     "onboarding_completed": user.role in ("worker", "shop_owner", "shopkeeper")}}


@router.post("/auth/whatsapp/logout")
def logout(request: Request, deviceId: str | None = None, db: Session = Depends(get_db)):
    token = request.headers.get("authorization", "").removeprefix("Bearer ")
    if not token.startswith("errno_"):
        raise HTTPException(status_code=401, detail="Backend session required")
    digest = hashlib.sha256(token.encode()).hexdigest()
    session = db.query(BackendAuthSession).filter(BackendAuthSession.token_digest == digest,
        BackendAuthSession.revoked_at.is_(None)).with_for_update().first()
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid session")
    session.revoked_at = datetime.now(timezone.utc)
    if deviceId:
        from models import NotificationDevice
        db.query(NotificationDevice).filter_by(user_id=session.user_id, device_identifier=deviceId, active=True).update(
            {NotificationDevice.active: False, NotificationDevice.invalidated_at: datetime.now(timezone.utc)}, synchronize_session=False)
    db.commit()
    return {"success": True}


def _admin_call(admin, permission: str, action: str, method: str, path: str, body=None, db: Session | None = None):
    if permission not in (admin.permissions or []):
        raise HTTPException(status_code=403, detail="Administrator permission required")
    result = _gateway(method, path, body)
    if db is not None:
        db.add(AdminAuditLog(administrator_uid=admin.firebase_uid, action=action, resource_type="whatsapp_gateway",
            resource_id=None, outcome="success", change_metadata={"result": result.get("status", result.get("accepted"))}))
        db.commit()
    return result


@admin_router.get("/status")
def gateway_status(admin=Depends(require_admin("whatsapp.read"))):
    if "whatsapp.read" not in (admin.permissions or []):
        raise HTTPException(status_code=403, detail="Administrator permission required")
    return _gateway("GET", "/internal/whatsapp/status")


@admin_router.get("/qr")
def gateway_qr(response: Response, admin=Depends(require_admin("whatsapp.connect"))):
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return _admin_call(admin, "whatsapp.connect", "whatsapp.qr_read", "GET", "/internal/whatsapp/qr")


@admin_router.post("/connect")
def gateway_connect(admin=Depends(require_admin("whatsapp.connect")), db: Session = Depends(get_db)):
    return _admin_call(admin, "whatsapp.connect", "whatsapp.connect", "POST", "/internal/whatsapp/connect", {"regenerate": True}, db)


@admin_router.post("/disconnect")
def gateway_disconnect(admin=Depends(require_admin("whatsapp.manage")), db: Session = Depends(get_db)):
    return _admin_call(admin, "whatsapp.manage", "whatsapp.disconnect", "POST", "/internal/whatsapp/disconnect", {}, db)


@admin_router.post("/logout")
def gateway_logout(admin=Depends(require_admin("whatsapp.manage")), db: Session = Depends(get_db)):
    return _admin_call(admin, "whatsapp.manage", "whatsapp.logout", "POST", "/internal/whatsapp/logout", {}, db)


@admin_router.get("/monitoring")
def gateway_monitoring(admin=Depends(require_admin("whatsapp.monitor")), db: Session = Depends(get_db)):
    if "whatsapp.monitor" not in (admin.permissions or []):
        raise HTTPException(status_code=403, detail="Administrator permission required")
    events = db.query(WhatsAppGatewayAudit).order_by(WhatsAppGatewayAudit.created_at.desc()).limit(100).all()
    counts = {}
    for event in db.query(WhatsAppGatewayAudit.event_type, WhatsAppGatewayAudit.outcome).all():
        key = f"{event.event_type}_{event.outcome}"
        counts[key] = counts.get(key, 0) + 1
    return {"counts": counts, "events": [{"event_type": row.event_type, "outcome": row.outcome,
        "message_id": row.message_id, "destination_suffix": row.destination_suffix,
        "created_at": row.created_at} for row in events]}
