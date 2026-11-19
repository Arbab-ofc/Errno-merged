import crypto from 'node:crypto';

const secret = process.env.WHATSAPP_GATEWAY_INTERNAL_AUTH_SECRET || '';
if (secret.length < 32) process.exit(1);
const path = '/internal/health';
const timestamp = String(Math.floor(Date.now() / 1000));
const nonce = crypto.randomBytes(18).toString('base64url');
const signature = crypto.createHmac('sha256', secret)
  .update(`${timestamp}\nGET\n${path}\n`)
  .digest('hex');

try {
  const response = await fetch(`http://127.0.0.1:${process.env.WHATSAPP_GATEWAY_PORT || 8787}${path}`, {
    headers: {
      'X-ERRNO-Timestamp': timestamp,
      'X-ERRNO-Nonce': nonce,
      'X-ERRNO-Signature': signature,
    },
    signal: AbortSignal.timeout(4000),
  });
  const status = await response.json();
  if (!response.ok || status.healthy !== true) process.exit(1);
} catch {
  process.exit(1);
}
