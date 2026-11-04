import test from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import { validOtpDelivery, verifyInternalRequest } from '../src/security.js';

const secret = 'gateway-test-secret-'.padEnd(40, 'x');
function signed(body = {}, method = 'POST', path = '/internal/whatsapp/send', timestamp = '1700000000', nonce = 'nonce_abcdefghijklmnop') {
  const payload = method === 'GET' ? Buffer.alloc(0) : Buffer.from(JSON.stringify(body));
  const data = Buffer.concat([Buffer.from(`${timestamp}\n${method}\n${path}\n`), payload]);
  return crypto.createHmac('sha256', secret).update(data).digest('hex');
}

test('internal request signatures are accepted once and reject replay', () => {
  const now = 1_700_000_000_000; const nonceStore = new Map();
  const request = { timestamp: '1700000000', method: 'POST', path: '/internal/whatsapp/send', body: { requestId: 'x' },
    nonce: 'nonce_abcdefghijklmnop', secret, now, nonceStore };
  request.signature = signed(request.body);
  assert.equal(verifyInternalRequest(request), 'valid');
  assert.equal(verifyInternalRequest(request), 'replay');
});

test('internal request rejects tampering, expired timestamps and weak configuration', () => {
  const base = { timestamp: '1700000000', method: 'POST', path: '/internal/whatsapp/send', body: { requestId: 'x' },
    nonce: 'nonce_abcdefghijklmnop', secret, now: 1_700_000_000_000, nonceStore: new Map() };
  assert.equal(verifyInternalRequest({ ...base, signature: signed({ requestId: 'y' }) }), 'invalid');
  assert.equal(verifyInternalRequest({ ...base, timestamp: '1699999000', signature: signed() }), 'invalid');
  assert.equal(verifyInternalRequest({ ...base, secret: 'short', signature: signed() }), 'invalid');
});

test('gateway accepts only bounded single-recipient OTP messages', () => {
  const valid = { requestId: 'A'.repeat(32), phone: '+919876543210', messageType: 'otp', otp: '081204', expiresInSeconds: 300 };
  assert.equal(validOtpDelivery(valid), true);
  assert.equal(validOtpDelivery({ ...valid, messageType: 'bulk' }), false);
  assert.equal(validOtpDelivery({ ...valid, phone: '919876543210' }), false);
  assert.equal(validOtpDelivery({ ...valid, otp: '12345' }), false);
  assert.equal(validOtpDelivery({ ...valid, expiresInSeconds: 0 }), false);
});
