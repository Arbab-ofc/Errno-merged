import express from 'express';
import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import pino from 'pino';
import QRCode from 'qrcode';
import makeWASocket, { DisconnectReason, useMultiFileAuthState } from '@whiskeysockets/baileys';
import { validOtpDelivery, verifyInternalRequest } from './security.js';

const logger = pino({ level: process.env.LOG_LEVEL || 'info' });
const port = Number(process.env.WHATSAPP_GATEWAY_PORT || 8787);
const bind = process.env.WHATSAPP_GATEWAY_BIND || '127.0.0.1';
const sessionPath = path.resolve(process.env.WHATSAPP_GATEWAY_SESSION_PATH || './session');
const secret = process.env.WHATSAPP_GATEWAY_INTERNAL_AUTH_SECRET || '';
const qrTtl = Number(process.env.WHATSAPP_GATEWAY_QR_TTL_SECONDS || 60);
const app = express();
app.disable('x-powered-by');
app.use(express.json({ limit: '16kb', strict: true }));

const state = { status: 'DISCONNECTED', qr: null, qrExpiresAt: null, socket: null, account: null,
  connectedAt: null, disconnectedAt: null, lastHeartbeatAt: null, lastError: null, reconnectTimer: null,
  stopping: false, attemptIds: new Map(), usedNonces: new Map() };
let sendQueue = Promise.resolve();
let queuedSends = 0;
let persistAttemptTail = Promise.resolve();
let persistNonceTail = Promise.resolve();

async function authorized(req, res, next) {
  const timestamp = req.get('X-ERRNO-Timestamp') || '';
  const signature = req.get('X-ERRNO-Signature') || '';
  const nonce = req.get('X-ERRNO-Nonce') || '';
  const now = Date.now();
  const verdict = verifyInternalRequest({ timestamp, signature, nonce, method: req.method, path: req.path,
    body: req.body, secret, now, nonceStore: state.usedNonces });
  if (verdict === 'invalid') return res.status(secret.length < 32 ? 503 : 401).json({ error: secret.length < 32 ? 'internal_auth_not_configured' : 'invalid_internal_auth' });
  if (verdict === 'replay') return res.status(409).json({ error: 'replayed_request' });
  try { await persistUsedNonces(); }
  catch { state.usedNonces.delete(nonce); return res.status(503).json({ error: 'internal_auth_state_unavailable' }); }
  next();
}

app.use('/internal', authorized);
app.get('/internal/health', (_req, res) => res.json({ healthy: true, status: state.status, timestamp: new Date().toISOString() }));
app.get('/internal/whatsapp/status', (_req, res) => {
  state.lastHeartbeatAt = new Date().toISOString();
  res.json({ status: state.status, account: state.account, connectedAt: state.connectedAt,
    disconnectedAt: state.disconnectedAt, lastHeartbeatAt: state.lastHeartbeatAt, lastError: state.lastError,
    pairingRequired: state.status === 'QR_REQUIRED', qrExpiresAt: state.qrExpiresAt });
});
app.get('/internal/whatsapp/qr', async (_req, res) => {
  if (state.status !== 'QR_REQUIRED' || !state.qr || Date.parse(state.qrExpiresAt || '') <= Date.now()) {
    return res.status(404).json({ status: state.status, qrDataUrl: null, expiresAt: null });
  }
  res.json({ status: state.status, qrDataUrl: await QRCode.toDataURL(state.qr), expiresAt: state.qrExpiresAt });
});
app.post('/internal/whatsapp/connect', async (req, res) => {
  if (req.body?.regenerate === true && state.status === 'QR_REQUIRED') {
    state.stopping = true; const previousSocket = state.socket; state.socket = null; previousSocket?.end(undefined);
    await new Promise((resolve) => setTimeout(resolve, 300));
    state.stopping = false;
    state.qr = null; state.qrExpiresAt = null; state.status = 'DISCONNECTED';
  }
  await connectWhatsApp();
  res.status(202).json({ status: state.status });
});
app.post('/internal/whatsapp/disconnect', async (_req, res) => {
  clearTimeout(state.reconnectTimer);
  state.stopping = true;
  state.socket?.end(undefined);
  state.socket = null;
  state.status = 'DISCONNECTED'; state.qr = null; state.qrExpiresAt = null;
  state.disconnectedAt = new Date().toISOString();
  await persistOperationalState();
  res.json({ status: state.status });
});
app.post('/internal/whatsapp/logout', async (_req, res) => {
  clearTimeout(state.reconnectTimer);
  state.stopping = true;
  try { await state.socket?.logout(); } catch (error) { logger.warn({ err: error }, 'whatsapp logout request failed'); }
  state.socket = null; state.qr = null; state.qrExpiresAt = null; state.account = null;
  state.status = 'DISCONNECTED'; state.disconnectedAt = new Date().toISOString();
  await fs.rm(sessionPath, { recursive: true, force: true });
  await secureSessionDirectory();
  await persistOperationalState();
  res.json({ status: state.status, credentialsRemoved: true });
});
app.post('/internal/whatsapp/send', async (req, res) => {
  const { requestId, phone, messageType, otp, expiresInSeconds } = req.body || {};
  if (!validOtpDelivery({ requestId, phone, messageType, otp, expiresInSeconds })) {
    return res.status(422).json({ accepted: false, error: 'invalid_message_request' });
  }
  const existing = state.attemptIds.get(requestId);
  if (existing) return res.status(409).json({ accepted: existing.accepted, messageId: existing.messageId || null, error: 'duplicate_request' });
  if (state.status !== 'CONNECTED' || !state.socket) return res.status(503).json({ accepted: false, error: 'whatsapp_disconnected' });
  if (queuedSends >= 4) return res.status(429).json({ accepted: false, error: 'send_queue_full' });
  state.attemptIds.set(requestId, { accepted: false, createdAt: Date.now() });
  const message = `ERRNO verification code: ${otp}\n\nThis code expires in ${Math.ceil(expiresInSeconds / 60)} minutes.\n\nDo not share this code with anyone.`;
  try {
    await persistAttemptIds();
    queuedSends += 1;
    const send = sendQueue.then(async () => {
      if (state.status !== 'CONNECTED' || !state.socket) throw new Error('WhatsApp disconnected before send');
      const response = await state.socket.sendMessage(`${phone.slice(1)}@s.whatsapp.net`, { text: message });
      await new Promise((resolve) => setTimeout(resolve, 1200));
      return response;
    });
    sendQueue = send.catch(() => {});
    const result = await send;
    const messageId = result?.key?.id || null;
    state.attemptIds.set(requestId, { accepted: true, messageId, createdAt: Date.now() });
    await persistAttemptIds();
    res.status(202).json({ accepted: true, messageId, deliveryStatus: 'accepted' });
  } catch (error) {
    // Transport errors are ambiguous after dispatch. Keep the key to prevent a replayed OTP send.
    state.attemptIds.set(requestId, { accepted: false, messageId: null, uncertain: true, createdAt: Date.now() });
    await persistAttemptIds().catch(() => {});
    logger.warn({ requestId, err: error }, 'whatsapp send failed');
    res.status(503).json({ accepted: false, error: 'send_failed' });
  } finally {
    queuedSends = Math.max(0, queuedSends - 1);
  }
});

async function secureSessionDirectory() {
  await fs.mkdir(sessionPath, { recursive: true, mode: 0o700 });
  await fs.chmod(sessionPath, 0o700);
  for (const entry of await fs.readdir(sessionPath, { withFileTypes: true })) {
    if (entry.isFile()) await fs.chmod(path.join(sessionPath, entry.name), 0o600).catch(() => {});
  }
}

async function persistAttemptIds() {
  persistAttemptTail = persistAttemptTail.then(async () => {
    const cutoff = Date.now() - 15 * 60_000;
    for (const [id, attempt] of state.attemptIds) if (attempt.createdAt < cutoff) state.attemptIds.delete(id);
    const destination = path.join(sessionPath, 'send-idempotency.json');
    const temporary = `${destination}.tmp`;
    await fs.writeFile(temporary, JSON.stringify([...state.attemptIds]), { mode: 0o600 });
    await fs.chmod(temporary, 0o600);
    await fs.rename(temporary, destination);
  });
  await persistAttemptTail;
}

async function persistOperationalState() {
  const filename = path.join(sessionPath, 'gateway-status.json');
  const temporary = `${filename}.tmp`;
  const safeState = { account: state.account, connectedAt: state.connectedAt,
    disconnectedAt: state.disconnectedAt, lastError: state.lastError };
  await fs.writeFile(temporary, JSON.stringify(safeState), { mode: 0o600 });
  await fs.chmod(temporary, 0o600);
  await fs.rename(temporary, filename);
}

async function persistUsedNonces() {
  persistNonceTail = persistNonceTail.then(async () => {
    const now = Date.now();
    for (const [nonce, expires] of state.usedNonces) if (expires <= now) state.usedNonces.delete(nonce);
    const filename = path.join(sessionPath, 'internal-nonces.json');
    const temporary = `${filename}.tmp`;
    await fs.writeFile(temporary, JSON.stringify([...state.usedNonces]), { mode: 0o600 });
    await fs.chmod(temporary, 0o600);
    await fs.rename(temporary, filename);
  });
  await persistNonceTail;
}

async function connectWhatsApp() {
  if (state.status === 'CONNECTED' || state.status === 'CONNECTING') return;
  clearTimeout(state.reconnectTimer); state.stopping = false; state.status = 'CONNECTING'; state.lastError = null;
  try {
    await secureSessionDirectory();
    const { state: authState, saveCreds } = await useMultiFileAuthState(sessionPath);
    const socket = makeWASocket({ auth: authState, logger: pino({ level: 'silent' }), printQRInTerminal: false,
      connectTimeoutMs: 20_000, defaultQueryTimeoutMs: 30_000, keepAliveIntervalMs: 20_000 });
    state.socket = socket;
    socket.ev.on('creds.update', async () => {
      await saveCreds();
      for (const entry of await fs.readdir(sessionPath, { withFileTypes: true })) {
        if (entry.isFile()) await fs.chmod(path.join(sessionPath, entry.name), 0o600).catch(() => {});
      }
    });
    socket.ev.on('connection.update', ({ connection, lastDisconnect, qr }) => {
      if (qr) {
        state.qr = qr; state.qrExpiresAt = new Date(Date.now() + qrTtl * 1000).toISOString(); state.status = 'QR_REQUIRED';
        setTimeout(() => { if (state.qr === qr) { state.qr = null; state.qrExpiresAt = null; if (state.status === 'QR_REQUIRED') state.status = 'CONNECTING'; } }, qrTtl * 1000).unref();
      }
      if (connection === 'open') {
        state.status = 'CONNECTED'; state.qr = null; state.qrExpiresAt = null; state.connectedAt = new Date().toISOString();
        const jid = socket.user?.id || '';
        state.account = { phoneMasked: jid.split(':')[0].replace(/\D/g, '').slice(-4).padStart(4, '*'), displayName: socket.user?.name || null };
        persistOperationalState().catch(() => {});
      }
      if (connection === 'close') {
        state.socket = null; state.qr = null; state.qrExpiresAt = null; state.disconnectedAt = new Date().toISOString();
        const code = lastDisconnect?.error?.output?.statusCode;
        const loggedOut = code === DisconnectReason.loggedOut;
        state.status = state.stopping ? 'DISCONNECTED' : loggedOut ? 'ERROR' : 'RECONNECTING';
        state.lastError = loggedOut ? 'WhatsApp session logged out; unlink and pair again.' : 'Connection interrupted; reconnect scheduled.';
        persistOperationalState().catch(() => {});
        if (!state.stopping && !loggedOut) state.reconnectTimer = setTimeout(() => connectWhatsApp().catch(() => {}), 3000);
      }
    });
  } catch (error) {
    state.status = 'ERROR'; state.lastError = 'Gateway connection initialization failed.';
    logger.error({ err: error }, 'whatsapp connection initialization failed');
    throw error;
  }
}

await secureSessionDirectory();
try {
  const savedNonces = JSON.parse(await fs.readFile(path.join(sessionPath, 'internal-nonces.json'), 'utf8'));
  if (Array.isArray(savedNonces)) for (const [nonce, expires] of savedNonces) {
    if (typeof nonce === 'string' && Number.isFinite(expires) && expires > Date.now()) state.usedNonces.set(nonce, expires);
  }
} catch (error) { if (error?.code !== 'ENOENT') logger.warn('could not load internal nonce metadata'); }
try {
  const savedState = JSON.parse(await fs.readFile(path.join(sessionPath, 'gateway-status.json'), 'utf8'));
  if (savedState && typeof savedState === 'object') {
    state.account = savedState.account || null;
    state.connectedAt = savedState.connectedAt || null;
    state.disconnectedAt = savedState.disconnectedAt || null;
    state.lastError = savedState.lastError || null;
  }
} catch (error) { if (error?.code !== 'ENOENT') logger.warn('could not load gateway status metadata'); }
try {
  const stored = JSON.parse(await fs.readFile(path.join(sessionPath, 'send-idempotency.json'), 'utf8'));
  if (Array.isArray(stored)) for (const [id, record] of stored) {
    if (typeof id === 'string' && record?.createdAt > Date.now() - 15 * 60_000) state.attemptIds.set(id, record);
  }
} catch (error) { if (error?.code !== 'ENOENT') logger.warn('could not load message idempotency metadata'); }

const server = app.listen(port, bind, () => logger.info({ bind, port }, 'ERRNO WhatsApp gateway listening'));
if (secret.length >= 32 && process.env.WHATSAPP_GATEWAY_AUTOCONNECT === 'true') connectWhatsApp().catch(() => {});
async function shutdown() {
  state.stopping = true; clearTimeout(state.reconnectTimer); state.socket?.end(undefined);
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(1), 5000).unref();
}
process.on('SIGTERM', shutdown); process.on('SIGINT', shutdown);
