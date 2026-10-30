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
};
