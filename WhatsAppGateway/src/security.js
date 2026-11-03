import crypto from 'node:crypto';

export function verifyInternalRequest({ timestamp, signature, nonce, method, path, body, secret, now = Date.now(), nonceStore }) {
  const seconds = Number(timestamp);
  if (secret.length < 32 || !Number.isInteger(seconds) || Math.abs(now / 1000 - seconds) > 60 || !/^[A-Za-z0-9_-]{16,80}$/.test(nonce || '')) return 'invalid';
  const payload = method === 'GET' ? Buffer.alloc(0) : Buffer.from(JSON.stringify(body || {}));
  const canonical = Buffer.concat([Buffer.from(`${timestamp}\n${method}\n${path}\n`), payload]);
  const expected = crypto.createHmac('sha256', secret).update(canonical).digest('hex');
  if (!/^[a-f0-9]{64}$/.test(signature || '') || !crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected))) return 'invalid';
  for (const [key, expires] of nonceStore) if (expires <= now) nonceStore.delete(key);
  if (nonceStore.has(nonce)) return 'replay';
  nonceStore.set(nonce, now + 120_000);
  return 'valid';
}

export function validOtpDelivery({ requestId, phone, messageType, otp, expiresInSeconds }) {
  return typeof requestId === 'string' && /^[A-Za-z0-9_-]{20,64}$/.test(requestId) &&
    typeof phone === 'string' && /^\+[1-9][0-9]{7,14}$/.test(phone) && messageType === 'otp' &&
    typeof otp === 'string' && /^\d{6}$/.test(otp) && Number.isInteger(expiresInSeconds) && expiresInSeconds >= 60 && expiresInSeconds <= 900;
}
