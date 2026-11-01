import hashlib
import hmac
import json
import secrets
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import firebase_auth
import routers.payments as payments
from database import Base, get_db
from models import (AdminPermission, Job, PaymentTransaction, PricingQuote, Shop, User,
                    CashCollection, PlatformFinanceLedgerEntry, WalletLedgerEntry, WorkerPayoutMethod, WorkerWithdrawal)

PAYMENT_TEST_SECRET = secrets.token_urlsafe(32)
WEBHOOK_TEST_SECRET = secrets.token_urlsafe(32)


@pytest.fixture
def payment_client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    now = datetime.now(timezone.utc)
    with factory() as db:
        owner = User(id="owner", firebase_uid="owner-uid", full_name="Owner", role="shop_owner")
        worker = User(id="worker", firebase_uid="worker-uid", full_name="Worker", role="worker")
        db.add_all([owner, worker, AdminPermission(firebase_uid="finance-admin", active=True,
            permissions=["payments.read", "payments.refund", "wallet.read", "withdrawals.read", "withdrawals.manage", "reconciliation.read", "reconciliation.manage"],
            granted_by_uid="test", reason="test"), Shop(id="shop", owner_id="owner", shop_name="Shop")])
        job = Job(id="job-1", shop_id="shop", title="Shift", pay_amount=160.0, duration_type="1 hour",
            status="completed", assigned_worker_id="worker", completed_at=now, created_at=now)
        db.add(job)
        db.add(PricingQuote(id="quote-1", user_id="owner", duration_hours=1, service_start_at=now,
            base_price=Decimal("120.00"), maximum_price=Decimal("160.00"), time_multiplier=Decimal("1.25"),
            demand_multiplier=Decimal("1.0"), raw_price=Decimal("150"), final_service_charge=Decimal("160.00"),
            commission_rate=Decimal("0.08"), commission_amount=Decimal("12.80"), worker_payout_amount=Decimal("147.20"),
            pricing_rule_version=1, created_at=now, expires_at=now+timedelta(minutes=5), consumed_at=now,
            job_id="job-1", status="consumed"))
        db.commit()

    def get_test_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    claims = {"owner-token": {"uid": "owner-uid"}, "worker-token": {"uid": "worker-uid"}, "admin-token": {"uid": "finance-admin"}}
    monkeypatch.setattr(firebase_auth, "verify_firebase_token", lambda token: claims[token] if token in claims else (_ for _ in ()).throw(HTTPException(401)))
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_public")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", PAYMENT_TEST_SECRET)
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", WEBHOOK_TEST_SECRET)
    monkeypatch.setenv("RAZORPAY_ENVIRONMENT", "test")
    app = FastAPI()
    app.include_router(payments.router)
    app.include_router(payments.admin_router)
    app.dependency_overrides[get_db] = get_test_db
    with TestClient(app) as client:
        yield client, factory
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_payment_requires_shopkeeper_verified_completion(payment_client):
    client, factory = payment_client
    with factory() as db:
        db.query(Job).filter_by(id="job-1").update({"status": "in_progress", "completed_at": None})
        db.commit()
    response = client.post("/api/v1/bookings/job-1/payment-order", headers={"Authorization": "Bearer owner-token"})
    assert response.status_code == 409


def test_order_uses_immutable_quote_and_webhook_credits_once(payment_client, monkeypatch):
    client, factory = payment_client
    monkeypatch.setattr(payments, "_api", lambda path, method="GET", payload=None: {"id": "order_test_1", "status": "created"})
    response = client.post("/api/v1/bookings/job-1/payment-order", headers={"Authorization": "Bearer owner-token"})
    assert response.status_code == 200
    assert response.json()["amountPaise"] == 16000
    with factory() as db:
        txn = db.query(PaymentTransaction).one()
        assert (txn.commission_paise, txn.worker_earning_paise) == (1280, 14720)
        assert txn.order_id == "order_test_1"
    payload = {"event": "payment.captured", "payload": {"payment": {"entity": {
        "id": "pay_test_1", "order_id": "order_test_1", "amount": 16000, "currency": "INR", "status": "captured"}}}}
    raw = json.dumps(payload, separators=(",", ":")).encode()
    signature = hmac.new(WEBHOOK_TEST_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    headers = {"X-Razorpay-Signature": signature, "X-Razorpay-Event-Id": "evt_test_1", "Content-Type": "application/json"}
    assert client.post("/api/v1/webhooks/razorpay", content=raw, headers=headers).status_code == 200
    assert client.post("/api/v1/webhooks/razorpay", content=raw, headers=headers).json()["duplicate"] is True
    with factory() as db:
        assert db.query(WalletLedgerEntry).filter_by(idempotency_key="earning:" + db.query(PaymentTransaction).one().id).count() == 1
        commission = db.query(PlatformFinanceLedgerEntry).filter_by(entry_type="COMMISSION_CREDIT").one()
        assert commission.amount_paise == 1280


def test_order_is_owner_scoped_and_legacy_quote_rejected(payment_client):
    client, factory = payment_client
    other = client.post("/api/v1/bookings/job-1/payment-order", headers={"Authorization": "Bearer worker-token"})
    assert other.status_code == 403
    with factory() as db:
        db.query(PricingQuote).delete()
        db.commit()
    missing = client.post("/api/v1/bookings/job-1/payment-order", headers={"Authorization": "Bearer owner-token"})
    assert missing.status_code == 409 and missing.json()["detail"]["code"] == "FINANCIAL_SNAPSHOT_MISSING"


def test_unauthorized_admin_finance_access_fails(payment_client):
    client, _ = payment_client
    response = client.get("/api/v1/admin/finance/overview", headers={"Authorization": "Bearer owner-token"})
    assert response.status_code == 403


def test_finance_overview_includes_completed_unpaid_bookings(payment_client):
    client, _ = payment_client
    response = client.get("/api/v1/admin/finance/overview", headers={"Authorization": "Bearer admin-token"})
    assert response.status_code == 200
    assert response.json()["outstandingCompletedPaymentsPaise"] == 16000
    assert response.json()["outstandingCompletedJobCount"] == 1


def test_client_verification_requires_provider_captured_and_signature(payment_client, monkeypatch):
    client, factory = payment_client
    monkeypatch.setattr(payments, "_api", lambda path, method="GET", payload=None: {"id": "order_test_2", "status": "created"})
    order = client.post("/api/v1/bookings/job-1/payment-order", headers={"Authorization": "Bearer owner-token"}).json()
    secret = PAYMENT_TEST_SECRET
    signature = hmac.new(secret.encode(), b"order_test_2|pay_test_2", hashlib.sha256).hexdigest()
    monkeypatch.setattr(payments, "_api", lambda path, method="GET", payload=None: {"order_id": "order_test_2", "amount": 16000, "currency": "INR", "status": "authorized"})
    response = client.post("/api/v1/payments/verify", headers={"Authorization": "Bearer owner-token"}, json={
        "bookingId": "job-1", "razorpayOrderId": order["razorpayOrderId"], "razorpayPaymentId": "pay_test_2", "razorpaySignature": signature})
    assert response.status_code == 200 and response.json()["status"] == "PAYMENT_PROCESSING"
    with factory() as db:
        assert db.query(WalletLedgerEntry).count() == 0


def test_cash_requires_both_parties_and_admin_commission_reconciliation(payment_client):
    client, factory = payment_client
    started = client.post("/api/v1/bookings/job-1/cash-collection", headers={"Authorization": "Bearer owner-token"})
    assert started.status_code == 200
    collection_id = started.json()["cashCollectionId"]
    assert client.post(f"/api/v1/cash-collections/{collection_id}/confirm", headers={"Authorization": "Bearer worker-token"}, json={}).status_code == 200
    admin = client.post(f"/api/v1/admin/cash-collections/{collection_id}/resolve", headers={"Authorization": "Bearer admin-token"}, json={
        "outcome": "RECONCILED", "reason": "Commission proof checked by finance team", "errnoCommissionReceivedPaise": 1280})
    assert admin.status_code == 200 and admin.json()["status"] == "RECONCILED"
    with factory() as db:
        assert db.query(CashCollection).one().reconciliation_status == "RECONCILED"
        assert db.query(PaymentTransaction).one().status == "CASH_RECONCILED"
        assert db.query(PlatformFinanceLedgerEntry).filter_by(entry_type="CASH_COMMISSION_RECEIPT").one().amount_paise == 1280


def test_withdrawal_requires_three_paid_jobs_verified_method_and_reserves_ledger(payment_client):
    client, factory = payment_client
    now = datetime.now(timezone.utc)
    with factory() as db:
        for index in range(3):
            job_id = f"paid-job-{index}"
            db.add(Job(id=job_id, shop_id="shop", title=f"Paid {index}", pay_amount=100,
                duration_type="1 hour", status="completed", assigned_worker_id="worker", completed_at=now, created_at=now))
            db.flush()
            tx = PaymentTransaction(id=f"pay-{index}", booking_id=job_id, shopkeeper_id="owner", worker_id="worker",
                amount_paise=10000, commission_paise=800, worker_earning_paise=9200, status="PAID",
                payment_id=f"provider-{index}", idempotency_key=f"payment-{index}")
            db.add(tx)
            db.add(WalletLedgerEntry(worker_id="worker", booking_id=job_id, payment_id=tx.id, category="EARNING_AVAILABLE",
                amount_paise=9200, idempotency_key=f"earning:{tx.id}"))
        db.add(WorkerPayoutMethod(id="verified-method", worker_id="worker", provider_reference="provider-reference-1",
            status="VERIFIED", kyc_verified=True, verified_by="finance-admin", verified_at=now))
        db.commit()
    result = client.post("/api/v1/worker/withdrawals", headers={"Authorization": "Bearer worker-token"},
        json={"amountPaise": 5000, "payoutMethodId": "verified-method", "idempotencyKey": "withdrawal-test-key-0001"})
    assert result.status_code == 200 and result.json()["status"] == "PENDING_EXTERNAL_PAYOUT"
    duplicate = client.post("/api/v1/worker/withdrawals", headers={"Authorization": "Bearer worker-token"},
        json={"amountPaise": 5000, "payoutMethodId": "verified-method", "idempotencyKey": "withdrawal-test-key-0001"})
    assert duplicate.status_code == 200 and duplicate.json()["withdrawalId"] == result.json()["withdrawalId"]
    wallet = client.get("/api/v1/worker/wallet", headers={"Authorization": "Bearer worker-token"}).json()
    assert wallet["availableBalancePaise"] == 22600 and wallet["withdrawalPendingPaise"] == 5000


def test_wallet_surfaces_refund_shortfall_as_withdrawal_hold(payment_client):
    client, factory = payment_client
    with factory() as db:
        db.add(WalletLedgerEntry(worker_id="worker", category="REFUND_REVERSAL", amount_paise=2500,
            idempotency_key="refund-reversal-shortfall"))
        db.commit()
    wallet = client.get("/api/v1/worker/wallet", headers={"Authorization": "Bearer worker-token"}).json()
    assert wallet["availableBalancePaise"] == 0
    assert wallet["unresolvedSettlementAdjustmentsPaise"] == 2500


def test_partial_refund_requires_provider_webhook_and_reverses_worker_ledger(payment_client, monkeypatch):
    client, factory = payment_client
    with factory() as db:
        txn = PaymentTransaction(id="paid-payment", booking_id="job-1", shopkeeper_id="owner", worker_id="worker",
            amount_paise=16000, commission_paise=1280, worker_earning_paise=14720, currency="INR",
            status="PAID", payment_id="pay_refund_test", idempotency_key="paid-payment-key")
        db.add(txn)
        db.add(WalletLedgerEntry(worker_id="worker", booking_id="job-1", payment_id=txn.id,
            category="EARNING_AVAILABLE", amount_paise=14720, idempotency_key="earning:paid-payment"))
        db.commit()
    monkeypatch.setattr(payments, "_api", lambda *args, **kwargs: {"id": "rfnd_test_1", "status": "pending"})
    response = client.post("/api/v1/admin/refunds", headers={"Authorization": "Bearer admin-token"}, json={
        "paymentId": "paid-payment", "amountPaise": 5000, "reason": "Verified service issue",
        "idempotencyKey": "refund-idempotency-test-0001"})
    assert response.status_code == 200 and response.json()["status"] == "REQUESTED"
    payload = {"event": "refund.processed", "payload": {"refund": {"entity": {
        "id": "rfnd_test_1", "payment_id": "pay_refund_test", "amount": 5000,
        "notes": {"errno_refund_id": response.json()["refundId"]}}}}}
    raw = json.dumps(payload, separators=(",", ":")).encode()
    signature = hmac.new(WEBHOOK_TEST_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    headers = {"X-Razorpay-Signature": signature, "X-Razorpay-Event-Id": "evt_refund_1", "Content-Type": "application/json"}
    assert client.post("/api/v1/webhooks/razorpay", content=raw, headers=headers).status_code == 200
    with factory() as db:
        txn = db.query(PaymentTransaction).filter_by(id="paid-payment").one()
        assert txn.refunded_paise == 5000 and txn.status == "PARTIALLY_REFUNDED"
        reversal = db.query(WalletLedgerEntry).filter_by(idempotency_key=f"refund-worker-reversal:{response.json()['refundId']}").one()
        assert reversal.amount_paise == 4600
        commission_reversal = db.query(PlatformFinanceLedgerEntry).filter_by(entry_type="COMMISSION_REVERSAL").one()
        assert commission_reversal.amount_paise == 400
