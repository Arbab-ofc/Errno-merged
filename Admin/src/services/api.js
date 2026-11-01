export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

const baseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

async function send(path, { user, method = 'GET', body, signal, publicRequest = false } = {}, refreshed = false) {
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (user && !publicRequest) headers.Authorization = `Bearer ${await user.getIdToken(refreshed)}`;
  let response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: 'omit',
      redirect: 'error',
      signal,
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new ApiError(0, 'Could not reach the ERRNO API. Check the connection and retry.');
  }

  if (response.status === 401 && user && !refreshed) {
    return send(path, { user, method, body, signal, publicRequest }, true);
  }
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = await response.json();
      message = payload.detail || payload.message || message;
    } catch { /* keep the status-based message */ }
    throw new ApiError(response.status, message);
  }
  return response.status === 204 ? null : response.json();
}

export const api = {
  request: send,
  health: (signal) => send('/health', { publicRequest: true, signal }),
  adminMe: (user) => send('/api/v1/admin/me', { user }),
  dashboard: (user, signal) => send('/api/v1/admin/dashboard', { user, signal }),
  shopOwners: (user, params, signal) => send(`/api/v1/admin/shop-owners?${new URLSearchParams(params)}`, { user, signal }),
  shopOwner: (user, id, signal) => send(`/api/v1/admin/shop-owners/${encodeURIComponent(id)}`, { user, signal }),
  updateShopOwner: (user, id, is_active) => send(`/api/v1/admin/shop-owners/${encodeURIComponent(id)}`, { user, method: 'PATCH', body: { is_active } }),
  workers: (user, params, signal) => send(`/api/v1/admin/workers?${new URLSearchParams(params)}`, { user, signal }),
  worker: (user, id, params = {}, signal) => send(`/api/v1/admin/workers/${encodeURIComponent(id)}?${new URLSearchParams(params)}`, { user, signal }),
  updateWorker: (user, id, is_active) => send(`/api/v1/admin/workers/${encodeURIComponent(id)}`, { user, method: 'PATCH', body: { is_active } }),
  jobs: (user, params, signal) => send(`/api/v1/admin/jobs?${new URLSearchParams(params)}`, { user, signal }),
  job: (user, id, signal) => send(`/api/v1/admin/jobs/${encodeURIComponent(id)}`, { user, signal }),
  updateJobStatus: (user, id, status) => send(`/api/v1/admin/jobs/${encodeURIComponent(id)}/status`, { user, method: 'PATCH', body: { status } }),
  pricingDurations: (user) => send('/api/v1/admin/pricing/durations', { user }),
  updatePricingDuration: (user, hours, body) => send(`/api/v1/admin/pricing/durations/${hours}`, { user, method: 'PUT', body }),
  activatePricingDuration: (user, duration_hours) => send('/api/v1/admin/pricing/activate', { user, method: 'POST', body: { duration_hours } }),
  previewPricing: (user, body) => send('/api/v1/admin/pricing/preview', { user, method: 'POST', body }),
  pricingSettings: (user) => send('/api/v1/admin/pricing/settings', { user }),
  updatePricingSettings: (user, body) => send('/api/v1/admin/pricing/settings', { user, method: 'PATCH', body }),
  activatePricingSettings: (user) => send('/api/v1/admin/pricing/settings/activate', { user, method: 'POST', body: {} }),
  pricingTimeRules: (user) => send('/api/v1/admin/pricing/time-rules', { user }),
  createPricingTimeRule: (user, body) => send('/api/v1/admin/pricing/time-rules', { user, method: 'POST', body }),
  updatePricingTimeRule: (user, id, body) => send(`/api/v1/admin/pricing/time-rules/${encodeURIComponent(id)}`, { user, method: 'PATCH', body }),
  activatePricingTimeRule: (user, id) => send(`/api/v1/admin/pricing/time-rules/${encodeURIComponent(id)}/activate`, { user, method: 'POST', body: {} }),
  pricingDemandRules: (user) => send('/api/v1/admin/pricing/demand-rules', { user }),
  createPricingDemandRule: (user, body) => send('/api/v1/admin/pricing/demand-rules', { user, method: 'POST', body }),
  updatePricingDemandRule: (user, id, body) => send(`/api/v1/admin/pricing/demand-rules/${encodeURIComponent(id)}`, { user, method: 'PATCH', body }),
  activatePricingDemandRule: (user, id) => send(`/api/v1/admin/pricing/demand-rules/${encodeURIComponent(id)}/activate`, { user, method: 'POST', body: {} }),
  pricingAreas: (user) => send('/api/v1/admin/pricing/areas', { user }),
  createPricingArea: (user, body) => send('/api/v1/admin/pricing/areas', { user, method: 'POST', body }),
  updatePricingArea: (user, id, body) => send(`/api/v1/admin/pricing/areas/${encodeURIComponent(id)}`, { user, method: 'PATCH', body }),
  activatePricingArea: (user, id) => send(`/api/v1/admin/pricing/areas/${encodeURIComponent(id)}/activate`, { user, method: 'POST', body: {} }),
  pricingAudit: (user, params = {}) => send(`/api/v1/admin/pricing/audit?${new URLSearchParams(params)}`, { user }),
  pricingBookings: (user, params = {}) => send(`/api/v1/admin/pricing/bookings?${new URLSearchParams(params)}`, { user }),
  presenceSummary: (user, signal) => send('/api/v1/admin/presence/summary', { user, signal }),
  whatsappStatus: (user) => send('/api/v1/admin/whatsapp/status', { user }),
  whatsappQr: (user) => send('/api/v1/admin/whatsapp/qr', { user }),
  whatsappConnect: (user) => send('/api/v1/admin/whatsapp/connect', { user, method: 'POST', body: {} }),
  whatsappDisconnect: (user) => send('/api/v1/admin/whatsapp/disconnect', { user, method: 'POST', body: {} }),
  whatsappLogout: (user) => send('/api/v1/admin/whatsapp/logout', { user, method: 'POST', body: {} }),
  whatsappMonitoring: (user) => send('/api/v1/admin/whatsapp/monitoring', { user }),
};
