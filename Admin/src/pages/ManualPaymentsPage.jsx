import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Activity, ArrowDownUp, Check, CheckCircle2, ChevronLeft, ChevronRight, Clock3, FileImage, Image as ImageIcon, RefreshCw, Search, ShieldCheck, X } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { api } from '../services/api';
import { PageHeader } from '../components/PageHeader';
import '../styles/payments.css';

const money = (paise) => paise == null ? '—' : new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(Number(paise) / 100);
const date = (value) => value ? new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—';
const statuses = ['PENDING_REVIEW', 'APPROVED', 'REJECTED'];
const countStatuses = [...statuses, 'ALL'];

function Status({ value }) { const tone = value === 'APPROVED' ? 'good' : value === 'REJECTED' ? 'bad' : 'pending'; return <span className={`pay-status ${tone}`}><i />{(value || 'UNKNOWN').replaceAll('_', ' ')}</span>; }

export function ManualPaymentsPage() {
  const { user, admin } = useAuth();
  const permissions = admin?.permissions || [];
  const canRead = permissions.includes('payments.read'); const canManage = permissions.includes('payments.manage');
  const [config, setConfig] = useState(null); const [rows, setRows] = useState([]); const [selected, setSelected] = useState(null);
  const [counts, setCounts] = useState({}); const [total, setTotal] = useState(0); const [filter, setFilter] = useState('PENDING_REVIEW');
  const [offset, setOffset] = useState(0); const [merchant, setMerchant] = useState(''); const [upi, setUpi] = useState(''); const [provider, setProvider] = useState('MANUAL_QR');
  const [query, setQuery] = useState(''); const [sort, setSort] = useState('newest'); const [loading, setLoading] = useState(true); const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false); const [error, setError] = useState(''); const [socketConnected, setSocketConnected] = useState(false); const [updatedAt, setUpdatedAt] = useState(null);
  const [action, setAction] = useState(null); const [reason, setReason] = useState(''); const [acting, setActing] = useState(false); const [previewFailed, setPreviewFailed] = useState(false);
  const refreshRef = useRef(null); const closeRef = useRef(null); const previewRetryRef = useRef(null);

  const refresh = useCallback(async (initial = false) => {
    if (!canRead) { setLoading(false); return; }
    if (initial || rows.length === 0) setLoading(true); setError('');
    try {
      const [settings, queue, ...totals] = await Promise.all([
        api.manualPaymentConfig(user), api.manualPayments(user, filter, offset),
        ...countStatuses.map((status) => api.manualPayments(user, status, 0, 1)),
      ]);
      setConfig(settings); setRows(queue.items || []); setTotal(queue.total || 0); setCounts(Object.fromEntries(countStatuses.map((s, i) => [s, totals[i]?.total || 0])));
      setMerchant(settings.merchantName || ''); setUpi(settings.upiId || ''); setProvider(settings.activeProvider || 'MANUAL_QR'); setUpdatedAt(new Date());
      if (selected?.id) { try { const fresh = await api.manualPayment(user, selected.id); setSelected(fresh); setPreviewFailed(false); } catch (e) { if (e.status === 404) setSelected(null); } }
    } catch (e) { setError(e.message || 'Payment data could not be loaded.'); }
    finally { setLoading(false); }
  }, [user, filter, offset, selected?.id, canRead]);
  useEffect(() => { refreshRef.current = refresh; }, [refresh]);
  useEffect(() => { refresh(true); }, [refresh]);

  useEffect(() => {
    if (!canRead) return undefined;
    let active = true; let socket; let retryTimer; let fallbackTimer; let delay = 1000; let connecting = false;
    const fallback = () => { if (!fallbackTimer) fallbackTimer = window.setInterval(() => refreshRef.current?.(), 30000); };
    const stopFallback = () => { if (fallbackTimer) window.clearInterval(fallbackTimer); fallbackTimer = null; };
    const connect = async () => {
      if (!active || connecting || (socket && socket.readyState <= 1)) return; connecting = true;
      try {
        socket = await api.paymentSocket(user, 'admin'); if (!active) { socket.close(); return; }
        socket.onopen = () => { connecting = false; delay = 1000; setSocketConnected(true); stopFallback(); refreshRef.current?.(); };
        socket.onmessage = (event) => { try { const data = JSON.parse(event.data); if (data.version === 1 && data.eventType?.startsWith('manual_payment.')) refreshRef.current?.(); } catch { /* Ignore unsupported event frames. */ } };
        socket.onclose = () => { connecting = false; setSocketConnected(false); fallback(); if (active) { retryTimer = window.setTimeout(connect, delay); delay = Math.min(delay * 2, 30000); } };
        socket.onerror = () => socket?.close();
      } catch { connecting = false; setSocketConnected(false); fallback(); if (active) { retryTimer = window.setTimeout(connect, delay); delay = Math.min(delay * 2, 30000); } }
    };
    connect(); return () => { active = false; clearTimeout(retryTimer); stopFallback(); socket?.close(); setSocketConnected(false); };
  }, [user, canRead]);

  useEffect(() => {
    if (!selected && !action) return undefined;
    const dialog = document.querySelector(action ? '.confirm-layer [role="alertdialog"]' : '.payment-drawer[role="dialog"]');
    (action ? dialog : closeRef.current)?.focus();
    const onKey = (event) => {
      if (event.key === 'Escape' && !acting) { setSelected(null); setAction(null); }
      if (event.key === 'Tab' && dialog) {
        const focusable = [...dialog.querySelectorAll('button:not(:disabled),a[href],input:not(:disabled),textarea:not(:disabled),select:not(:disabled),[tabindex]:not([tabindex="-1"])')].filter((el) => el.offsetParent !== null);
        if (!focusable.length) { event.preventDefault(); dialog.focus(); return; }
        const first = focusable[0]; const last = focusable[focusable.length - 1];
        if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog)) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    };
    window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey);
  }, [selected, action, acting]);
  const filtered = useMemo(() => rows.filter((row) => [row.id, row.bookingId, row.shopkeeperName, row.shopkeeperId].join(' ').toLowerCase().includes(query.toLowerCase())).sort((a, b) => sort === 'oldest' ? new Date(a.submittedAt) - new Date(b.submittedAt) : new Date(b.submittedAt) - new Date(a.submittedAt)), [rows, query, sort]);

  async function saveSettings() {
    setSaving(true); setError('');
    try { await api.updateManualPaymentConfig(user, { activeProvider: provider, merchantName: merchant.trim() || null, upiId: upi.trim() || null }); await refresh(); }
    catch (e) { setError(e.message || 'Settings could not be saved.'); } finally { setSaving(false); }
  }
  async function upload(file) {
    if (!file) return; if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024) { setError('Choose a JPG, PNG or WebP image under 5 MB.'); return; }
    setUploading(true); setError(''); try { await api.uploadPaymentQr(user, file); await refresh(); } catch (e) { setError(e.message || 'QR upload failed.'); } finally { setUploading(false); }
  }
  async function openReview(row) { setError(''); setPreviewFailed(false); previewRetryRef.current = null; try { setSelected(await api.manualPayment(user, row.id)); } catch (e) { setError(e.message || 'Submission details are unavailable.'); } }
  async function retryPreview(automatic = false) { if (!selected) return; if (automatic && previewRetryRef.current === selected.id) { setPreviewFailed(true); return; } if (automatic) previewRetryRef.current = selected.id; else previewRetryRef.current = null; setPreviewFailed(true); try { const fresh = await api.manualPayment(user, selected.id); setSelected(fresh); setPreviewFailed(false); } catch (e) { setError(e.message || 'A fresh screenshot link is unavailable.'); setPreviewFailed(true); } }
  async function submitDecision() {
    if (!action || !selected || acting) return; if (action === 'reject' && !reason.trim()) return;
    setActing(true); setError('');
    try { if (action === 'approve') await api.approveManualPayment(user, selected.id); else await api.rejectManualPayment(user, selected.id, reason.trim()); setSelected(null); setAction(null); setReason(''); await refresh(true); }
    catch (e) { setError(e.message || `Payment could not be ${action}d.`); await refresh(); }
    finally { setActing(false); }
  }
  const dirty = Boolean(config && (merchant !== (config.merchantName || '') || upi !== (config.upiId || '') || provider !== (config.activeProvider || 'MANUAL_QR')));

  if (!canRead) return <main className="payments-page"><PageHeader title="Manual Payment Verification" description="Review submitted payment evidence and manage payment configuration." /><section className="payments-error"><ShieldCheck /><div><h2>Payment access required</h2><p>Your account needs the <code>payments.read</code> permission to view payment submissions.</p></div></section></main>;
  return <main className="payments-page">
    <PageHeader eyebrow="FINANCE OPERATIONS" title="Manual Payment Verification" description="Review shopkeeper payment evidence and manage the manual payment channel." onRefresh={() => refresh(true)} refreshing={loading} />
    {error && <div className="payments-alert" role="alert"><span>{error}</span><button className="pay-icon-button" onClick={() => refresh(true)} aria-label="Retry loading"><RefreshCw size={16} /></button></div>}

    <section className="payment-overview" aria-label="Submission overview">
      <article className="payment-kpi primary-kpi"><span>Awaiting review</span><strong>{counts.PENDING_REVIEW ?? '—'}</strong><small><i /> {counts.PENDING_REVIEW ? 'Needs a decision' : 'Queue is clear'}</small><Clock3 className="kpi-icon" size={19} /></article>
      <article className="payment-kpi"><span>Approved</span><strong>{counts.APPROVED ?? '—'}</strong><small>All recorded submissions</small><CheckCircle2 className="kpi-icon" size={19} /></article>
      <article className="payment-kpi"><span>Rejected</span><strong>{counts.REJECTED ?? '—'}</strong><small>Includes resubmitted attempts</small><X className="kpi-icon" size={19} /></article>
      <article className="payment-kpi"><span>Total submissions</span><strong>{counts.ALL ?? '—'}</strong><small>Across all review states</small><FileImage className="kpi-icon" size={19} /></article>
    </section>

    <section className="payment-config-layout">
      <div className="payment-surface payment-config-form">
        <div className="payment-section-head"><div><span className="section-kicker">CHANNEL SETTINGS</span><h2>Payment configuration</h2><p>Settings apply to new payment obligations; existing records keep their original provider.</p></div><span className={`config-state ${config?.configured ? 'is-ready' : ''}`}><i />{config?.configured ? 'Configured' : 'Setup needed'}</span></div>
        <div className="config-fields">
          <label>Payment method<select value={provider} disabled={!canManage || !config} onChange={(e) => setProvider(e.target.value)}><option value="MANUAL_QR">Manual QR payment</option><option value="RAZORPAY">Razorpay</option></select></label>
          <label>Merchant display name<input value={merchant} disabled={!canManage} onChange={(e) => setMerchant(e.target.value)} placeholder="ERRNO Private Limited" /></label>
          <label className="field-wide">Company UPI ID <span className="optional-label">Optional</span><input value={upi} disabled={!canManage} onChange={(e) => setUpi(e.target.value)} placeholder="payments@examplebank" /></label>
        </div>
        <div className="config-actions"><span className={dirty ? 'unsaved-note' : 'saved-note'}>{dirty ? 'Unsaved changes' : 'Configuration is up to date'}</span>{canManage && <><button className="pay-button quiet" disabled={!dirty || saving} onClick={() => { setMerchant(config?.merchantName || ''); setUpi(config?.upiId || ''); setProvider(config?.activeProvider || 'MANUAL_QR'); }}>Cancel</button><button className="pay-button solid" disabled={!dirty || saving} onClick={saveSettings}>{saving ? 'Saving…' : 'Save configuration'}</button></>}</div>
        {!canManage && <p className="permission-note">Read-only access · payment configuration controls are disabled.</p>}
      </div>
      <aside className="payment-surface qr-panel"><div className="payment-section-head"><div><span className="section-kicker">PAYMENT DESTINATION</span><h2>Company QR code</h2><p>Shopkeepers use this QR to make manual payments.</p></div><span className={`config-state ${config?.qrImageUrl ? 'is-ready' : ''}`}><i />{config?.qrImageUrl ? 'Active' : 'Not set'}</span></div>
        {config?.qrImageUrl ? <a className="qr-preview" href={config.qrImageUrl} target="_blank" rel="noreferrer" aria-label="Open current payment QR image"><img src={config.qrImageUrl} alt="Current company payment QR" /></a> : <div className="qr-placeholder"><ImageIcon size={25} /><span>No QR image uploaded</span></div>}
        <label className={`upload-zone ${!canManage || uploading ? 'disabled' : ''}`}><input type="file" accept="image/jpeg,image/png,image/webp" disabled={!canManage || uploading} onChange={(e) => { upload(e.target.files?.[0]); e.target.value = ''; }} /><span className="upload-mark"><FileImage size={17} /></span><span><b>{uploading ? 'Uploading securely…' : config?.qrImageUrl ? 'Replace QR image' : 'Upload QR image'}</b><small>JPG, PNG or WebP · up to 5 MB</small></span>{canManage && <span className="upload-action">Browse</span>}</label>
      </aside>
    </section>

    <section className="payment-surface review-queue">
      <div className="payment-section-head queue-head"><div><span className="section-kicker">SUBMISSION QUEUE</span><h2>Payment submissions</h2><p>Select a submission to inspect its evidence and review history.</p></div><div className={`socket-state ${socketConnected ? 'connected' : ''}`}><i />{socketConnected ? 'Live updates connected' : 'Live updates reconnecting'}</div></div>
      <div className="queue-toolbar"><div className="queue-tabs" role="tablist" aria-label="Filter by payment status">{[['PENDING_REVIEW','Pending'],['APPROVED','Approved'],['REJECTED','Rejected'],['ALL','All']].map(([value,label]) => <button key={value} role="tab" aria-selected={filter === value} className={filter === value ? 'active' : ''} onClick={() => { setOffset(0); setFilter(value); }}>{label}<b>{counts[value]}</b></button>)}</div>
        <div className="queue-tools"><label className="queue-search"><Search size={16} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search ID, booking or shopkeeper" aria-label="Search submissions on this page" /></label><button className="pay-button quiet sort-button" onClick={() => setSort(sort === 'newest' ? 'oldest' : 'newest')}><ArrowDownUp size={15} />{sort === 'newest' ? 'Newest first' : 'Oldest first'}</button></div></div>
      {loading && !rows.length ? <div className="payment-skeleton" aria-label="Loading submissions"><i /><i /><i /><i /></div> : error && !rows.length ? <div className="payment-empty"><h3>Queue could not be loaded</h3><p>Retry to fetch the latest payment submissions.</p><button className="pay-button solid" onClick={() => refresh(true)}>Retry</button></div> : !filtered.length ? <div className="payment-empty"><span className="empty-icon"><FileImage size={20} /></span><h3>{query ? 'No matching submissions' : filter === 'PENDING_REVIEW' ? 'Nothing waiting for review' : 'No submissions in this view'}</h3><p>{query ? 'Try another booking ID, submission ID or shopkeeper name.' : 'New payment screenshots will appear here when submitted.'}</p></div> : <>
        <div className="payment-table-wrap"><table className="payment-table"><thead><tr><th>Submission</th><th>Shopkeeper</th><th>Booking / job</th><th>Amount</th><th>Submitted</th><th>Attempt</th><th>Status</th><th><span className="sr-only">Action</span></th></tr></thead><tbody>{filtered.map((row) => <tr key={row.id} onDoubleClick={() => openReview(row)}><td data-label="Submission"><button className="submission-link" onClick={() => openReview(row)}><span className="submission-mark"><FileImage size={15} /></span><span><b>{row.id.slice(0, 10)}</b><small>{row.id}</small></span></button></td><td data-label="Shopkeeper"><b className="shop-name">{row.shopkeeperName || 'Shopkeeper'}</b><small className="cell-sub">{row.shopkeeperId}</small></td><td data-label="Booking / job"><b>{row.bookingTitle || 'Booking'}</b><small className="cell-sub">{row.bookingId}</small></td><td data-label="Amount" className="amount-cell">{money(row.amountPaise)}</td><td data-label="Submitted">{date(row.submittedAt)}</td><td data-label="Attempt"><span className="attempt-count">{row.attemptNumber}</span></td><td data-label="Status"><Status value={row.status} /></td><td data-label="Action"><button className="pay-button outline" onClick={() => openReview(row)}>Review</button></td></tr>)}</tbody></table></div>
        <div className="queue-pagination"><span>Showing {total ? offset + 1 : 0}–{offset + rows.length} of {total}</span><div><button className="pay-icon-button" aria-label="Previous page" disabled={!offset || loading} onClick={() => setOffset(Math.max(0, offset - 50))}><ChevronLeft size={17} /></button><button className="pay-icon-button" aria-label="Next page" disabled={offset + rows.length >= total || loading} onClick={() => setOffset(offset + 50)}><ChevronRight size={17} /></button></div></div>
      </>}
      {updatedAt && <span className="queue-updated">Updated {date(updatedAt)}</span>}
    </section>

    {selected && <div className="payment-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget && !acting) setSelected(null); }}><section className="payment-drawer" role="dialog" aria-modal="true" aria-labelledby="review-title"><div className="drawer-head"><div><span className="section-kicker">PAYMENT REVIEW</span><h2 id="review-title">Submission details</h2><p>{selected.id}</p></div><button ref={closeRef} className="pay-icon-button" aria-label="Close review" onClick={() => setSelected(null)}><X size={19} /></button></div>
      <div className="drawer-scroll"><div className="review-amount"><div><span>Submitted amount</span><strong>{money(selected.amountPaise)}</strong></div><Status value={selected.status} /></div>
        <div className="review-facts"><div><span>Shopkeeper</span><b>{selected.shopkeeperName || 'Shopkeeper'}</b><small>{selected.shopkeeperId}</small></div><div><span>Booking / job</span><b>{selected.bookingTitle || 'Booking'}</b><small>{selected.bookingId}</small></div><div><span>Submitted</span><b>{date(selected.submittedAt)}</b></div><div><span>Attempt</span><b>{selected.attemptNumber}</b></div><div><span>Booking status</span><b>{selected.bookingStatus || '—'}</b></div><div><span>Reviewed</span><b>{selected.reviewedAt ? date(selected.reviewedAt) : 'Not reviewed'}</b><small>{selected.reviewedBy || ''}</small></div></div>
        <div className="evidence-heading"><div><h3>Payment evidence</h3><p>Private image link expires after five minutes.</p></div>{selected.screenshotUrl && <a className="pay-button quiet" href={selected.screenshotUrl} target="_blank" rel="noreferrer">Open full size</a>}</div>
        <div className="evidence-frame">{previewFailed ? <div className="preview-error"><ImageIcon /><b>Screenshot link expired or unavailable</b><button className="pay-button outline" onClick={() => retryPreview(false)}>Fetch a fresh link</button></div> : <img src={selected.screenshotUrl} alt="Shopkeeper submitted payment screenshot" onError={() => retryPreview(true)} />}</div>
        <div className="history-block"><div className="evidence-heading"><div><h3>Submission history</h3><p>Previous attempts and reviewer decisions</p></div></div>{(selected.history || []).length ? <ol className="attempt-history">{selected.history.map((item) => <li key={item.id}><span className="history-node" /><div><div className="history-title"><b>Attempt {item.attemptNumber}</b><Status value={item.status} /></div><small>{date(item.submittedAt)}{item.reviewedBy ? ` · Reviewed by ${item.reviewedBy}` : ''}</small>{item.rejectionReason && <p className="rejection-note">“{item.rejectionReason}”</p>}</div></li>)}</ol> : <p className="muted-copy">No prior attempt history is available.</p>}</div>
      </div>
      {selected.status === 'PENDING_REVIEW' && canManage ? <div className="drawer-actions"><button className="pay-button reject" disabled={acting} onClick={() => { setAction('reject'); setReason(''); }}>Reject submission</button><button className="pay-button approve" disabled={acting} onClick={() => setAction('approve')}><Check size={16} />Approve payment</button></div> : <div className="drawer-finalized"><ShieldCheck size={16} />This submission has a final decision. Review actions are disabled.</div>}
      </section></div>}
    {action && selected && <div className="payment-overlay confirm-layer"><section className="decision-dialog" tabIndex="-1" role="alertdialog" aria-modal="true" aria-labelledby="decision-title" aria-describedby="decision-description"><button className="dialog-close pay-icon-button" aria-label="Cancel decision" disabled={acting} onClick={() => setAction(null)}><X size={18} /></button><span className={`decision-icon ${action}`} >{action === 'approve' ? <CheckCircle2 /> : <X />}</span><h2 id="decision-title">{action === 'approve' ? 'Approve this payment?' : 'Reject this submission?'}</h2><p id="decision-description">{action === 'approve' ? `Confirm the ${money(selected.amountPaise)} submission for booking ${selected.bookingId}. Approval records the payment and worker earnings.` : `This changes the payment back to pending and lets the shopkeeper submit a replacement screenshot.`}</p>
        <div className="decision-recap"><span>{selected.shopkeeperName || selected.shopkeeperId}</span><b>{money(selected.amountPaise)}</b></div>
        {action === 'reject' && <label className="decision-reason">Rejection reason<textarea autoFocus rows="3" maxLength="500" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Explain what needs to be corrected" required /><small>{reason.trim().length}/500 · Required</small></label>}
        <div className="decision-actions"><button className="pay-button quiet" disabled={acting} onClick={() => setAction(null)}>Cancel</button><button className={`pay-button ${action === 'approve' ? 'approve' : 'reject'}`} disabled={acting || (action === 'reject' && !reason.trim())} onClick={submitDecision}>{acting ? 'Processing…' : action === 'approve' ? 'Confirm approval' : 'Confirm rejection'}</button></div>
      </section></div>}
  </main>;
}
