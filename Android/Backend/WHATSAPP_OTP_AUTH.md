# ERRNO WhatsApp OTP authentication

ERRNO owns authentication, phone challenges, user identity and revocable API sessions in FastAPI. `WhatsAppGateway/` owns the QR paired WhatsApp Web connection and message transport only. The gateway cannot create or verify OTPs. Google Login remains Firebase ID token based; Firebase verification and administrator RBAC are unchanged.

## Environment

Set the variables in `.env.whatsapp.example` in the backend secret manager (the example values are placeholders). Generate independent high entropy secrets for `WHATSAPP_OTP_HASH_SECRET` and `WHATSAPP_GATEWAY_INTERNAL_AUTH_SECRET`. Enable the backend gateway only after the QR account is paired and the private network is configured. Never expose the gateway port publicly. `WHATSAPP_SESSION_TTL_SECONDS` controls backend session duration and `WHATSAPP_SESSION_MAX_ACTIVE` caps active devices (the oldest session is revoked when the cap is reached). OTP policy and phone/IP rate limits are configurable through the listed values.

The gateway requires `WHATSAPP_GATEWAY_BIND`, `WHATSAPP_GATEWAY_PORT`, `WHATSAPP_GATEWAY_SESSION_PATH`, `WHATSAPP_GATEWAY_INTERNAL_AUTH_SECRET`, and optionally `WHATSAPP_GATEWAY_AUTOCONNECT` and `WHATSAPP_GATEWAY_QR_TTL_SECONDS`. Session files are written under a private directory with restrictive permissions and must be backed up only through the deployment's approved secret storage.

## Start locally

```sh
cd WhatsAppGateway
npm install
WHATSAPP_GATEWAY_INTERNAL_AUTH_SECRET='<same secret configured in FastAPI>' \
WHATSAPP_GATEWAY_SESSION_PATH='./session' npm start
```

For Docker, create the private Docker network named `errno-private`, configure the gateway secret in the deployment environment, then run `docker compose -f WhatsAppGateway/compose.yaml up -d --build`. The compose service has no published host port and expects FastAPI to share the private network. Local development may instead bind the gateway to loopback and use `http://127.0.0.1:8787`.

## Migrations and routes

Apply `Android/Backend/alembic_canonical/versions/46aa7d91bc02_whatsapp_otp_auth.py` through the approved non-production/production migration procedure. It follows canonical head `3b7280d1c6a4` and adds OTP challenges, revocable backend sessions, and gateway metadata audit records. This implementation does not execute migrations.

Mobile routes: `POST /api/v1/auth/whatsapp/send-otp`, `POST /api/v1/auth/whatsapp/resend-otp`, `POST /api/v1/auth/whatsapp/verify-otp`, `POST /api/v1/auth/whatsapp/logout`. OTP response status means WhatsApp accepted the send request, not that handset delivery was confirmed. Session tokens are opaque, returned once, stored hashed in PostgreSQL, and revocable. They are accepted by the ordinary user API authentication dependency; Firebase ID tokens continue through Firebase Admin verification.

Admin routes are under `/api/v1/admin/whatsapp`: `GET status`, `GET qr`, `POST connect`, `POST disconnect`, `POST logout`, and `GET monitoring`. Provision `whatsapp.read`, `whatsapp.connect`, `whatsapp.manage`, `whatsapp.monitor` only to explicitly authorized Firebase administrators using the existing `provision_admin.py` CLI. The QR is retrievable only through FastAPI authorization and is transient.

## Limitations

Baileys implements the unofficial WhatsApp Web protocol. WhatsApp may disconnect or restrict an account; OTP login fails closed if the gateway is unavailable. A `sendMessage` acknowledgment is not a delivery receipt. Do not use this transport for bulk messaging. Keep device credentials and backups out of source control; the gateway volume is sensitive account state.
