"""Consent-aware worker/staff identity verification and manual-review APIs."""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

import kyc_service
import kyc_storage
from database import get_db
from firebase_auth import authenticated_user, require_admin, require_role
from models import (AdminPermission, FinancialAuditEvent, KYCConsentRecord, KYCAuditEvent,
                    KYCManualReview, KYCVerificationProfile, KYCVerificationSession,
                    KYCVerifiedDocument, User)
from services.notification_service import queue_notification, queue_admin_notifications

router = APIRouter(prefix="/api/v1", tags=["Identity verification"])
admin_router = APIRouter(prefix="/api/v1/admin/kyc", tags=["Admin KYC"])

STATUS_SET = {"NOT_STARTED", "CONSENT_PENDING", "VERIFICATION_PENDING", "VERIFIED", "FAILED",
              "EXPIRED", "MANUAL_REVIEW", "REJECTED", "REVERIFICATION_REQUIRED"}


class StartSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requestedDocumentTypes: list[str] = Field(min_length=1, max_length=6)
    consentVersion: str = Field(min_length=1, max_length=80)
    consentGiven: bool


class CancelSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(default="USER_CANCELLED", min_length=1, max_length=80)


class MockCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    testOnlyMockToken: str = Field(min_length=24, max_length=160)


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(pattern="^(APPROVE|REJECT|RESUBMIT)$")
    reasonCode: str = Field(min_length=2, max_length=80)
    note: str = Field(min_length=5, max_length=1000)


def _now():
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _audit(db: Session, profile: KYCVerificationProfile | None, actor_type: str, actor_id: str | None,
           event_type: str, old: str | None = None, new: str | None = None, details: dict | None = None):
    db.add(KYCAuditEvent(profile_id=profile.id if profile else None, actor_type=actor_type, actor_id=actor_id,
        event_type=event_type, from_status=old, to_status=new, details=details or {}))


def _profile_for_worker(db: Session, user: User, create=False) -> KYCVerificationProfile | None:
    profile = db.query(KYCVerificationProfile).filter_by(user_id=user.id).with_for_update().first()
    if profile is None and create:
        profile = KYCVerificationProfile(user_id=user.id, subject_role="worker", status="NOT_STARTED")
        db.add(profile)
        db.flush()
    return profile


def _profile_for_staff(db: Session, firebase_uid: str, create=False) -> KYCVerificationProfile | None:
    profile = db.query(KYCVerificationProfile).filter_by(staff_firebase_uid=firebase_uid).with_for_update().first()
    if profile is None and create:
        profile = KYCVerificationProfile(staff_firebase_uid=firebase_uid, subject_role="staff", status="NOT_STARTED")
        db.add(profile)
        db.flush()
    return profile


def _cancel_open_sessions(db: Session, profile: KYCVerificationProfile):
    rows = db.query(KYCVerificationSession).filter(KYCVerificationSession.profile_id == profile.id,
        KYCVerificationSession.status.in_(["CONSENT_PENDING", "VERIFICATION_PENDING"])).with_for_update().all()
    for row in rows:
        row.status = "CANCELLED"
        row.consumed_at = _now()


def _start_session(db: Session, profile: KYCVerificationProfile, requested: list[str], version: str,
                   consent_given: bool, subject_user_id: str | None, staff_uid: str | None):
    if not kyc_service.feature_enabled("DIGILOCKER_ENABLED"):
        raise HTTPException(503, detail={"code": "PROVIDER_NOT_CONFIGURED", "message": "DigiLocker is unavailable. Manual document review may be requested."})
    if not consent_given:
        raise HTTPException(422, detail={"code": "CONSENT_REQUIRED", "message": "Explicit consent is required before starting verification."})
    if version != kyc_service.consent_version():
        raise HTTPException(409, detail={"code": "CONSENT_VERSION_STALE", "message": "Review the current consent notice before continuing."})
    document_types = kyc_service.ensure_document_types(requested)
    provider = kyc_service.ensure_provider_enabled()
    existing = db.query(KYCVerificationSession).filter(KYCVerificationSession.profile_id == profile.id,
        KYCVerificationSession.status.in_(["CONSENT_PENDING", "VERIFICATION_PENDING"]),
        KYCVerificationSession.expires_at > _now()).first()
    if existing:
        raise HTTPException(409, detail={"code": "ACTIVE_SESSION_EXISTS", "message": "A verification session is already active."})
    raw_state = secrets.token_urlsafe(32)
    raw_nonce = secrets.token_urlsafe(32)
    provider_session = provider.create_authorization(raw_state, raw_nonce, document_types)
    # State/nonce and mock completion credentials are never stored in plaintext.
    row = KYCVerificationSession(profile_id=profile.id, user_id=subject_user_id,
        staff_firebase_uid=staff_uid, provider=provider_session.provider,
        status="VERIFICATION_PENDING", state_hash=kyc_service.digest(raw_state, keyed=True),
        nonce_hash=kyc_service.digest(raw_nonce, keyed=True),
        mock_callback_token_hash=(kyc_service.digest(provider_session.test_completion_token) if provider_session.test_completion_token else None),
        requested_document_types=document_types, consent_version=version, expires_at=kyc_service.expiry())
    db.add(row)
    db.flush()
    queue_admin_notifications(db, permission="kyc.review", event_type="kyc_manual_review_pending",
        title="Worker verification review", body="A worker identity submission is awaiting manual review.",
        data={"route":"kyc","kyc_profile_id":profile.id}, event_id=f"kyc:{profile.id}:manual-review:{row.id}")
    db.flush()
    db.add(KYCConsentRecord(profile_id=profile.id, session_id=row.id, subject_user_id=subject_user_id,
        subject_staff_uid=staff_uid, purpose="ERRNO worker/staff identity verification for onboarding and eligibility review",
        document_types=document_types, consent_version=version))
    old = profile.status
    profile.status = "VERIFICATION_PENDING"
    profile.provider = provider_session.provider
    profile.verification_method = None
    profile.document_types = document_types
    profile.user_message_code = None
    profile.consent_withdrawn_at = None
    _audit(db, profile, "USER" if subject_user_id else "STAFF", subject_user_id or staff_uid,
        "verification.session_started", old, profile.status, {"provider": provider_session.provider, "document_types": document_types, "consent_version": version})
    db.commit()
    response = {"sessionId": row.id, "status": row.status, "authorizationUrl": provider_session.authorization_url,
        "expiresInSeconds": kyc_service.ttl_seconds(), "provider": row.provider, "providerReady": bool(provider_session.authorization_url)}
    if provider_session.test_completion_token:
        # This property is emitted only by the deterministic local/test adapter.
        response["testOnlyMockToken"] = provider_session.test_completion_token
    return response


def _status(db: Session, profile: KYCVerificationProfile | None, *, staff=False):
    if profile is None:
        return {"status": "NOT_STARTED", "verificationMethod": None, "provider": None,
            "requiredDocumentTypes": [], "verifiedDocumentTypes": [], "lastVerifiedAt": None,
            "reverificationRequired": False, "pendingAdminReview": False, "failureReasonCode": None,
            "nextAction": "START_VERIFICATION", "availableDocumentTypes": sorted(kyc_service.allowed_document_types()),
            "manualReviewEnabled": kyc_service.feature_enabled("KYC_MANUAL_REVIEW_ENABLED"),
            "digilockerEnabled": kyc_service.feature_enabled("DIGILOCKER_ENABLED"),
            "consentVersion": kyc_service.consent_version()}
    status = profile.status
    if profile.status == "VERIFIED" and profile.reverification_required_at and _as_utc(profile.reverification_required_at) <= _now():
        status = "REVERIFICATION_REQUIRED"
    pending = db.query(KYCManualReview).filter_by(profile_id=profile.id).filter(
        KYCManualReview.status.in_(["PENDING_SCAN", "PENDING_REVIEW", "RESUBMISSION_REQUESTED"])).count() > 0
    next_action = {"NOT_STARTED": "START_VERIFICATION", "CONSENT_PENDING": "REVIEW_CONSENT",
        "VERIFICATION_PENDING": "CONTINUE_VERIFICATION", "VERIFIED": "NONE", "FAILED": "RETRY_OR_MANUAL_REVIEW",
        "EXPIRED": "RETRY", "MANUAL_REVIEW": "WAIT_FOR_REVIEW", "REJECTED": "REVIEW_REASON_OR_RESUBMIT",
        "REVERIFICATION_REQUIRED": "REVERIFY"}.get(status, "CONTACT_SUPPORT")
    return {"status": status, "verificationMethod": profile.verification_method, "provider": profile.provider,
        "requiredDocumentTypes": profile.document_types or [], "verifiedDocumentTypes": profile.verified_document_types or [],
        "lastVerifiedAt": profile.verified_at.isoformat() if profile.verified_at else None,
        "reverificationRequired": status == "REVERIFICATION_REQUIRED", "pendingAdminReview": pending,
        "failureReasonCode": profile.user_message_code, "nextAction": next_action,
        "availableDocumentTypes": sorted(kyc_service.allowed_document_types()),
        "manualReviewEnabled": kyc_service.feature_enabled("KYC_MANUAL_REVIEW_ENABLED"),
        "digilockerEnabled": kyc_service.feature_enabled("DIGILOCKER_ENABLED"),
        "consentVersion": kyc_service.consent_version()}


@router.get("/worker/verification-status")
def worker_verification_status(user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "worker")
    return _status(db, _profile_for_worker(db, user))


@router.post("/worker/verification-sessions")
def create_worker_verification_session(body: StartSessionRequest, user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "worker")
    profile = _profile_for_worker(db, user, create=True)
    if profile.status == "VERIFIED" and not (profile.reverification_required_at and profile.reverification_required_at <= _now()):
        raise HTTPException(409, detail={"code": "ALREADY_VERIFIED", "message": "Identity verification is already complete."})
    return _start_session(db, profile, body.requestedDocumentTypes, body.consentVersion, body.consentGiven, user.id, None)


@router.get("/worker/verification-sessions/{session_id}")
def worker_verification_session_status(session_id: str, user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "worker")
    row = db.query(KYCVerificationSession).filter_by(id=session_id, user_id=user.id).first()
    if row is None:
        raise HTTPException(404, detail="Verification session not found")
    if _as_utc(row.expires_at) <= _now() and row.status in {"CONSENT_PENDING", "VERIFICATION_PENDING"}:
        row.status = "EXPIRED"
        row.consumed_at = _now()
        profile = db.query(KYCVerificationProfile).filter_by(id=row.profile_id).with_for_update().first()
        old = profile.status
        profile.status = "EXPIRED"
        _audit(db, profile, "SYSTEM", None, "verification.session_expired", old, profile.status)
        db.commit()
    return {"sessionId": row.id, "status": row.status, "provider": row.provider,
        "expiresAt": row.expires_at.isoformat(), "failureReasonCode": row.failure_code}


@router.post("/worker/verification-sessions/{session_id}/cancel")
def cancel_worker_verification_session(session_id: str, body: CancelSessionRequest,
                                       user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "worker")
    row = db.query(KYCVerificationSession).filter_by(id=session_id, user_id=user.id).with_for_update().first()
    if row is None:
        raise HTTPException(404, detail="Verification session not found")
    if row.status not in {"CONSENT_PENDING", "VERIFICATION_PENDING"}:
        raise HTTPException(409, detail="Verification session cannot be cancelled in its current state")
    profile = db.query(KYCVerificationProfile).filter_by(id=row.profile_id).with_for_update().one()
    old = profile.status
    row.status = "CANCELLED"
    row.consumed_at = _now()
    profile.status = "NOT_STARTED"
    _audit(db, profile, "USER", user.id, "verification.session_cancelled", old, profile.status, {"reason": body.reason})
    db.commit()
    return {"sessionId": row.id, "status": row.status}


@router.post("/worker/verification-sessions/{session_id}/mock-complete")
def complete_mock_session(session_id: str, body: MockCompletionRequest,
                          user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "worker")
    provider = kyc_service.ensure_provider_enabled()
    if provider.name != "mock" or kyc_service.environment() not in {"test", "development", "local"}:
        raise HTTPException(404, detail="Not found")
    row = db.query(KYCVerificationSession).filter_by(id=session_id, user_id=user.id).with_for_update().first()
    if row is None or row.provider != "mock":
        raise HTTPException(404, detail="Verification session not found")
    if row.status != "VERIFICATION_PENDING" or row.consumed_at or _as_utc(row.expires_at) <= _now():
        raise HTTPException(409, detail={"code": "SESSION_NOT_ACTIVE", "message": "This test session is expired or already used."})
    if not row.mock_callback_token_hash or not hmac.compare_digest(kyc_service.digest(body.testOnlyMockToken), row.mock_callback_token_hash):
        raise HTTPException(400, detail={"code": "MOCK_PROOF_INVALID", "message": "The test provider proof is invalid."})
    profile = db.query(KYCVerificationProfile).filter_by(id=row.profile_id).with_for_update().one()
    old = profile.status
    row.status = "VERIFIED"
    row.consumed_at = _now()
    row.mock_callback_token_hash = None
    profile.status = "VERIFIED"
    profile.verification_method = "MOCK_PROVIDER_TEST"
    profile.provider = "mock"
    profile.verified_document_types = list(row.requested_document_types or [])
    profile.verified_at = _now()
    profile.user_message_code = None
    for doc_type in row.requested_document_types or []:
        db.add(KYCVerifiedDocument(profile_id=profile.id, session_id=row.id, document_type=doc_type,
            issuer_id="mock-test-only", proof_status="MOCK_SIMULATED", metadata_json={"test_only": True}))
    _audit(db, profile, "MOCK_PROVIDER", "test-adapter", "verification.mock_completed", old, profile.status,
        {"document_types": profile.verified_document_types})
    db.commit()
    return {"sessionId": row.id, "status": row.status, "verificationMethod": profile.verification_method, "testOnly": True}


@router.get("/verification/digilocker/callback")
async def digilocker_callback_placeholder():
    # Deliberately accepts no provider-specific query semantics until official
    # requester documentation authorizes the exact callback protocol.
    raise HTTPException(503, detail={"code": "PROVIDER_SPEC_REQUIRED", "message": "DigiLocker callback processing awaits ERRNO's approved requester API specification."})


@router.post("/verification/digilocker/callback")
async def digilocker_callback_placeholder_post():
    raise HTTPException(503, detail={"code": "PROVIDER_SPEC_REQUIRED", "message": "DigiLocker callback processing awaits ERRNO's approved requester API specification."})


@router.post("/worker/verification/withdraw-consent")
def withdraw_worker_consent(user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "worker")
    profile = _profile_for_worker(db, user)
    if profile is None:
        return {"status": "NOT_STARTED", "consentWithdrawn": True}
    now = _now()
    old = profile.status
    consents = db.query(KYCConsentRecord).filter_by(profile_id=profile.id, withdrawn_at=None).with_for_update().all()
    for consent in consents:
        consent.withdrawn_at = now
    _cancel_open_sessions(db, profile)
    profile.consent_withdrawn_at = now
    profile.status = "NOT_STARTED"
    profile.verification_method = None
    profile.verified_document_types = []
    profile.verified_at = None
    db.query(KYCVerifiedDocument).filter_by(profile_id=profile.id).delete(synchronize_session=False)
    pending_reviews = db.query(KYCManualReview).filter_by(profile_id=profile.id).filter(
        KYCManualReview.status.in_(["PENDING_SCAN", "PENDING_REVIEW", "RESUBMISSION_REQUESTED"])).with_for_update().all()
    for review in pending_reviews:
        kyc_storage.delete(review.encrypted_storage_key)
        review.status = "DELETED"
        review.encrypted_storage_key = f"deleted-{secrets.token_urlsafe(16)}.enc"
        review.sha256 = ""
        review.reviewer_note = None
    # Preserve only the fact that consent was withdrawn; metadata is removed.
    _audit(db, profile, "USER", user.id, "consent.withdrawn", old, profile.status, {"records_removed": True})
    db.commit()
    return {"status": profile.status, "consentWithdrawn": True}


@router.post("/worker/verification/manual-reviews", status_code=201)
async def submit_manual_review(document_type: str = Form(...), consent_version: str = Form(...),
                               consent_given: bool = Form(...), file: UploadFile = File(...),
                               user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "worker")
    if not kyc_service.feature_enabled("KYC_MANUAL_REVIEW_ENABLED"):
        raise HTTPException(503, detail={"code": "MANUAL_REVIEW_UNAVAILABLE", "message": "Manual verification is not configured."})
    if not consent_given:
        raise HTTPException(422, detail={"code": "CONSENT_REQUIRED", "message": "Explicit consent is required to submit a document."})
    if consent_version != kyc_service.consent_version():
        raise HTTPException(409, detail={"code": "CONSENT_VERSION_STALE", "message": "Review the current privacy notice before uploading."})
    doc_types = kyc_service.ensure_document_types([document_type])
    payload = await file.read(kyc_storage.MAX_DOCUMENT_BYTES + 1)
    kyc_storage.validate_file(payload, file.content_type or "")
    scan_status = kyc_storage.scan(payload)
    if scan_status == "INFECTED":
        raise HTTPException(422, detail={"code": "DOCUMENT_REJECTED_BY_SCAN", "message": "The document did not pass the malware scan."})
    profile = _profile_for_worker(db, user, create=True)
    key = secrets.token_urlsafe(24) + ".enc"
    checksum = kyc_storage.store(payload, key)
    status = "PENDING_REVIEW" if scan_status == "CLEAN" else "PENDING_SCAN"
    old = profile.status
    row = KYCManualReview(profile_id=profile.id, user_id=user.id, document_type=doc_types[0], encrypted_storage_key=key,
        content_type=file.content_type, size_bytes=len(payload), sha256=checksum, scan_status=scan_status,
        status=status, retain_until=(_now() + timedelta(days=kyc_service.retention_days()) if kyc_service.retention_days() > 0 else None))
    db.add(row)
    profile.status = "MANUAL_REVIEW"
    profile.verification_method = "MANUAL_DOCUMENT_REVIEW"
    profile.provider = None
    profile.document_types = doc_types
    _cancel_open_sessions(db, profile)
    db.add(KYCConsentRecord(profile_id=profile.id, subject_user_id=user.id,
        purpose="Manual ERRNO identity document review", document_types=doc_types, consent_version=consent_version))
    _audit(db, profile, "USER", user.id, "manual_review.submitted", old, profile.status,
        {"document_type": doc_types[0], "scan_status": scan_status, "size_bytes": len(payload)})
    db.commit()
    return {"manualReviewId": row.id, "status": row.status, "scanStatus": row.scan_status,
        "verificationMethod": "MANUAL_DOCUMENT_REVIEW", "message": "No official DigiLocker verification is implied."}


@router.get("/worker/verification/manual-reviews")
def worker_manual_reviews(user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "worker")
    return [{"id": row.id, "documentType": row.document_type, "status": row.status,
        "reasonCode": row.review_reason_code, "submittedAt": row.created_at.isoformat(),
        "reviewedAt": row.reviewed_at.isoformat() if row.reviewed_at else None}
        for row in db.query(KYCManualReview).filter_by(user_id=user.id).order_by(KYCManualReview.created_at.desc()).limit(50).all()]


@admin_router.get("/overview")
def admin_kyc_overview(admin=Depends(require_admin("kyc.read")), db: Session = Depends(get_db)):
    counts = {status: db.query(KYCVerificationProfile).filter_by(status=status).count() for status in sorted(STATUS_SET)}
    counts["PENDING_SCAN"] = db.query(KYCManualReview).filter_by(status="PENDING_SCAN").count()
    counts["MANUAL_REVIEW_QUEUE"] = db.query(KYCManualReview).filter_by(status="PENDING_REVIEW").count()
    counts["TOTAL_WORKERS"] = db.query(User).filter_by(role="worker").count()
    counts["TOTAL_STAFF"] = db.query(KYCVerificationProfile).filter_by(subject_role="staff").count()
    counts["VERIFIED_WORKERS"] = db.query(KYCVerificationProfile).join(User, User.id == KYCVerificationProfile.user_id).filter(
        User.role == "worker", KYCVerificationProfile.status == "VERIFIED").count()
    return counts


@admin_router.get("/verifications")
def admin_kyc_list(limit: int = 50, offset: int = 0, status: str | None = None, q: str | None = None,
                   admin=Depends(require_admin("kyc.read")), db: Session = Depends(get_db)):
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(422, detail="Invalid pagination")
    query = db.query(KYCVerificationProfile, User).outerjoin(User, User.id == KYCVerificationProfile.user_id)
    if status:
        query = query.filter(KYCVerificationProfile.status == status)
    if q:
        escaped = q[:100].replace("%", "\\%").replace("_", "\\_")
        query = query.filter(or_(User.full_name.ilike(f"%{escaped}%"), User.email.ilike(f"%{escaped}%"),
            KYCVerificationProfile.staff_firebase_uid.ilike(f"%{escaped}%")))
    total = query.count()
    rows = query.order_by(KYCVerificationProfile.updated_at.desc()).offset(offset).limit(limit).all()
    items = []
    for profile, subject in rows:
        manual = db.query(KYCManualReview).filter_by(profile_id=profile.id).order_by(KYCManualReview.created_at.desc()).first()
        items.append({"id": profile.id, "userId": subject.id if subject else None,
            "identity": subject.full_name if subject else "Staff identity",
            "role": profile.subject_role, "staffUid": profile.staff_firebase_uid if profile.subject_role == "staff" else None,
            "status": profile.status, "verificationMethod": profile.verification_method, "provider": profile.provider,
            "documentTypes": profile.document_types or [], "verifiedDocumentTypes": profile.verified_document_types or [],
            "verifiedAt": profile.verified_at.isoformat() if profile.verified_at else None,
            "pendingReview": bool(manual and manual.status in {"PENDING_REVIEW", "PENDING_SCAN"}),
            "lastActionAt": profile.updated_at.isoformat()})
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@admin_router.get("/verifications/{profile_id}")
def admin_kyc_detail(profile_id: str, admin=Depends(require_admin("kyc.read")), db: Session = Depends(get_db)):
    profile = db.query(KYCVerificationProfile).filter_by(id=profile_id).first()
    if profile is None:
        raise HTTPException(404, detail="Verification record not found")
    subject = db.query(User).filter_by(id=profile.user_id).first() if profile.user_id else None
    sessions = db.query(KYCVerificationSession).filter_by(profile_id=profile.id).order_by(KYCVerificationSession.created_at.desc()).limit(50).all()
    consents = db.query(KYCConsentRecord).filter_by(profile_id=profile.id).order_by(KYCConsentRecord.created_at.desc()).limit(50).all()
    docs = db.query(KYCVerifiedDocument).filter_by(profile_id=profile.id).order_by(KYCVerifiedDocument.verified_at.desc()).all()
    manual = db.query(KYCManualReview).filter_by(profile_id=profile.id).order_by(KYCManualReview.created_at.desc()).all()
    return {"id": profile.id, "user": {"id": subject.id, "name": subject.full_name, "email": subject.email} if subject else None,
        "staffUid": profile.staff_firebase_uid, "role": profile.subject_role, "status": profile.status,
        "verificationMethod": profile.verification_method, "provider": profile.provider,
        "documents": [{"documentType": d.document_type, "issuerId": d.issuer_id, "proofStatus": d.proof_status,
            "maskedIdentifier": d.masked_identifier, "metadata": d.metadata_json, "verifiedAt": d.verified_at.isoformat()} for d in docs],
        "sessions": [{"id": s.id, "provider": s.provider, "status": s.status, "requestedDocumentTypes": s.requested_document_types,
            "expiresAt": s.expires_at.isoformat(), "createdAt": s.created_at.isoformat()} for s in sessions],
        "consents": [{"purpose": c.purpose, "documentTypes": c.document_types, "version": c.consent_version,
            "grantedAt": c.granted_at.isoformat(), "withdrawnAt": c.withdrawn_at.isoformat() if c.withdrawn_at else None} for c in consents],
        "manualReviews": [{"id": x.id, "documentType": x.document_type, "status": x.status, "scanStatus": x.scan_status,
            "sizeBytes": x.size_bytes, "reasonCode": x.review_reason_code, "reviewerUid": x.reviewer_uid,
            "reviewerNote": x.reviewer_note, "createdAt": x.created_at.isoformat(),
            "reviewedAt": x.reviewed_at.isoformat() if x.reviewed_at else None} for x in manual]}


@admin_router.get("/manual-reviews/{review_id}/document")
def admin_manual_document(review_id: str, admin=Depends(require_admin("kyc.review")), db: Session = Depends(get_db)):
    row = db.query(KYCManualReview).filter_by(id=review_id).first()
    if row is None:
        raise HTTPException(404, detail="Manual review not found")
    if row.scan_status != "CLEAN" or row.status not in {"PENDING_REVIEW", "RESUBMISSION_REQUESTED"}:
        raise HTTPException(409, detail={"code": "DOCUMENT_QUARANTINED", "message": "Document access is blocked until malware scanning succeeds."})
    data = kyc_storage.read(row.encrypted_storage_key)
    _audit(db, db.query(KYCVerificationProfile).filter_by(id=row.profile_id).first(), "ADMIN", admin.firebase_uid,
        "manual_document.viewed", details={"manual_review_id": row.id})
    db.commit()
    return Response(content=data, media_type=row.content_type,
        headers={"Content-Disposition": "attachment; filename=kyc-review-document", "Cache-Control": "no-store, private"})


@admin_router.post("/verifications/{profile_id}/review")
def review_manual_kyc(profile_id: str, body: ReviewRequest, admin=Depends(require_admin("kyc.review")), db: Session = Depends(get_db)):
    profile = db.query(KYCVerificationProfile).filter_by(id=profile_id).with_for_update().first()
    if profile is None:
        raise HTTPException(404, detail="Verification record not found")
    if profile.staff_firebase_uid and profile.staff_firebase_uid == admin.firebase_uid:
        raise HTTPException(403, detail="Administrators cannot review their own staff verification")
    review = db.query(KYCManualReview).filter_by(profile_id=profile.id).filter(
        KYCManualReview.status.in_(["PENDING_REVIEW", "RESUBMISSION_REQUESTED"])).order_by(KYCManualReview.created_at.desc()).with_for_update().first()
    if review is None:
        raise HTTPException(409, detail="No scannable manual document is awaiting review")
    if review.scan_status != "CLEAN":
        raise HTTPException(409, detail={"code": "DOCUMENT_QUARANTINED", "message": "Document must pass malware scanning before review."})
    old = profile.status
    now = _now()
    review.reviewer_uid = admin.firebase_uid
    review.reviewer_note = body.note.strip()
    review.review_reason_code = body.reasonCode
    review.reviewed_at = now
    if body.action == "APPROVE":
        review.status = "APPROVED"
        profile.status = "VERIFIED"
        profile.verification_method = "MANUAL_DOCUMENT_REVIEW"
        profile.verified_at = now
        profile.verified_document_types = sorted(set((profile.verified_document_types or []) + [review.document_type]))
        db.add(KYCVerifiedDocument(profile_id=profile.id, document_type=review.document_type,
            issuer_id=None, proof_status="MANUAL_REVIEWED_NOT_PROVIDER_VERIFIED",
            metadata_json={"manual_review_id": review.id, "reason_code": body.reasonCode}, verified_at=now,
            retain_until=review.retain_until))
    elif body.action == "REJECT":
        review.status = "REJECTED"
        profile.status = "REJECTED"
        profile.user_message_code = body.reasonCode
        profile.verification_method = "MANUAL_DOCUMENT_REVIEW"
    else:
        review.status = "RESUBMISSION_REQUESTED"
        review.resubmission_requested = True
        profile.status = "MANUAL_REVIEW"
        profile.user_message_code = body.reasonCode
    profile.provider = None
    _audit(db, profile, "ADMIN", admin.firebase_uid, f"manual_review.{body.action.lower()}", old, profile.status,
        {"manual_review_id": review.id, "reason_code": body.reasonCode, "note": body.note.strip()})
    db.add(FinancialAuditEvent(actor_id=admin.firebase_uid, event_type=f"kyc.manual_review.{body.action.lower()}",
        resource_type="kyc_profile", resource_id=profile.id, details={"reason_code": body.reasonCode, "method": "MANUAL_DOCUMENT_REVIEW"}))
    subject = db.query(User).filter_by(id=profile.user_id).first() if profile.user_id else None
    if subject and old != profile.status:
        queue_notification(db, recipient=subject, event_type="kyc_status_changed", category="verification",
            title="Verification status updated", body="Your ERRNO identity verification status has changed. Open the app for details.",
            data={"route":"kyc","kyc_profile_id":profile.id}, event_id=f"kyc:{profile.id}:{profile.status}:{review.id}")
    db.commit()
    return {"profileId": profile.id, "status": profile.status, "verificationMethod": profile.verification_method,
        "manualReviewId": review.id, "reviewStatus": review.status}


@admin_router.get("/audit")
def admin_kyc_audit(limit: int = 50, offset: int = 0, admin=Depends(require_admin("kyc.audit")), db: Session = Depends(get_db)):
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(422, detail="Invalid pagination")
    rows = db.query(KYCAuditEvent).order_by(KYCAuditEvent.created_at.desc()).offset(offset).limit(limit).all()
    return {"items": [{"id": row.id, "profileId": row.profile_id, "actorType": row.actor_type,
        "actorId": row.actor_id, "eventType": row.event_type, "fromStatus": row.from_status,
        "toStatus": row.to_status, "details": row.details, "createdAt": row.created_at.isoformat()} for row in rows],
        "limit": limit, "offset": offset}


@admin_router.get("/me/verification-status")
def staff_verification_status(admin=Depends(require_admin("kyc.read")), db: Session = Depends(get_db)):
    row = _profile_for_staff(db, admin.firebase_uid)
    return _status(db, row, staff=True)


@admin_router.post("/me/verification-sessions")
def create_staff_verification_session(body: StartSessionRequest, admin=Depends(require_admin("kyc.manage")), db: Session = Depends(get_db)):
    profile = _profile_for_staff(db, admin.firebase_uid, create=True)
    return _start_session(db, profile, body.requestedDocumentTypes, body.consentVersion, body.consentGiven, None, admin.firebase_uid)


@admin_router.post("/me/manual-reviews", status_code=201)
async def submit_staff_manual_review(document_type: str = Form(...), consent_version: str = Form(...),
                                     consent_given: bool = Form(...), file: UploadFile = File(...),
                                     admin=Depends(require_admin("kyc.manage")), db: Session = Depends(get_db)):
    if not kyc_service.feature_enabled("KYC_MANUAL_REVIEW_ENABLED"):
        raise HTTPException(503, detail={"code": "MANUAL_REVIEW_UNAVAILABLE", "message": "Manual verification is not configured."})
    if not consent_given or consent_version != kyc_service.consent_version():
        raise HTTPException(422, detail={"code": "CONSENT_REQUIRED", "message": "Current explicit consent is required."})
    doc_type = kyc_service.ensure_document_types([document_type])[0]
    payload = await file.read(kyc_storage.MAX_DOCUMENT_BYTES + 1)
    kyc_storage.validate_file(payload, file.content_type or "")
    scan_status = kyc_storage.scan(payload)
    if scan_status == "INFECTED":
        raise HTTPException(422, detail={"code": "DOCUMENT_REJECTED_BY_SCAN", "message": "The document did not pass the malware scan."})
    profile = _profile_for_staff(db, admin.firebase_uid, create=True)
    key = secrets.token_urlsafe(24) + ".enc"
    checksum = kyc_storage.store(payload, key)
    review = KYCManualReview(profile_id=profile.id, user_id=None, document_type=doc_type,
        encrypted_storage_key=key, content_type=file.content_type, size_bytes=len(payload), sha256=checksum,
        scan_status=scan_status, status="PENDING_REVIEW" if scan_status == "CLEAN" else "PENDING_SCAN")
    old = profile.status
    profile.status = "MANUAL_REVIEW"; profile.verification_method = "MANUAL_DOCUMENT_REVIEW"
    profile.document_types = [doc_type]; profile.provider = None
    db.add(review)
    db.add(KYCConsentRecord(profile_id=profile.id, subject_staff_uid=admin.firebase_uid,
        purpose="ERRNO staff identity verification", document_types=[doc_type], consent_version=consent_version))
    _audit(db, profile, "STAFF", admin.firebase_uid, "manual_review.submitted", old, profile.status,
        {"document_type": doc_type, "scan_status": scan_status, "size_bytes": len(payload)})
    db.commit()
    return {"manualReviewId": review.id, "status": review.status, "verificationMethod": "MANUAL_DOCUMENT_REVIEW"}


@admin_router.post("/me/withdraw-consent")
def withdraw_staff_consent(admin=Depends(require_admin("kyc.manage")), db: Session = Depends(get_db)):
    profile = _profile_for_staff(db, admin.firebase_uid)
    if profile is None:
        return {"status": "NOT_STARTED", "consentWithdrawn": True}
    now = _now(); old = profile.status
    for consent in db.query(KYCConsentRecord).filter_by(profile_id=profile.id, withdrawn_at=None).with_for_update().all():
        consent.withdrawn_at = now
    _cancel_open_sessions(db, profile)
    for review in db.query(KYCManualReview).filter_by(profile_id=profile.id).filter(
        KYCManualReview.status.in_(["PENDING_SCAN", "PENDING_REVIEW", "RESUBMISSION_REQUESTED"])).with_for_update().all():
        kyc_storage.delete(review.encrypted_storage_key)
        review.status = "DELETED"; review.encrypted_storage_key = f"deleted-{secrets.token_urlsafe(16)}.enc"
        review.sha256 = ""; review.reviewer_note = None
    db.query(KYCVerifiedDocument).filter_by(profile_id=profile.id).delete(synchronize_session=False)
    profile.status = "NOT_STARTED"; profile.verification_method = None; profile.verified_document_types = []
    profile.verified_at = None; profile.consent_withdrawn_at = now
    _audit(db, profile, "STAFF", admin.firebase_uid, "consent.withdrawn", old, profile.status, {"records_removed": True})
    db.commit()
    return {"status": profile.status, "consentWithdrawn": True}


@admin_router.post("/retention/cleanup")
def cleanup_kyc_retention(admin=Depends(require_admin("kyc.manage")), db: Session = Depends(get_db)):
    now = _now()
    rows = db.query(KYCManualReview).filter(KYCManualReview.retain_until.is_not(None),
        KYCManualReview.retain_until <= now, KYCManualReview.status != "DELETED").with_for_update().limit(500).all()
    removed = 0
    for row in rows:
        kyc_storage.delete(row.encrypted_storage_key)
        row.status = "DELETED"
        row.encrypted_storage_key = f"deleted-{secrets.token_urlsafe(16)}.enc"
        row.sha256 = ""
        row.reviewer_note = None
        removed += 1
        _audit(db, db.query(KYCVerificationProfile).filter_by(id=row.profile_id).first(), "ADMIN", admin.firebase_uid,
            "retention.document_deleted", details={"manual_review_id": row.id})
    db.commit()
    return {"deleted": removed}
