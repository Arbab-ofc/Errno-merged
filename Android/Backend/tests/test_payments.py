import hashlib
import hmac
import json
import secrets
import sys
import io
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import firebase_auth
import routers.payments as payments
from database import Base, get_db
from models import (AdminPermission, Job, PaymentTransaction, PricingQuote, Shop, User,
                    CashCollection, CompanyPaymentConfiguration, ManualPaymentSubmission, PlatformFinanceLedgerEntry, WalletLedgerEntry, WorkerPayoutMethod, WorkerWithdrawal)
from models import KYCVerificationProfile

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
            permissions=["payments.read", "payments.manage", "payments.refund", "wallet.read", "withdrawals.read", "withdrawals.manage", "reconciliation.read", "reconciliation.manage"],
            granted_by_uid="test", reason="test"), Shop(id="shop", owner_id="owner", shop_name="Shop")])
        # Razorpay regression cases explicitly opt into their provider; production defaults to Manual QR.
        db.add(CompanyPaymentConfiguration(id="company", active_provider="RAZORPAY"))
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
    claim_lookup = lambda token: claims[token] if token in claims else (_ for _ in ()).throw(HTTPException(401))
    monkeypatch.setattr(firebase_auth, "verify_firebase_token", claim_lookup)
    monkeypatch.setattr(payments, "verify_firebase_token", claim_lookup)
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_public")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", PAYMENT_TEST_SECRET)
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", WEBHOOK_TEST_SECRET)
    monkeypatch.setenv("RAZORPAY_ENVIRONMENT", "test")
    app = FastAPI()
    app.include_router(payments.router)
    app.include_router(payments.admin_router)
    app.include_router(payments.ws_router)
    app.dependency_overrides[get_db] = get_test_db
    monkeypatch.setattr(payments, "SessionLocal", factory)
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


def test_manual_screenshot_rejection_resubmission_and_approval(payment_client, monkeypatch):
    client, factory = payment_client
    with factory() as db:
        config = db.query(CompanyPaymentConfiguration).filter_by(id="company").one()
        config.active_provider = "MANUAL_QR"; config.status = "VERIFIED"; config.qr_public_id = "errno/payment-qr/live"
        config.qr_asset_url = "https://res.cloudinary.com/demo/image/upload/qr.png"
        db.commit()
    counter = iter(("proof-one", "proof-two"))
    monkeypatch.setattr(payments, "_cloudinary_upload", lambda data, folder, private: {"public_id": next(counter)})
    monkeypatch.setattr(payments, "_cloudinary_destroy", lambda *args: None)
    monkeypatch.setattr(payments, "_private_asset_url", lambda public_id: "https://signed.example/" + public_id)
    image = io.BytesIO(); Image.new("RGB", (4, 4), "white").save(image, format="PNG")
    headers = {"Authorization": "Bearer owner-token"}
    first = client.post("/api/v1/payments/bookings/job-1/manual/submit", headers=headers,
        files={"screenshot": ("proof.png", image.getvalue(), "image/png")})
    assert first.status_code == 200
    assert first.json()["status"] == "PENDING_REVIEW"
    repeated = client.post("/api/v1/payments/bookings/job-1/manual/submit", headers=headers,
        files={"screenshot": ("proof.png", image.getvalue(), "image/png")})
    assert repeated.status_code == 409
    admin = {"Authorization": "Bearer admin-token"}
    rejected = client.post(f"/api/v1/admin/payments/manual/{first.json()['submissionId']}/reject", headers=admin,
        json={"reason": "Screenshot does not show the payment confirmation."})
    assert rejected.status_code == 200 and rejected.json()["status"] == "REJECTED"
    second = client.post("/api/v1/payments/bookings/job-1/manual/submit", headers=headers,
        files={"screenshot": ("proof.png", image.getvalue(), "image/png")})
    assert second.status_code == 200
    approved = client.post(f"/api/v1/admin/payments/manual/{second.json()['submissionId']}/approve", headers=admin)
    assert approved.status_code == 200 and approved.json()["paymentStatus"] == "PAID"
    status = client.get("/api/v1/bookings/job-1/payment-status", headers=headers).json()
    assert status["status"] == "PAID" and status["provider"] == "MANUAL_QR"
    with factory() as db:
        rows = db.query(ManualPaymentSubmission).filter_by(booking_id="job-1").order_by(ManualPaymentSubmission.attempt_number).all()
        assert [row.status for row in rows] == ["REJECTED", "APPROVED"]
        assert db.query(WalletLedgerEntry).filter_by(idempotency_key=f"earning:{status['paymentId']}").count() == 1


def test_payment_socket_auth_and_manual_submission_event(payment_client, monkeypatch):
    client, factory = payment_client
    with factory() as db:
        config = db.query(CompanyPaymentConfiguration).filter_by(id="company").one()
        config.active_provider = "MANUAL_QR"; config.status = "VERIFIED"; config.qr_public_id = "qr"
        config.qr_asset_url = "https://res.cloudinary.com/demo/image/upload/qr.png"
        db.commit()
    monkeypatch.setattr(payments, "_cloudinary_upload", lambda *args: {"public_id": "proof-live-test"})
    monkeypatch.setattr(payments, "_cloudinary_destroy", lambda *args: None)
    monkeypatch.setattr(payments, "_private_asset_url", lambda public_id: "https://signed.example/proof")
    image = io.BytesIO(); Image.new("RGB", (2, 2), "white").save(image, format="PNG")
    admin_headers = {"Authorization": "Bearer admin-token"}
    owner_headers = {"Authorization": "Bearer owner-token"}
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/v1/ws/payments?scope=admin", headers={"Authorization": "Bearer owner-token"}):
            pass
    with client.websocket_connect("/api/v1/ws/payments?scope=admin", subprotocols=["errno.payment.v1", "bearer.admin-token"]) as admin_socket, \
         client.websocket_connect("/api/v1/ws/payments?scope=user", headers=owner_headers) as owner_socket:
        assert admin_socket.receive_json()["eventType"] == "payment_socket.ready"
        assert owner_socket.receive_json()["eventType"] == "payment_socket.ready"
        response = client.post("/api/v1/payments/bookings/job-1/manual/submit", headers=owner_headers,
            files={"screenshot": ("proof.png", image.getvalue(), "image/png")})
        assert response.status_code == 200
        admin_event = admin_socket.receive_json(); owner_event = owner_socket.receive_json()
        assert admin_event["eventType"] == owner_event["eventType"] == "manual_payment.submitted"
        assert admin_event["version"] == 1 and admin_event["status"] == "PENDING_REVIEW"
        assert admin_event["paymentId"] == response.json()["paymentId"]
        assert "screenshotUrl" not in admin_event and "public_id" not in str(admin_event)
        submission_id = response.json()["submissionId"]
        rejected = client.post(f"/api/v1/admin/payments/manual/{submission_id}/reject", headers=admin_headers,
            json={"reason": "Screenshot is not readable."})
        assert rejected.status_code == 200
        rejected_state = client.get("/api/v1/bookings/job-1/payment-status", headers=owner_headers).json()
        assert rejected_state["status"] == "PAYMENT_PENDING" and rejected_state["submission"]["status"] == "REJECTED"
        assert admin_socket.receive_json()["eventType"] == owner_socket.receive_json()["eventType"] == "manual_payment.rejected"
        switched = client.patch("/api/v1/admin/payments/config", headers=admin_headers,
            json={"activeProvider": "RAZORPAY", "merchantName": "ERRNO", "upiId": "payee@example"})
        assert switched.status_code == 200
        assert admin_socket.receive_json()["eventType"] == owner_socket.receive_json()["eventType"] == "payment_config.updated"
        second = client.post("/api/v1/payments/bookings/job-1/manual/submit", headers=owner_headers,
            files={"screenshot": ("proof.png", image.getvalue(), "image/png")})
        assert second.status_code == 200
        resubmitted = admin_socket.receive_json(); owner_resubmitted = owner_socket.receive_json()
        assert resubmitted["eventType"] == owner_resubmitted["eventType"] == "manual_payment.resubmitted"
        approved = client.post(f"/api/v1/admin/payments/manual/{second.json()['submissionId']}/approve", headers=admin_headers)
        assert approved.status_code == 200
        assert admin_socket.receive_json()["status"] == owner_socket.receive_json()["status"] == "PAID"
        repeated_approval = client.post(f"/api/v1/admin/payments/manual/{second.json()['submissionId']}/approve", headers=admin_headers)
        assert repeated_approval.status_code == 409
    # Reconnect is followed by authoritative REST recovery rather than event replay.
    with client.websocket_connect("/api/v1/ws/payments?scope=user", headers=owner_headers) as reconnected:
        assert reconnected.receive_json()["eventType"] == "payment_socket.ready"
        assert client.get("/api/v1/bookings/job-1/payment-status", headers=owner_headers).json()["status"] == "PAID"


def test_payment_socket_hub_is_user_scoped():
    class Socket:
        def __init__(self): self.events = []
        async def send_json(self, event): self.events.append(event)
    owner, unrelated = Socket(), Socket()
    import asyncio
    asyncio.run(payments.payment_event_hub.connect("user:owner", owner))
    asyncio.run(payments.payment_event_hub.connect("user:other", unrelated))
    try:
        asyncio.run(payments.payment_event_hub.publish({"eventType": "manual_payment.approved"}, {"user:owner"}))
        assert len(owner.events) == 1
        assert unrelated.events == []
    finally:
        asyncio.run(payments.payment_event_hub.disconnect("user:owner", owner))
        asyncio.run(payments.payment_event_hub.disconnect("user:other", unrelated))


def test_manual_payment_notification_event_ids_fit_postgres_and_are_idempotent():
    first = payments._manual_notification_event_id("approved", "submission-123", "recipient-456")
    assert len(first) == 64
    assert first == payments._manual_notification_event_id("approved", "submission-123", "recipient-456")
    assert first != payments._manual_notification_event_id("rejected", "submission-123", "recipient-456")


def test_manual_image_validator_accepts_jpeg_png_and_rejects_bad_size_or_mime():
    class Upload:
        def __init__(self, content_type): self.content_type = content_type
    for fmt, mime in (("PNG", "image/png"), ("JPEG", "image/jpeg")):
        image = io.BytesIO(); Image.new("RGB", (3, 3), "green").save(image, format=fmt)
        assert payments._validated_image(Upload(mime), image.getvalue()) == mime
    with pytest.raises(HTTPException) as invalid:
        payments._validated_image(Upload("image/png"), b"not an image")
    assert invalid.value.status_code == 415
    with pytest.raises(HTTPException) as mismatch:
        payments._validated_image(Upload("image/png"), image.getvalue())
    assert mismatch.value.status_code == 415
    with pytest.raises(HTTPException) as oversized:
        payments._validated_image(Upload("image/png"), b"x" * (5 * 1024 * 1024 + 1))
    assert oversized.value.status_code == 413


def test_admin_preview_requests_authenticated_short_lived_cloudinary_download(monkeypatch):
    calls = []
    class Utils:
        @staticmethod
        def private_download_url(public_id, file_format, **options):
            calls.append((public_id, file_format, options)); return "https://signed.example/temporary"
    class Cloudinary: utils = Utils()
    monkeypatch.setattr(payments, "_cloudinary_config", lambda: Cloudinary())
    assert payments._private_asset_url("proof-private", "image/png") == "https://signed.example/temporary"
    assert calls[0][0:2] == ("proof-private", "png")
    assert calls[0][2]["type"] == "authenticated"
    assert calls[0][2]["expires_at"] > int(datetime.now(timezone.utc).timestamp())


def test_cloudinary_upload_failure_and_database_failure_cleanup(payment_client, monkeypatch):
    client, factory = payment_client
    with factory() as db:
        config = db.query(CompanyPaymentConfiguration).filter_by(id="company").one()
        config.active_provider = "MANUAL_QR"; config.status = "VERIFIED"; config.qr_public_id = "qr"
        config.qr_asset_url = "https://res.cloudinary.com/demo/image/upload/qr.png"
        db.commit()
    image = io.BytesIO(); Image.new("RGB", (2, 2), "white").save(image, format="PNG")
    headers = {"Authorization": "Bearer owner-token"}
    monkeypatch.setattr(payments, "_cloudinary_upload", lambda *args: (_ for _ in ()).throw(HTTPException(502, "storage unavailable")))
    failed_upload = client.post("/api/v1/payments/bookings/job-1/manual/submit", headers=headers,
        files={"screenshot": ("proof.png", image.getvalue(), "image/png")})
    assert failed_upload.status_code == 502
    with factory() as db: assert db.query(PaymentTransaction).filter_by(booking_id="job-1").count() == 0

    cleanup = []
    monkeypatch.setattr(payments, "_cloudinary_upload", lambda *args: {"public_id": "orphan-proof"})
    monkeypatch.setattr(payments, "_cloudinary_destroy", lambda public_id, private: cleanup.append((public_id, private)))
    original_commit = Session.commit
    monkeypatch.setattr(Session, "commit", lambda self: (_ for _ in ()).throw(RuntimeError("simulated database outage")))
    failed_db = client.post("/api/v1/payments/bookings/job-1/manual/submit", headers=headers,
        files={"screenshot": ("proof.png", image.getvalue(), "image/png")})
    assert failed_db.status_code == 409
    assert cleanup == [("orphan-proof", True)]
    monkeypatch.setattr(Session, "commit", original_commit)


def test_admin_qr_upload_replacement_is_authorized_and_mobile_config_updates(payment_client, monkeypatch):
    client, _ = payment_client
    uploaded = iter((
        {"public_id": "qr-first", "secure_url": "https://res.cloudinary.com/demo/image/upload/v1/qr-first.png"},
        {"public_id": "qr-second", "secure_url": "https://res.cloudinary.com/demo/image/upload/v2/qr-second.png"},
    ))
    destroyed = []
    monkeypatch.setattr(payments, "_cloudinary_upload", lambda data, folder, private: next(uploaded))
    monkeypatch.setattr(payments, "_cloudinary_destroy", lambda public_id, private: destroyed.append((public_id, private)))
    image = io.BytesIO(); Image.new("RGB", (3, 3), "blue").save(image, format="PNG")
    denied = client.post("/api/v1/admin/payments/qr", headers={"Authorization": "Bearer owner-token"},
        files={"image": ("qr.png", image.getvalue(), "image/png")})
    assert denied.status_code == 403
    admin = {"Authorization": "Bearer admin-token"}
    for expected in ("qr-first", "qr-second"):
        result = client.post("/api/v1/admin/payments/qr", headers=admin,
            files={"image": ("qr.png", image.getvalue(), "image/png")})
        assert result.status_code == 200 and expected in result.json()["qrImageUrl"]
    assert destroyed == [("qr-first", False)]
    changed = client.patch("/api/v1/admin/payments/config", headers=admin,
        json={"activeProvider": "MANUAL_QR", "merchantName": "ERRNO", "upiId": "payee@example"})
    assert changed.status_code == 200
    current = client.get("/api/v1/payments/config", headers={"Authorization": "Bearer owner-token"}).json()
    assert current["activeProvider"] == "MANUAL_QR"
    assert current["manual"]["qrImageUrl"].endswith("qr-second.png")


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
        db.add(KYCVerificationProfile(user_id="worker", subject_role="worker", status="VERIFIED",
            verification_method="MANUAL_DOCUMENT_REVIEW", document_types=["PAN"], verified_document_types=["PAN"], verified_at=now))
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


def test_wallet_requires_identity_verification_when_policy_enabled(payment_client):
    client, _ = payment_client
    wallet = client.get("/api/v1/worker/wallet", headers={"Authorization": "Bearer worker-token"}).json()
    assert wallet["kycVerified"] is False
    assert "KYC_REQUIRED" in wallet["eligibilityReasons"]
    assert wallet["withdrawalEligible"] is False


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
