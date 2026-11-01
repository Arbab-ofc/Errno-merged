"""Razorpay collections and append-only worker finance operations."""
import hashlib
import hmac
import json
import logging
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from firebase_auth import authenticated_user, require_admin, require_role
from models import (AdminAuditLog, CashCollection, FinancialAuditEvent, FinancialRefund, Job,
                    CompanyPaymentConfiguration, PaymentTransaction, PaymentWebhookEvent, PricingQuote, Shop, User,
                    PlatformFinanceLedgerEntry, WalletLedgerEntry, WorkerPayoutMethod, WorkerWithdrawal)

router = APIRouter(prefix="/api/v1", tags=["Payments and wallet"])
admin_router = APIRouter(prefix="/api/v1/admin", tags=["Admin finance"])
logger = logging.getLogger(__name__)


class WithdrawalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amountPaise: int = Field(gt=0, le=100_000_000)
    payoutMethodId: str = Field(min_length=8, max_length=160)
    idempotencyKey: str = Field(min_length=16, max_length=160)


class CashConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidenceReference: str | None = Field(default=None, max_length=500)


class RefundRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    paymentId: str = Field(min_length=1, max_length=64)
    amountPaise: int | None = Field(default=None, gt=0)
    reason: str = Field(min_length=5, max_length=1000)
    idempotencyKey: str = Field(min_length=16, max_length=160)


class CashResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outcome: str = Field(pattern="^(RECONCILED|DISPUTED)$")
    reason: str = Field(min_length=5, max_length=1000)
    errnoCommissionReceivedPaise: int | None = Field(default=None, ge=0)


class PayoutMethodCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    providerReference: str = Field(min_length=8, max_length=160)


class CompanyQRUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    qrAssetUrl: str = Field(min_length=10, max_length=2048)
    verified: bool
    reason: str = Field(min_length=5, max_length=1000)


class VerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bookingId: str = Field(min_length=1, max_length=64)
    razorpayOrderId: str = Field(min_length=1, max_length=100)
    razorpayPaymentId: str = Field(min_length=1, max_length=100)
    razorpaySignature: str = Field(min_length=32, max_length=128)


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def _credentials():
    key, secret, environment = _env("RAZORPAY_KEY_ID"), _env("RAZORPAY_KEY_SECRET"), _env("RAZORPAY_ENVIRONMENT")
    if not key or not secret or environment not in {"test", "live"}:
        raise HTTPException(503, detail={"code": "PAYMENTS_NOT_CONFIGURED", "message": "Online payment is temporarily unavailable."})
    if environment == "live" and key.startswith("rzp_test_"):
        raise HTTPException(503, detail={"code": "PAYMENTS_CONFIGURATION_INVALID", "message": "Live payment configuration is invalid."})
    return key, secret


def _api(path: str, method="GET", payload=None):
    key, secret = _credentials()
    timeout = max(3, min(30, int(_env("RAZORPAY_API_TIMEOUT_SECONDS") or "10")))
    data = json.dumps(payload, separators=(",", ":")).encode() if payload is not None else None
    req = urllib.request.Request("https://api.razorpay.com/v1" + path, data=data, method=method,
        headers={"Authorization": "Basic " + __import__("base64").b64encode(f"{key}:{secret}".encode()).decode(),
                 "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode() or "{}")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("razorpay_api_failure method=%s endpoint=%s reason=%s", method, path.split("?")[0], type(exc).__name__)
        raise HTTPException(502, detail={"code": "PAYMENT_PROVIDER_UNAVAILABLE", "message": "Payment provider is unavailable. Check payment status before retrying."}) from None


def _payment_snapshot(db: Session, job: Job):
    quote = db.query(PricingQuote).filter(PricingQuote.job_id == job.id).with_for_update().first()
    if quote is None:
        raise HTTPException(409, detail={"code": "FINANCIAL_SNAPSHOT_MISSING", "message": "This booking has no authoritative pricing snapshot and cannot be paid online."})
    try:
        amount = int((Decimal(quote.final_service_charge) * 100).to_integral_exact())
        commission = int((Decimal(quote.commission_amount) * 100).to_integral_exact())
        worker = int((Decimal(quote.worker_payout_amount) * 100).to_integral_exact())
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(409, detail={"code": "FINANCIAL_SNAPSHOT_INVALID", "message": "This booking has an invalid financial snapshot."}) from None
    if amount <= 0 or commission < 0 or worker < 0 or commission + worker != amount:
        raise HTTPException(409, detail={"code": "FINANCIAL_SNAPSHOT_INVALID", "message": "This booking has an invalid financial snapshot."})
    if quote.final_service_charge <= 0 or not job.assigned_worker_id:
        raise HTTPException(409, detail={"code": "BOOKING_NOT_PAYABLE", "message": "This booking is not eligible for payment."})
    return quote, amount, commission, worker


def _owned_job(db: Session, job_id: str, user: User, lock=False):
    query = db.query(Job).filter(Job.id == job_id)
    if lock:
        query = query.with_for_update()
    job = query.first()
    if job is None:
        raise HTTPException(404, detail="Booking not found")
    shop = db.query(Shop).filter(Shop.id == job.shop_id, Shop.owner_id == user.id).first()
    if shop is None:
        raise HTTPException(403, detail="You do not own this booking")
    return job


def _record_paid(db: Session, txn: PaymentTransaction, payment_id: str, paid_at=None):
    if txn.status == "PAID":
        if txn.payment_id != payment_id:
            raise HTTPException(409, detail="Booking has already been paid using another payment")
        return False
    if txn.status in {"REFUNDED", "DISPUTED"}:
        raise HTTPException(409, detail="Payment cannot be finalized in its current state")
    txn.payment_id = payment_id
    txn.status = "PAID"
    txn.paid_at = paid_at or datetime.now(timezone.utc)
    db.add(WalletLedgerEntry(worker_id=txn.worker_id, booking_id=txn.booking_id, payment_id=txn.id,
        category="EARNING_AVAILABLE", amount_paise=txn.worker_earning_paise,
        idempotency_key=f"earning:{txn.id}"))
    if txn.commission_paise:
        db.add(PlatformFinanceLedgerEntry(payment_id=txn.id, entry_type="COMMISSION_CREDIT",
            amount_paise=txn.commission_paise, idempotency_key=f"commission:{txn.id}"))
    db.add(FinancialAuditEvent(event_type="payment.paid", resource_type="payment", resource_id=txn.id,
        details={"amount_paise": txn.amount_paise, "payment_id": payment_id}))
    return True


@router.post("/bookings/{booking_id}/payment-order")
def create_payment_order(booking_id: str, user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "shop_owner", "shopkeeper")
    job = _owned_job(db, booking_id, user, lock=True)
    # The existing completion route is shopkeeper-owned and sets completed_at.
    if job.status != "completed" or job.completed_at is None:
        raise HTTPException(409, detail={"code": "COMPLETION_NOT_VERIFIED", "message": "Payment is available after the shopkeeper verifies job completion."})
    quote, amount, commission, worker_amount = _payment_snapshot(db, job)
    txn = db.query(PaymentTransaction).filter(PaymentTransaction.booking_id == job.id).with_for_update().first()
    if txn and txn.status == "PAID":
        raise HTTPException(409, detail={"code": "ALREADY_PAID", "message": "This booking is already paid."})
    if txn and txn.status == "CASH_PENDING":
        raise HTTPException(409, detail={"code": "CASH_PAYMENT_PENDING", "message": "Cash collection is in progress for this booking."})
    if txn and txn.order_id:
        key_id, _ = _credentials()
        return {"bookingId": job.id, "razorpayOrderId": txn.order_id, "amountPaise": txn.amount_paise,
                "currency": txn.currency, "keyId": key_id, "paymentStatus": txn.status}
    if txn is None:
        txn = PaymentTransaction(booking_id=job.id, shopkeeper_id=user.id, worker_id=job.assigned_worker_id,
            amount_paise=amount, commission_paise=commission, worker_earning_paise=worker_amount,
            idempotency_key=f"booking-payment:{job.id}")
        db.add(txn)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            txn = db.query(PaymentTransaction).filter(PaymentTransaction.booking_id == job.id).first()
            if txn is None:
                raise HTTPException(409, detail="Payment order is already being created") from None
            if txn.order_id:
                key_id, _ = _credentials()
                return {"bookingId": job.id, "razorpayOrderId": txn.order_id, "amountPaise": txn.amount_paise,
                        "currency": txn.currency, "keyId": key_id, "paymentStatus": txn.status}
            raise HTTPException(409, detail="Payment order is already being created") from None
    if txn.amount_paise != amount or txn.commission_paise != commission or txn.worker_earning_paise != worker_amount:
        raise HTTPException(409, detail="Stored payment snapshot does not match booking quote")
    result = _api("/orders", "POST", {"amount": amount, "currency": "INR", "receipt": ("errno-" + job.id)[:40],
        "notes": {"booking_id": job.id, "pricing_version": str(quote.pricing_rule_version)}})
    txn.order_id = result.get("id")
    txn.status = "ORDER_CREATED"
    txn.provider_payload = {"order_status": result.get("status")}
    db.add(FinancialAuditEvent(actor_id=user.id, event_type="payment.order_created", resource_type="payment", resource_id=txn.id,
        details={"booking_id": job.id, "amount_paise": amount}))
    db.commit()
    key_id, _ = _credentials()
    return {"bookingId": job.id, "razorpayOrderId": txn.order_id, "amountPaise": amount,
            "currency": "INR", "keyId": key_id, "paymentStatus": txn.status}


@router.post("/payments/verify")
def verify_payment(body: VerifyRequest, user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    job = _owned_job(db, body.bookingId, user, lock=True)
    if job.status != "completed" or job.completed_at is None:
        raise HTTPException(409, detail="Payment is not due until completion is verified")
    txn = db.query(PaymentTransaction).filter(PaymentTransaction.booking_id == job.id).with_for_update().first()
    if txn is None or txn.order_id != body.razorpayOrderId:
        raise HTTPException(404, detail="Payment order not found")
    _, secret = _credentials()
    message = f"{txn.order_id}|{body.razorpayPaymentId}".encode()
    expected = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, body.razorpaySignature):
        raise HTTPException(400, detail="Invalid payment signature")
    provider = _api(f"/payments/{urllib.parse.quote(body.razorpayPaymentId)}")
    if provider.get("order_id") != txn.order_id or int(provider.get("amount", -1)) != txn.amount_paise or provider.get("currency") != txn.currency:
        raise HTTPException(409, detail="Provider payment does not match the booking order")
    if provider.get("status") != "captured":
        txn.status = "PAYMENT_PROCESSING" if provider.get("status") in {"created", "authorized"} else "PAYMENT_FAILED"
        db.commit()
        return {"paymentId": txn.id, "bookingId": job.id, "status": txn.status}
    if db.query(CashCollection).filter_by(booking_id=job.id).first():
        txn.status = "DISPUTED"
        db.add(FinancialAuditEvent(actor_id=user.id, event_type="payment.cash_conflict", resource_type="payment", resource_id=txn.id,
            details={"provider_payment_id": body.razorpayPaymentId}))
        db.commit()
        raise HTTPException(409, detail="Cash collection is also recorded; payment requires reconciliation")
    _record_paid(db, txn, body.razorpayPaymentId)
    db.commit()
    return {"paymentId": txn.id, "bookingId": job.id, "status": txn.status}


@router.get("/payments/{payment_id}")
def get_payment(payment_id: str, user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    txn = db.query(PaymentTransaction).filter(PaymentTransaction.id == payment_id).first()
    if txn is None:
        raise HTTPException(404, detail="Payment not found")
    if user.id not in {txn.shopkeeper_id, txn.worker_id}:
        raise HTTPException(403, detail="Payment is not available to this user")
    return {"paymentId": txn.id, "bookingId": txn.booking_id, "amountPaise": txn.amount_paise,
            "currency": txn.currency, "status": txn.status, "paidAt": txn.paid_at,
            "workerEarningPaise": txn.worker_earning_paise if user.id == txn.worker_id else None}


@router.get("/bookings/{booking_id}/payment-status")
def booking_payment_status(booking_id: str, user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter_by(id=booking_id).first()
    if job is None:
        raise HTTPException(404, detail="Booking not found")
    if user.id not in {job.assigned_worker_id, (db.query(Shop.owner_id).filter(Shop.id == job.shop_id).scalar())}:
        raise HTTPException(403, detail="Payment is not available to this user")
    txn = db.query(PaymentTransaction).filter_by(booking_id=booking_id).first()
    cash = db.query(CashCollection).filter_by(booking_id=booking_id).first()
    if txn is None:
        return {"bookingId": booking_id, "status": "PAYMENT_PENDING", "amountPaise": None, "paymentId": None, "cashCollectionId": None}
    return {"bookingId": booking_id, "paymentId": txn.id, "providerPaymentId": txn.payment_id,
            "status": txn.status, "amountPaise": txn.amount_paise, "paidAt": txn.paid_at,
            "cashCollectionId": cash.id if cash else None,
            "cashShopkeeperConfirmed": bool(cash and cash.shopkeeper_confirmed_at),
            "cashWorkerConfirmed": bool(cash and cash.worker_confirmed_at),
            "cashReconciliationStatus": cash.reconciliation_status if cash else None}


@router.get("/worker/cash-collections")
def worker_cash_collections(user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "worker")
    return [{"id": row.id, "bookingId": row.booking_id, "amountPaise": row.amount_paise,
             "shopkeeperConfirmed": row.shopkeeper_confirmed_at is not None,
             "workerConfirmed": row.worker_confirmed_at is not None, "status": row.reconciliation_status}
        for row in db.query(CashCollection).filter_by(worker_id=user.id).order_by(CashCollection.created_at.desc()).limit(100).all()]


@router.get("/worker/company-upi-qr")
def worker_company_upi_qr(user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "worker")
    config = db.query(CompanyPaymentConfiguration).filter_by(id="company", status="VERIFIED").first()
    if config is None or not config.qr_asset_url:
        return {"configured": False, "label": "Pay ERRNO via UPI", "qrAssetUrl": None}
    return {"configured": True, "label": "Pay ERRNO via UPI", "qrAssetUrl": config.qr_asset_url}


@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request, x_razorpay_signature: str = Header(default=""),
                          x_razorpay_event_id: str = Header(default=""), db: Session = Depends(get_db)):
    secret = _env("RAZORPAY_WEBHOOK_SECRET")
    if len(secret) < 32:
        raise HTTPException(503, detail="Payment webhook is not configured")
    raw = await request.body()
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    if not x_razorpay_signature or not hmac.compare_digest(expected, x_razorpay_signature):
        raise HTTPException(401, detail="Invalid webhook signature")
    if not x_razorpay_event_id:
        raise HTTPException(400, detail="Missing provider event identifier")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(400, detail="Invalid webhook JSON") from None
    event_type = payload.get("event", "unknown")
    digest = hashlib.sha256(raw).hexdigest()
    event = PaymentWebhookEvent(provider_event_id=x_razorpay_event_id, event_type=event_type, payload_digest=digest)
    db.add(event)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return {"received": True, "duplicate": True}
    try:
        entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        if event_type == "payment.captured":
            txn = db.query(PaymentTransaction).filter(PaymentTransaction.order_id == entity.get("order_id")).with_for_update().first()
            if txn and entity.get("id") and entity.get("currency") == txn.currency and int(entity.get("amount", -1)) == txn.amount_paise:
                cash = db.query(CashCollection).filter_by(booking_id=txn.booking_id).first()
                if cash is not None:
                    txn.status = "DISPUTED"
                    db.add(FinancialAuditEvent(event_type="payment.cash_conflict", resource_type="payment", resource_id=txn.id,
                        details={"provider_payment_id": entity["id"]}))
                    event.outcome = "conflict"
                else:
                    _record_paid(db, txn, entity["id"])
                    event.outcome = "processed"
            else:
                event.outcome = "unmatched"
        elif event_type == "payment.failed":
            txn = db.query(PaymentTransaction).filter(PaymentTransaction.order_id == entity.get("order_id")).with_for_update().first()
            if txn and txn.status != "PAID":
                txn.status = "PAYMENT_FAILED"
                event.outcome = "processed"
        elif event_type == "refund.processed":
            refund_entity = payload.get("payload", {}).get("refund", {}).get("entity", {})
            refund = db.query(FinancialRefund).filter_by(provider_refund_id=refund_entity.get("id")).with_for_update().first()
            if refund is None:
                refund_id = (refund_entity.get("notes") or {}).get("errno_refund_id")
                if refund_id:
                    refund = db.query(FinancialRefund).filter_by(id=refund_id).with_for_update().first()
                    if refund is not None and not refund.provider_refund_id:
                        refund.provider_refund_id = refund_entity.get("id")
            if refund is not None and refund.status != "processed":
                txn = db.query(PaymentTransaction).filter_by(id=refund.payment_id).with_for_update().first()
                if txn and refund_entity.get("payment_id") == txn.payment_id and int(refund_entity.get("amount", -1)) == refund.amount_paise:
                    refund.status = "processed"
                    txn.refunded_paise += refund.amount_paise
                    txn.status = "REFUNDED" if txn.refunded_paise == txn.amount_paise else "PARTIALLY_REFUNDED"
                    prior_commission_reversals = db.query(func.coalesce(func.sum(PlatformFinanceLedgerEntry.amount_paise), 0)).filter(
                        PlatformFinanceLedgerEntry.payment_id == txn.id,
                        PlatformFinanceLedgerEntry.entry_type == "COMMISSION_REVERSAL").scalar() or 0
                    target_commission_reversals = (txn.commission_paise * txn.refunded_paise) // txn.amount_paise
                    commission_reversal = int(target_commission_reversals) - int(prior_commission_reversals)
                    worker_reversal = refund.amount_paise - commission_reversal
                    if worker_reversal:
                        db.add(WalletLedgerEntry(worker_id=txn.worker_id, booking_id=txn.booking_id, payment_id=txn.id,
                            category="REFUND_REVERSAL", amount_paise=worker_reversal,
                            idempotency_key=f"refund-worker-reversal:{refund.id}"))
                    if commission_reversal:
                        db.add(PlatformFinanceLedgerEntry(payment_id=txn.id, refund_id=refund.id,
                            entry_type="COMMISSION_REVERSAL", amount_paise=commission_reversal,
                            idempotency_key=f"refund-commission-reversal:{refund.id}"))
                    db.add(FinancialAuditEvent(event_type="refund.processed", resource_type="refund", resource_id=refund.id,
                        details={"amount_paise": refund.amount_paise, "worker_reversal_paise": worker_reversal,
                                 "commission_reversal_paise": commission_reversal}))
                    event.outcome = "processed"
                else:
                    event.outcome = "unmatched"
            else:
                event.outcome = "unmatched"
        else:
            event.outcome = "ignored"
        event.processed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("razorpay_webhook_processing_failed event=%s", event_type)
        raise HTTPException(500, detail="Webhook processing failed; provider retry is safe") from None
    return {"received": True, "duplicate": False}


def _wallet_summary(db: Session, worker_id: str):
    entries = db.query(WalletLedgerEntry).filter(WalletLedgerEntry.worker_id == worker_id).order_by(
        WalletLedgerEntry.created_at.desc(), WalletLedgerEntry.id.desc()).all()
    available = pending = withdrawn = reserved = 0
    for row in entries:
        if row.category == "EARNING_PENDING": pending += row.amount_paise
        elif row.category in {"EARNING_AVAILABLE", "WITHDRAWAL_FAILED_RELEASE", "ADMIN_ADJUSTMENT_CREDIT"}: available += row.amount_paise
        elif row.category in {"WITHDRAWAL_RESERVED", "REFUND_REVERSAL", "ADMIN_ADJUSTMENT_DEBIT"}:
            available -= row.amount_paise
        elif row.category == "WITHDRAWAL_COMPLETED": withdrawn += row.amount_paise
    requests = db.query(WorkerWithdrawal).filter(WorkerWithdrawal.worker_id == worker_id).all()
    reserved = sum(x.amount_paise for x in requests if x.status in {"PENDING_EXTERNAL_PAYOUT", "APPROVED", "PAYOUT_PROCESSING"})
    # Keep the raw ledger total long enough to surface a shortfall when a
    # refund reverses earnings that were already withdrawn. Hiding this under
    # a zero clamp would allow a later withdrawal despite an outstanding debt.
    refund_shortfall = max(0, -available)
    available = max(0, available)
    cash_rows = db.query(CashCollection).filter(CashCollection.worker_id == worker_id).all()
    cash_collected = sum(x.amount_paise for x in cash_rows if x.worker_confirmed_at is not None)
    cash_unresolved = sum(x.amount_paise for x in cash_rows if x.reconciliation_status != "RECONCILED")
    paid_jobs = db.query(PaymentTransaction.booking_id).join(Job, Job.id == PaymentTransaction.booking_id).filter(
        PaymentTransaction.worker_id == worker_id, PaymentTransaction.status == "PAID", PaymentTransaction.refunded_paise < PaymentTransaction.amount_paise,
        Job.status == "completed").distinct().count()
    total_earned = db.query(func.coalesce(func.sum(WalletLedgerEntry.amount_paise), 0)).filter(
        WalletLedgerEntry.worker_id == worker_id,
        WalletLedgerEntry.category.in_(["EARNING_PENDING", "EARNING_AVAILABLE"])).scalar() or 0
    total_refunded = db.query(func.coalesce(func.sum(WalletLedgerEntry.amount_paise), 0)).filter(
        WalletLedgerEntry.worker_id == worker_id, WalletLedgerEntry.category == "REFUND_REVERSAL").scalar() or 0
    recent = [{"id": x.id, "bookingId": x.booking_id, "category": x.category, "amountPaise": x.amount_paise,
               "currency": x.currency, "createdAt": x.created_at} for x in entries[:50]]
    return {"totalEarningsPaise": max(0, int(total_earned) - int(total_refunded)),
            "pendingEarningsPaise": pending, "availableBalancePaise": available, "withdrawalPendingPaise": reserved,
            "totalWithdrawnPaise": withdrawn, "cashCollectedPaise": cash_collected,
            "unresolvedSettlementAdjustmentsPaise": cash_unresolved + refund_shortfall,
            "eligibleCompletedOrders": paid_jobs, "withdrawalEligible": paid_jobs >= 3 and available > 0,
            "eligibilityReasons": ([] if paid_jobs >= 3 else [f"Complete {3-paid_jobs} more eligible paid orders"])
            + ([] if available > 0 else ["No available balance"]), "recentTransactions": recent}


@router.get("/worker/wallet")
def worker_wallet(user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "worker")
    return _wallet_summary(db, user.id)


@router.post("/worker/withdrawals")
def request_withdrawal(body: WithdrawalRequest, user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "worker")
    db.query(User).filter_by(id=user.id).with_for_update().first()
    if db.query(WorkerWithdrawal).filter_by(idempotency_key=body.idempotencyKey).first():
        existing = db.query(WorkerWithdrawal).filter_by(idempotency_key=body.idempotencyKey, worker_id=user.id).first()
        if existing:
            return {"withdrawalId": existing.id, "status": existing.status, "amountPaise": existing.amount_paise}
        raise HTTPException(409, detail="Idempotency key already used")
    summary = _wallet_summary(db, user.id)
    if summary["eligibleCompletedOrders"] < 3:
        raise HTTPException(409, detail={"code": "WITHDRAWAL_NOT_ELIGIBLE", "reasons": summary["eligibilityReasons"]})
    if summary["unresolvedSettlementAdjustmentsPaise"] > 0:
        raise HTTPException(409, detail={"code": "SETTLEMENT_HOLD", "message": "An unresolved refund adjustment blocks withdrawal."})
    if body.amountPaise > summary["availableBalancePaise"]:
        raise HTTPException(409, detail="Withdrawal exceeds available balance")
    payout_method = db.query(WorkerPayoutMethod).filter_by(id=body.payoutMethodId, worker_id=user.id,
        status="VERIFIED", kyc_verified=True).first()
    if payout_method is None:
        raise HTTPException(409, detail={"code": "PAYOUT_METHOD_UNVERIFIED", "message": "Admin verification of payout method and KYC is required before withdrawal."})
    withdrawal = WorkerWithdrawal(worker_id=user.id, amount_paise=body.amountPaise, payout_method_id=body.payoutMethodId,
                                  status="PENDING_EXTERNAL_PAYOUT", idempotency_key=body.idempotencyKey)
    db.add(withdrawal)
    db.flush()
    db.add(WalletLedgerEntry(worker_id=user.id, withdrawal_id=withdrawal.id, category="WITHDRAWAL_RESERVED",
        amount_paise=body.amountPaise, idempotency_key=f"withdrawal-reserve:{withdrawal.id}"))
    db.add(FinancialAuditEvent(actor_id=user.id, event_type="withdrawal.requested", resource_type="withdrawal",
        resource_id=withdrawal.id, details={"amount_paise": body.amountPaise}))
    db.commit()
    return {"withdrawalId": withdrawal.id, "status": withdrawal.status, "amountPaise": withdrawal.amount_paise}


@router.get("/worker/payout-methods")
def list_worker_payout_methods(user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "worker")
    return [{"id": p.id, "status": p.status, "kycVerified": p.kyc_verified, "createdAt": p.created_at}
        for p in db.query(WorkerPayoutMethod).filter_by(worker_id=user.id).order_by(WorkerPayoutMethod.created_at.desc()).all()]


@router.post("/worker/payout-methods")
def add_worker_payout_method(body: PayoutMethodCreate, user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "worker")
    row = WorkerPayoutMethod(worker_id=user.id, provider_reference=body.providerReference.strip(), status="PENDING_VERIFICATION", kyc_verified=False)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        row = db.query(WorkerPayoutMethod).filter_by(worker_id=user.id, provider_reference=body.providerReference.strip()).first()
    return {"id": row.id, "status": row.status, "message": "Payout method requires manual admin verification."}


@router.post("/bookings/{booking_id}/cash-collection")
def start_cash_collection(booking_id: str, user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    require_role(user, "shop_owner", "shopkeeper")
    job = _owned_job(db, booking_id, user, lock=True)
    if job.status != "completed" or job.completed_at is None:
        raise HTTPException(409, detail="Cash payment is available after verified completion")
    txn = db.query(PaymentTransaction).filter_by(booking_id=job.id).with_for_update().first()
    if txn is None:
        _, amount, commission, worker = _payment_snapshot(db, job)
        txn = PaymentTransaction(booking_id=job.id, shopkeeper_id=user.id, worker_id=job.assigned_worker_id,
            amount_paise=amount, commission_paise=commission, worker_earning_paise=worker,
            status="PAYMENT_PENDING", idempotency_key=f"booking-payment:{job.id}")
        db.add(txn); db.flush()
    if txn.status == "PAID":
        raise HTTPException(409, detail="Booking already paid online")
    if txn.order_id:
        raise HTTPException(409, detail="An online order already exists; resolve its provider status before switching to cash")
    cash = db.query(CashCollection).filter_by(booking_id=job.id).first()
    if cash is None:
        cash = CashCollection(booking_id=job.id, payment_id=txn.id, shopkeeper_id=user.id,
            worker_id=job.assigned_worker_id, amount_paise=txn.amount_paise,
            shopkeeper_confirmed_at=datetime.now(timezone.utc))
        db.add(cash)
    txn.status = "CASH_PENDING"
    db.commit()
    return {"cashCollectionId": cash.id, "status": cash.reconciliation_status, "amountPaise": cash.amount_paise,
            "message": "Cash is pending both-party confirmation and admin reconciliation."}


@router.post("/cash-collections/{collection_id}/confirm")
def confirm_cash_collection(collection_id: str, body: CashConfirmation, user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    cash = db.query(CashCollection).filter_by(id=collection_id).with_for_update().first()
    if cash is None:
        raise HTTPException(404, detail="Cash collection not found")
    if user.id == cash.shopkeeper_id:
        cash.shopkeeper_confirmed_at = cash.shopkeeper_confirmed_at or datetime.now(timezone.utc)
    elif user.id == cash.worker_id:
        cash.worker_confirmed_at = cash.worker_confirmed_at or datetime.now(timezone.utc)
    else:
        raise HTTPException(403, detail="Only the booking parties can confirm cash")
    if body.evidenceReference:
        cash.evidence_reference = body.evidenceReference
    if cash.worker_confirmed_at and cash.shopkeeper_confirmed_at:
        cash.reconciliation_status = "PENDING_ADMIN_RECONCILIATION"
    db.commit()
    return {"cashCollectionId": cash.id, "status": cash.reconciliation_status,
            "shopkeeperConfirmed": cash.shopkeeper_confirmed_at is not None, "workerConfirmed": cash.worker_confirmed_at is not None}


@admin_router.get("/finance/overview")
def finance_overview(admin=Depends(require_admin("payments.read")), db: Session = Depends(get_db)):
    count = lambda status: db.query(func.count(PaymentTransaction.id)).filter(PaymentTransaction.status == status).scalar() or 0
    sumq = lambda q: int(q.scalar() or 0)
    paid = db.query(func.coalesce(func.sum(PaymentTransaction.amount_paise - PaymentTransaction.refunded_paise), 0)).filter(PaymentTransaction.status == "PAID")
    settled_bookings = select(PaymentTransaction.booking_id).where(
        PaymentTransaction.status.in_(["PAID", "PARTIALLY_REFUNDED", "REFUNDED", "CASH_RECONCILED"]))
    outstanding_rows = db.query(PricingQuote.final_service_charge).join(Job, Job.id == PricingQuote.job_id).filter(
        Job.status == "completed", ~Job.id.in_(settled_bookings)).all()
    outstanding_paise = sum(int((Decimal(row[0]) * 100).to_integral_exact()) for row in outstanding_rows)
    withdrawals = db.query(WorkerWithdrawal)
    cashq = db.query(CashCollection)
    platform_credits = sumq(db.query(func.coalesce(func.sum(PlatformFinanceLedgerEntry.amount_paise), 0)).filter(PlatformFinanceLedgerEntry.entry_type.in_(["COMMISSION_CREDIT", "CASH_COMMISSION_RECEIPT"])))
    platform_reversals = sumq(db.query(func.coalesce(func.sum(PlatformFinanceLedgerEntry.amount_paise), 0)).filter(PlatformFinanceLedgerEntry.entry_type == "COMMISSION_REVERSAL"))
    return {"verifiedCollectionsPaise": sumq(paid), "errnoCommissionNetPaise": platform_credits - platform_reversals,
        "outstandingCompletedPaymentsPaise": outstanding_paise,
        "outstandingCompletedJobCount": len(outstanding_rows),
        "paymentPendingCount": count("PAYMENT_PENDING"), "paymentFailedCount": count("PAYMENT_FAILED"),
        "refundTotalPaise": sumq(db.query(func.coalesce(func.sum(FinancialRefund.amount_paise), 0)).filter(FinancialRefund.status == "processed")),
        "workerPayablePaise": sumq(db.query(func.coalesce(func.sum(PaymentTransaction.worker_earning_paise), 0)).filter(PaymentTransaction.status == "PAID")),
        "withdrawalsPendingPaise": sumq(db.query(func.coalesce(func.sum(WorkerWithdrawal.amount_paise), 0)).filter(WorkerWithdrawal.status == "PENDING_EXTERNAL_PAYOUT")),
        "cashCollectionsPending": cashq.filter(CashCollection.reconciliation_status != "RECONCILED").count(),
        "unreconciledWebhookEvents": db.query(PaymentWebhookEvent).filter(PaymentWebhookEvent.outcome.in_(["unmatched", "received"])).count()}


@admin_router.get("/finance/payments")
def finance_payments(limit: int = 50, offset: int = 0, admin=Depends(require_admin("payments.read")), db: Session = Depends(get_db)):
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(422, detail="Invalid pagination")
    rows = db.query(PaymentTransaction).order_by(PaymentTransaction.created_at.desc()).offset(offset).limit(limit).all()
    return {"items": [{"id": p.id, "bookingId": p.booking_id, "shopkeeperId": p.shopkeeper_id, "workerId": p.worker_id,
        "amountPaise": p.amount_paise, "commissionPaise": p.commission_paise, "workerEarningPaise": p.worker_earning_paise,
        "orderId": p.order_id, "paymentId": p.payment_id, "status": p.status, "createdAt": p.created_at, "paidAt": p.paid_at} for p in rows], "limit": limit, "offset": offset}


@admin_router.get("/finance/refunds")
def finance_refunds(limit: int = 50, offset: int = 0, admin=Depends(require_admin("payments.read")), db: Session = Depends(get_db)):
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(422, detail="Invalid pagination")
    rows = db.query(FinancialRefund).order_by(FinancialRefund.created_at.desc()).offset(offset).limit(limit).all()
    return {"items": [{"id": row.id, "paymentId": row.payment_id, "amountPaise": row.amount_paise,
        "reason": row.reason, "providerRefundId": row.provider_refund_id, "status": row.status,
        "createdAt": row.created_at} for row in rows], "limit": limit, "offset": offset}


@admin_router.get("/finance/audit")
def finance_audit(limit: int = 50, offset: int = 0, admin=Depends(require_admin("payments.read")), db: Session = Depends(get_db)):
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(422, detail="Invalid pagination")
    rows = db.query(FinancialAuditEvent).order_by(FinancialAuditEvent.created_at.desc()).offset(offset).limit(limit).all()
    return {"items": [{"id": row.id, "actorId": row.actor_id, "eventType": row.event_type,
        "resourceType": row.resource_type, "resourceId": row.resource_id, "details": row.details,
        "createdAt": row.created_at} for row in rows], "limit": limit, "offset": offset}


@admin_router.post("/refunds")
def create_refund(body: RefundRequest, admin=Depends(require_admin("payments.refund")), db: Session = Depends(get_db)):
    existing = db.query(FinancialRefund).filter_by(idempotency_key=body.idempotencyKey).first()
    if existing:
        return {"refundId": existing.id, "status": existing.status, "amountPaise": existing.amount_paise}
    payment = db.query(PaymentTransaction).filter_by(id=body.paymentId).with_for_update().first()
    if payment is None or payment.status not in {"PAID", "PARTIALLY_REFUNDED"} or not payment.payment_id:
        raise HTTPException(409, detail="Only provider-confirmed payments can be refunded")
    amount = body.amountPaise or payment.amount_paise - payment.refunded_paise
    pending_refunds = db.query(func.coalesce(func.sum(FinancialRefund.amount_paise), 0)).filter(
        FinancialRefund.payment_id == payment.id, FinancialRefund.status.in_(["REQUESTED", "PROVIDER_UNKNOWN"])).scalar() or 0
    if amount <= 0 or payment.refunded_paise + int(pending_refunds) + amount > payment.amount_paise:
        raise HTTPException(422, detail="Refund exceeds unrefunded payment amount")
    refund = FinancialRefund(payment_id=payment.id, amount_paise=amount, reason=body.reason,
        status="REQUESTED", created_by=admin.firebase_uid, idempotency_key=body.idempotencyKey)
    db.add(refund)
    db.flush()
    db.add(FinancialAuditEvent(actor_id=admin.firebase_uid, event_type="refund.requested", resource_type="payment", resource_id=payment.id,
        details={"refund_id": refund.id, "amount_paise": amount, "reason": body.reason}))
    db.commit()
    try:
        result = _api(f"/payments/{urllib.parse.quote(payment.payment_id)}/refund", "POST", {
            "amount": amount, "notes": {"reason": body.reason[:180], "errno_refund_id": refund.id}})
        refund.provider_refund_id = result.get("id")
        db.add(refund)
        db.commit()
    except HTTPException:
        # Do not retry blindly: provider may have accepted a request before the timeout.
        refund.status = "PROVIDER_UNKNOWN"
        db.add(refund)
        db.commit()
        raise
    return {"refundId": refund.id, "providerRefundId": refund.provider_refund_id, "status": refund.status, "amountPaise": amount}


@admin_router.get("/reconciliation")
def reconciliation(admin=Depends(require_admin("reconciliation.read")), db: Session = Depends(get_db)):
    return {"payments": [{"id": p.id, "bookingId": p.booking_id, "orderId": p.order_id, "paymentId": p.payment_id, "status": p.status}
        for p in db.query(PaymentTransaction).filter(PaymentTransaction.status != "PAID").limit(100).all()],
        "cashCollections": [{"id": c.id, "bookingId": c.booking_id, "status": c.reconciliation_status, "amountPaise": c.amount_paise}
        for c in db.query(CashCollection).filter(CashCollection.reconciliation_status != "RECONCILED").limit(100).all()],
        "unmatchedEvents": db.query(PaymentWebhookEvent).filter(PaymentWebhookEvent.outcome == "unmatched").count()}


@admin_router.get("/finance/company-upi-qr")
def get_company_qr(admin=Depends(require_admin("payments.read")), db: Session = Depends(get_db)):
    config = db.query(CompanyPaymentConfiguration).filter_by(id="company").first()
    return {"qrAssetUrl": config.qr_asset_url if config else None,
            "status": config.status if config else "UNCONFIGURED", "verifiedBy": config.verified_by if config else None,
            "verifiedAt": config.verified_at if config else None}


@admin_router.put("/finance/company-upi-qr")
def update_company_qr(body: CompanyQRUpdate, admin=Depends(require_admin("payments.manage")), db: Session = Depends(get_db)):
    parsed = urllib.parse.urlparse(body.qrAssetUrl)
    if parsed.scheme != "https" or not parsed.netloc:
        raise HTTPException(422, detail="QR asset must use an HTTPS URL")
    config = db.query(CompanyPaymentConfiguration).filter_by(id="company").with_for_update().first()
    if config is None:
        config = CompanyPaymentConfiguration(id="company")
        db.add(config)
    config.qr_asset_url = body.qrAssetUrl
    config.status = "VERIFIED" if body.verified else "PENDING_VERIFICATION"
    config.verified_by = admin.firebase_uid if body.verified else None
    config.verified_at = datetime.now(timezone.utc) if body.verified else None
    db.add(FinancialAuditEvent(actor_id=admin.firebase_uid, event_type="company_upi_qr.updated", resource_type="company_payment_configuration",
        resource_id="company", details={"status": config.status, "reason": body.reason}))
    db.commit()
    return {"status": config.status, "qrAssetUrl": config.qr_asset_url}


@admin_router.post("/cash-collections/{collection_id}/resolve")
def resolve_cash_collection(collection_id: str, body: CashResolution,
                            admin=Depends(require_admin("reconciliation.manage")), db: Session = Depends(get_db)):
    cash = db.query(CashCollection).filter_by(id=collection_id).with_for_update().first()
    if cash is None:
        raise HTTPException(404, detail="Cash collection not found")
    if cash.reconciliation_status in {"RECONCILED", "DISPUTED"}:
        raise HTTPException(409, detail="Cash collection is already resolved")
    if body.outcome == "RECONCILED":
        if not cash.shopkeeper_confirmed_at or not cash.worker_confirmed_at:
            raise HTTPException(409, detail="Both shopkeeper and worker must confirm cash receipt")
        txn = db.query(PaymentTransaction).filter_by(id=cash.payment_id).with_for_update().first()
        if txn is None or body.errnoCommissionReceivedPaise != txn.commission_paise:
            raise HTTPException(409, detail="Admin must reconcile the exact commission amount from the booking snapshot")
        txn.status = "CASH_RECONCILED"
        txn.paid_at = datetime.now(timezone.utc)
        db.add(PlatformFinanceLedgerEntry(payment_id=txn.id, cash_collection_id=cash.id,
            entry_type="CASH_COMMISSION_RECEIPT", amount_paise=txn.commission_paise,
            idempotency_key=f"cash-commission:{cash.id}"))
    cash.reconciliation_status = body.outcome
    db.add(FinancialAuditEvent(actor_id=admin.firebase_uid, event_type=f"cash.{body.outcome.lower()}",
        resource_type="cash_collection", resource_id=cash.id,
        details={"reason": body.reason, "errno_commission_received_paise": body.errnoCommissionReceivedPaise}))
    db.commit()
    return {"cashCollectionId": cash.id, "status": cash.reconciliation_status}


@admin_router.get("/finance/withdrawals")
def finance_withdrawals(admin=Depends(require_admin("withdrawals.read")), db: Session = Depends(get_db)):
    return [{"id": x.id, "workerId": x.worker_id, "amountPaise": x.amount_paise, "status": x.status, "createdAt": x.created_at}
        for x in db.query(WorkerWithdrawal).order_by(WorkerWithdrawal.created_at.desc()).limit(200).all()]


@admin_router.get("/finance/wallets")
def finance_wallets(limit: int = 50, offset: int = 0, admin=Depends(require_admin("wallet.read")), db: Session = Depends(get_db)):
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(422, detail="Invalid pagination")
    workers = db.query(User).filter(User.role == "worker").order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    return {"items": [{"workerId": worker.id, "name": worker.full_name, **_wallet_summary(db, worker.id)} for worker in workers],
            "limit": limit, "offset": offset}


@admin_router.post("/finance/withdrawals/{withdrawal_id}/review")
def review_withdrawal(withdrawal_id: str, body: dict, admin=Depends(require_admin("withdrawals.manage")), db: Session = Depends(get_db)):
    status = body.get("status")
    if status not in {"APPROVED", "REJECTED", "COMPLETED"} or not isinstance(body.get("reason"), str) or not body["reason"].strip():
        raise HTTPException(422, detail="status and review reason are required")
    row = db.query(WorkerWithdrawal).filter_by(id=withdrawal_id).with_for_update().first()
    if row is None:
        raise HTTPException(404, detail="Withdrawal not found")
    if status == "COMPLETED":
        if row.status != "APPROVED" or not isinstance(body.get("providerPayoutId"), str) or len(body["providerPayoutId"]) < 6:
            raise HTTPException(409, detail="Record completion only after an external transfer is verified with its provider reference")
        row.provider_payout_id = body["providerPayoutId"]
        row.status = "COMPLETED"
        db.add(WalletLedgerEntry(worker_id=row.worker_id, withdrawal_id=row.id, category="WITHDRAWAL_COMPLETED",
            amount_paise=row.amount_paise, idempotency_key=f"withdrawal-completed:{row.id}"))
    elif row.status != "PENDING_EXTERNAL_PAYOUT":
        raise HTTPException(409, detail="Withdrawal has already been reviewed")
    else:
        row.status = status
    row.reviewed_by = admin.firebase_uid
    row.review_reason = body["reason"].strip()
    if status == "REJECTED":
        db.add(WalletLedgerEntry(worker_id=row.worker_id, withdrawal_id=row.id, category="WITHDRAWAL_FAILED_RELEASE",
            amount_paise=row.amount_paise, idempotency_key=f"withdrawal-release:{row.id}"))
    db.add(FinancialAuditEvent(actor_id=admin.firebase_uid, event_type=f"withdrawal.{status.lower()}", resource_type="withdrawal", resource_id=row.id,
        details={"reason": row.review_reason, "amount_paise": row.amount_paise}))
    db.commit()
    return {"withdrawalId": row.id, "status": row.status}


@admin_router.get("/finance/payout-methods")
def payout_methods(admin=Depends(require_admin("wallet.read")), db: Session = Depends(get_db)):
    return [{"id": p.id, "workerId": p.worker_id, "providerReferenceSuffix": p.provider_reference[-4:],
             "status": p.status, "kycVerified": p.kyc_verified, "createdAt": p.created_at}
        for p in db.query(WorkerPayoutMethod).order_by(WorkerPayoutMethod.created_at.desc()).limit(200).all()]


@admin_router.post("/finance/payout-methods/{method_id}/review")
def review_payout_method(method_id: str, body: dict, admin=Depends(require_admin("withdrawals.manage")), db: Session = Depends(get_db)):
    if body.get("status") not in {"VERIFIED", "REJECTED"} or not isinstance(body.get("reason"), str) or not body["reason"].strip():
        raise HTTPException(422, detail="status and reason are required")
    row = db.query(WorkerPayoutMethod).filter_by(id=method_id).with_for_update().first()
    if row is None:
        raise HTTPException(404, detail="Payout method not found")
    row.status = body["status"]
    row.kyc_verified = body["status"] == "VERIFIED"
    row.verified_by = admin.firebase_uid
    row.verified_at = datetime.now(timezone.utc)
    db.add(FinancialAuditEvent(actor_id=admin.firebase_uid, event_type=f"payout_method.{row.status.lower()}",
        resource_type="payout_method", resource_id=row.id, details={"reason": body["reason"].strip()}))
    db.commit()
    return {"id": row.id, "status": row.status, "kycVerified": row.kyc_verified}
