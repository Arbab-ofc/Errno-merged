# ERRNO payments and worker wallet

## Financial authority

Payment amounts are read only from the immutable `PricingQuote` attached to the completed job. The payment layer converts the stored customer charge, commission, and worker payout to integer paise and rejects missing, non-positive, or unbalanced snapshots. It does not change the pricing engine or commission policy. Completion is currently authorized by the shopkeeper through the existing job completion endpoint; workers cannot unlock payment by self-declaration.

## Razorpay setup

Configure `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, `RAZORPAY_ENVIRONMENT=test|live`, and `RAZORPAY_API_TIMEOUT_SECONDS` in a backend-only secret manager. Begin with isolated Razorpay Test Mode credentials. Register `/api/v1/webhooks/razorpay` in the Razorpay Dashboard and subscribe to `payment.captured`, `payment.failed`, and `refund.processed`. Never ship the Key Secret or webhook secret in mobile apps or Admin JavaScript.

The shopkeeper can create an order only when the canonical job is `completed` with `completed_at` set. The provider order uses the server pricing snapshot and is stored under a unique booking constraint. Checkout callback data is signature checked and independently fetched from Razorpay before ledger credit. A signed webhook can complete the same transition idempotently. A client closing checkout does not mark an order failed.

## Wallet and payouts

Worker balance is derived from append-only integer-paise ledger rows. ERRNO commission collections and refund reversals are independently recorded in the platform ledger. Three distinct completed, provider-paid jobs are required before requesting withdrawal. A payout method is a provider reference only; the application does not collect raw bank account credentials. A finance administrator must manually verify payout-method ownership and KYC before it becomes usable. Requests reserve balance and stay `PENDING_EXTERNAL_PAYOUT`; approval is a queue decision, not a transfer. Admin may record completion only with an external transfer reference after checking provider/bank evidence. ERRNO RazorpayX/Payout product authorization and credentials are not assumed.

## Cash

Cash can be selected only before a Razorpay order exists. Both shopkeeper and worker confirm it. It stays outside Razorpay transactions and wallet earnings until Finance reconciles the exact commission from the stored snapshot. Pending cash blocks withdrawal. A static QR scan is never accepted as payment proof.

## Refunds and unresolved business policy

Refund requests require `payments.refund`, are created idempotently before contacting Razorpay, and stay pending until a provider refund event is verified. If the provider request times out, the record is marked `PROVIDER_UNKNOWN` and must be reconciled; the API deliberately will not issue a blind duplicate. Processed refunds create compensating wallet ledger entries. When a worker earning has already been withdrawn, the debit remains visible as an unresolved hold for finance review.

Cancellation windows, no-show fees, refund eligibility, partial refund policy, provider-fee responsibility, and cash ownership/settlement terms remain business decisions. No default policy or replacement commission has been introduced. The YES BANK QR is displayed only after an administrator with `payments.manage` configures an HTTPS asset and marks its destination verified. Reconciliation is still required after a QR payment.

## Endpoints

- `POST /api/v1/bookings/{booking_id}/payment-order`
- `POST /api/v1/payments/verify`
- `GET /api/v1/payments/{payment_id}`
- `GET /api/v1/bookings/{booking_id}/payment-status`
- `POST /api/v1/webhooks/razorpay`
- `GET /api/v1/worker/wallet`
- `GET|POST /api/v1/worker/payout-methods`
- `POST /api/v1/worker/withdrawals`
- `POST /api/v1/bookings/{booking_id}/cash-collection`
- `POST /api/v1/cash-collections/{collection_id}/confirm`
- `GET /api/v1/worker/cash-collections`
- `GET /api/v1/worker/company-upi-qr`
- Finance operations under `/api/v1/admin/finance`, `/api/v1/admin/refunds`, and `/api/v1/admin/reconciliation`.

The finance Admin APIs require explicit persisted grants such as `payments.read`, `payments.refund`, `payments.manage`, `wallet.read`, `withdrawals.read`, `withdrawals.manage`, `reconciliation.read`, and `reconciliation.manage`. No administrator grant is changed by this feature.

The additive Alembic revision is `5e91c0f4a8d2` (parent `46aa7d91bc02`). Apply only after schema review and backup on the target environment; this feature work does not apply migrations.
