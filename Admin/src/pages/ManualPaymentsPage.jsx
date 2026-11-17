import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { api } from '../services/api';
import { PageHeader } from '../components/PageHeader';

const money = (paise) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format((Number(paise) || 0) / 100);

export function ManualPaymentsPage() {
  const { user, admin } = useAuth();
  const [config, setConfig] = useState(null); const [rows, setRows] = useState([]); const [selected, setSelected] = useState(null);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState('PENDING_REVIEW'); const [offset, setOffset] = useState(0); const [merchant, setMerchant] = useState(''); const [upi, setUpi] = useState('');
  const [uploading, setUploading] = useState(false); const [error, setError] = useState('');
  const [socketConnected, setSocketConnected] = useState(false);
  const refreshRef = useRef(null);
  const canManage = (admin?.permissions || []).includes('payments.manage');
  const refresh = useCallback(async () => {
    try {
      const [settings, queue] = await Promise.all([api.manualPaymentConfig(user), api.manualPayments(user, filter, offset)]);
      setConfig(settings); setRows(queue.items || []); setTotal(queue.total || 0); setMerchant(settings.merchantName || ''); setUpi(settings.upiId || ''); setError('');
      if (selected) { try { setSelected(await api.manualPayment(user, selected.id)); } catch { setSelected(null); } }
    } catch (e) { setError(e.message); }
  }, [user, filter, offset, selected?.id]);
  useEffect(() => { refreshRef.current = refresh; }, [refresh]);
  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => {
    let active = true; let socket; let retryTimer; let fallbackTimer; let retryDelay = 1000; let connecting = false;
    const startFallback = () => { if (!fallbackTimer) fallbackTimer = window.setInterval(() => refreshRef.current?.(), 30000); };
    const stopFallback = () => { if (fallbackTimer) window.clearInterval(fallbackTimer); fallbackTimer = null; };
    const connect = async () => {
      if (!active || connecting || (socket && socket.readyState <= WebSocket.OPEN)) return;
      connecting = true;
      try {
        socket = await api.paymentSocket(user, 'admin');
        if (!active) { socket.close(); return; }
        socket.onopen = () => { connecting = false; setSocketConnected(true); stopFallback(); refreshRef.current?.(); };
        socket.onmessage = (message) => {
          try {
            const event = JSON.parse(message.data);
            if (event.version === 1 && ['manual_payment.submitted', 'manual_payment.resubmitted', 'manual_payment.approved', 'manual_payment.rejected', 'payment_config.updated'].includes(event.eventType)) refreshRef.current?.();
          } catch { /* Ignore malformed or unsupported event payloads. */ }
        };
        socket.onclose = () => {
          connecting = false; setSocketConnected(false); startFallback();
          if (active) { retryTimer = window.setTimeout(connect, retryDelay); retryDelay = Math.min(retryDelay * 2, 30000); }
        };
        socket.onerror = () => socket?.close();
      } catch {
        connecting = false; setSocketConnected(false); startFallback();
        if (active) { retryTimer = window.setTimeout(connect, retryDelay); retryDelay = Math.min(retryDelay * 2, 30000); }
      }
    };
    const onVisibility = () => { if (document.visibilityState === 'visible') { refreshRef.current?.(); if (!socket || socket.readyState > WebSocket.OPEN) connect(); } };
    connect(); document.addEventListener('visibilitychange', onVisibility);
    return () => { active = false; clearTimeout(retryTimer); stopFallback(); document.removeEventListener('visibilitychange', onVisibility); socket?.close(); };
  }, [user]);
  async function saveSettings(provider = config?.activeProvider) {
    try { await api.updateManualPaymentConfig(user, { activeProvider: provider, merchantName: merchant || null, upiId: upi || null }); await refresh(); }
    catch (e) { setError(e.message); }
  }
  async function upload(file) {
    if (!file) return; setUploading(true); setError('');
    try { await api.uploadPaymentQr(user, file); await refresh(); }
    catch (e) { setError(e.message); }
    finally { setUploading(false); }
  }
  async function approve(row) {
    if (!window.confirm(`Approve payment for booking ${row.bookingId} (${money(row.amountPaise)})?`)) return;
    try { await api.approveManualPayment(user, row.id); setSelected(null); await refresh(); } catch (e) { setError(e.message); await refresh(); }
  }
  async function reject(row) {
    const reason = window.prompt('Required rejection reason:'); if (!reason?.trim()) return;
    try { await api.rejectManualPayment(user, row.id, reason.trim()); setSelected(null); await refresh(); } catch (e) { setError(e.message); await refresh(); }
  }
  return <>
    <PageHeader title="Manual Payment Verification" description="Payment settings and screenshot reviews. The pending queue refreshes automatically." onRefresh={refresh} />
    {error && <div className="inline-error" role="alert">{error}</div>}
    <section className="recent-panel"><div className="panel-heading"><div><h2>Payment settings</h2><p>Provider choice applies to new payment obligations. Existing payment records retain their provider.</p></div></div>
      <label className="form-field">Active provider<select value={config?.activeProvider || 'MANUAL_QR'} onChange={(e) => saveSettings(e.target.value)} disabled={!canManage || !config}><option value="MANUAL_QR">Manual QR</option><option value="RAZORPAY">Razorpay</option></select></label>
      <label className="form-field">Merchant / account display name<input value={merchant} onChange={(e) => setMerchant(e.target.value)} disabled={!canManage} /></label>
      <label className="form-field">UPI ID (optional)<input value={upi} onChange={(e) => setUpi(e.target.value)} disabled={!canManage} /></label>
      <button className="secondary-button" disabled={!canManage} onClick={() => saveSettings()}>Save payment details</button>
      <label className="form-field">Upload or replace payment QR<input type="file" accept="image/jpeg,image/png,image/webp" disabled={!canManage || uploading} onChange={(e) => upload(e.target.files?.[0])} /></label>
      {uploading && <p>Uploading QR…</p>}{config?.qrImageUrl && <img src={config.qrImageUrl} alt="Current ERRNO payment QR" style={{ width: 220, maxWidth: '100%', objectFit: 'contain' }} />}
      {!config?.configured && <p>Manual QR is not available until a valid QR image is uploaded.</p>}
    </section>
    <section className="recent-panel"><div className="panel-heading"><div><h2>Screenshot submissions <span>{filter === 'PENDING_REVIEW' ? total : ''}</span></h2><p>{socketConnected ? 'Live updates connected.' : 'Reconnecting; status refreshes every 30 seconds.'} Screenshot links expire after five minutes.</p></div><select value={filter} onChange={(e) => { setOffset(0); setFilter(e.target.value); }}><option value="PENDING_REVIEW">Pending</option><option value="APPROVED">Approved</option><option value="REJECTED">Rejected</option><option value="ALL">All submissions</option></select></div>
      {rows.length === 0 ? <div className="small-empty">No submissions in this view.</div> : <div className="table-scroll"><table className="data-table"><thead><tr><th>Booking</th><th>Shopkeeper</th><th>Amount</th><th>Attempt</th><th>Submitted</th><th>Status</th><th>Review</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id}><td>{row.bookingId}</td><td>{row.shopkeeperName || row.shopkeeperId}</td><td>{money(row.amountPaise)}</td><td>{row.attemptNumber}</td><td>{new Date(row.submittedAt).toLocaleString()}</td><td>{row.status}</td><td><button className="secondary-button" onClick={() => setSelected(row)}>Open</button></td></tr>)}</tbody></table></div>}
      <div className="pagination-actions"><button className="secondary-button" disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 50))}>Previous</button><span>Showing {total ? offset + 1 : 0}–{offset + rows.length} of {total}</span><button className="secondary-button" disabled={offset + rows.length >= total} onClick={() => setOffset(offset + 50)}>Next</button></div>
    </section>
    {selected && <div role="dialog" aria-modal="true" className="recent-panel"><div className="panel-heading"><div><h2>Payment review · {selected.bookingId}</h2><p>{selected.shopkeeperName || selected.shopkeeperId} · {money(selected.amountPaise)} · {selected.bookingTitle || ''}</p></div><button className="secondary-button" onClick={() => setSelected(null)}>Close</button></div>
      <img src={selected.screenshotUrl} alt="Uploaded payment screenshot" style={{ maxWidth: '100%', maxHeight: '65vh', objectFit: 'contain' }} />
      <p>Submitted {new Date(selected.submittedAt).toLocaleString()} · Attempt {selected.attemptNumber} · Booking status {selected.bookingStatus}</p>
      <h3>Attempt history</h3>{(selected.history || []).map((attempt) => <p key={attempt.id}>#{attempt.attemptNumber} · {attempt.status} · {attempt.rejectionReason || ''}</p>)}
      {selected.status === 'PENDING_REVIEW' && canManage && <div className="pagination-actions"><button className="primary-button" onClick={() => approve(selected)}>Approve payment</button><button className="secondary-button" onClick={() => reject(selected)}>Reject with reason</button></div>}
    </div>}
  </>;
}
