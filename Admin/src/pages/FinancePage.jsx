import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { api } from "../services/api";
import { PageHeader } from "../components/PageHeader";
import { StatePanel } from "../components/StatePanel";

const inr = (paise) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format((Number(paise) || 0) / 100);

export function FinancePage() {
  const { user, admin } = useAuth();
  const [data, setData] = useState(null);
  const [payments, setPayments] = useState([]);
  const [refunds, setRefunds] = useState([]);
  const [audit, setAudit] = useState([]);
  const [wallets, setWallets] = useState([]);
  const [withdrawals, setWithdrawals] = useState([]);
  const [methods, setMethods] = useState([]);
  const [reconciliation, setReconciliation] = useState(null);
  const [companyQr, setCompanyQr] = useState(null);
  const [companyQrUrl, setCompanyQrUrl] = useState("");
  const [qrVerified, setQrVerified] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [offset, setOffset] = useState(0);
  const can = new Set(admin?.permissions || []);
  const refresh = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [overview, paymentRows, refundRows, auditRows, walletRows, withdrawalRows, methodRows, reconcile, qrConfig] = await Promise.all([
        api.financeOverview(user), api.financePayments(user, { limit: 50, offset }),
        api.financeRefunds(user, { limit: 50, offset }),
        api.financeAudit(user, { limit: 50, offset }),
        can.has("wallet.read") ? api.financeWallets(user, { limit: 50, offset }) : Promise.resolve({ items: [] }),
        can.has("withdrawals.read") ? api.financeWithdrawals(user) : Promise.resolve([]),
        can.has("wallet.read") ? api.financePayoutMethods(user) : Promise.resolve([]),
        can.has("reconciliation.read") ? api.reconciliation(user) : Promise.resolve(null),
        api.companyPaymentQr(user),
      ]);
      setData(overview); setPayments(paymentRows.items || []); setRefunds(refundRows.items || []); setAudit(auditRows.items || []); setWallets(walletRows.items || []);
      setWithdrawals(withdrawalRows || []); setMethods(methodRows || []); setReconciliation(reconcile);
      setCompanyQr(qrConfig); setCompanyQrUrl(qrConfig.qrAssetUrl || ""); setQrVerified(qrConfig.status === "VERIFIED");
    } catch (e) { setError(e.message || "Finance data could not be loaded."); }
    finally { setLoading(false); }
  }, [user, offset, admin]);
  useEffect(() => { refresh(); }, [refresh]);

  async function reviewWithdrawal(row, status) {
    const reason = window.prompt(`Reason to ${status.toLowerCase()} withdrawal ${row.id}?`);
    if (!reason?.trim()) return;
    try { await api.reviewWithdrawal(user, row.id, { status, reason }); await refresh(); }
    catch (e) { setError(e.message); }
  }
  async function completeWithdrawal(row) {
    const providerPayoutId = window.prompt("Verified provider/bank transfer reference:");
    const reason = window.prompt("Verification note (must refer to checked transfer evidence):");
    if (!providerPayoutId?.trim() || !reason?.trim()) return;
    try { await api.reviewWithdrawal(user, row.id, { status: "COMPLETED", providerPayoutId, reason }); await refresh(); }
    catch (e) { setError(e.message); }
  }
  async function reviewMethod(row) {
    const status = window.confirm(`Verify payout method ending ${row.providerReferenceSuffix}? Confirm only after the independent KYC and ownership check.`) ? "VERIFIED" : "REJECTED";
    const reason = window.prompt("Enter the review reason:");
    if (!reason?.trim()) return;
    try { await api.reviewPayoutMethod(user, row.id, { status, reason }); await refresh(); }
    catch (e) { setError(e.message); }
  }
  async function refund(row) {
    const reason = window.prompt("Refund reason:");
    if (!reason?.trim()) return;
    const amount = window.prompt(`Refund amount in paise (blank for remaining balance):`);
    const body = { paymentId: row.id, reason, idempotencyKey: crypto.randomUUID() };
    if (amount?.trim()) body.amountPaise = Number(amount);
    try { await api.refundPayment(user, body); await refresh(); }
    catch (e) { setError(e.message); }
  }
  async function resolveCash(row) {
    const outcome = window.confirm("Confirm that ERRNO commission was received and reconciled? Choose Cancel to mark as disputed.") ? "RECONCILED" : "DISPUTED";
    const reason = window.prompt("Reconciliation or dispute reason:");
    if (!reason?.trim()) return;
    const body = { outcome, reason };
    if (outcome === "RECONCILED") body.errnoCommissionReceivedPaise = Number(window.prompt("Confirmed ERRNO commission received (paise):") || 0);
    try { await api.resolveCash(user, row.id, body); await refresh(); }
    catch (e) { setError(e.message); }
  }
  async function saveCompanyQr() {
    const reason = window.prompt("Confirm that this is the approved ERRNO YES BANK QR asset and that destination ownership was checked:");
    if (!reason?.trim()) return;
    try { await api.updateCompanyPaymentQr(user, { qrAssetUrl: companyQrUrl, verified: qrVerified, reason }); await refresh(); }
    catch (e) { setError(e.message); }
  }

  if (loading && !data) return <><PageHeader title="Finance & Payments" description="Verified collections, wallet ledger, refunds and settlement operations." /><StatePanel title="Loading finance data" detail="Fetching backend verified financial records…" loading /></>;
  if (error && !data) return <><PageHeader title="Finance & Payments" description="Backend controlled financial operations." onRefresh={refresh} /><StatePanel tone="denied" title="Finance data unavailable" detail={error} actionLabel="Retry" onAction={refresh} /></>;

  const cards = [
    ["Verified collections", data?.verifiedCollectionsPaise, true], ["ERRNO commission net", data?.errnoCommissionNetPaise, true],
    ["Completed-job amount outstanding", data?.outstandingCompletedPaymentsPaise, true], ["Worker payable", data?.workerPayablePaise, true],
    ["Withdrawals pending", data?.withdrawalsPendingPaise, true], ["Refunds total", data?.refundTotalPaise, true],
    ["Cash collections pending reconciliation", data?.cashCollectionsPending, false],
    ["Unmatched provider events", data?.unreconciledWebhookEvents, false], ["Payments failed", data?.paymentFailedCount, false],
  ];
  return <>
    <PageHeader title="Finance & Payments" description="Razorpay collections, append-only worker wallet, withdrawals and cash reconciliation." onRefresh={refresh} refreshing={loading} />
    {error && <div className="inline-error" role="alert">{error}</div>}
    <section className="metric-grid">{cards.map(([label, value, isMoney]) => <article className="metric-card" key={label}><small>{label}</small><strong>{value == null ? "—" : isMoney ? inr(value) : value}</strong></article>)}</section>

    <section className="recent-panel"><div className="panel-heading"><div><h2>Payment transactions</h2><p>Provider verified status · amounts originate from immutable booking pricing snapshots</p></div></div>
      {!can.has("payments.read") ? <StatePanel tone="denied" title="Payments permission required" detail="Your admin grant does not include payments.read." /> : payments.length === 0 ? <div className="small-empty">No payment attempts recorded.</div> : <div className="table-scroll"><table className="data-table"><thead><tr><th>Booking</th><th>Shopkeeper</th><th>Worker</th><th>Amount</th><th>Provider order / payment</th><th>Status</th><th>Action</th></tr></thead><tbody>{payments.map((p) => <tr key={p.id}><td>{p.bookingId}</td><td>{p.shopkeeperId}</td><td>{p.workerId}</td><td>{inr(p.amountPaise)}</td><td>{p.orderId || "—"}<br />{p.paymentId || "—"}</td><td>{p.status}</td><td>{can.has("payments.refund") && p.status === "PAID" ? <button className="secondary-button" onClick={() => refund(p)}>Refund</button> : "—"}</td></tr>)}</tbody></table></div>}
      <div className="pagination-actions"><button className="secondary-button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 50))}>Previous</button><span>Showing {offset + 1}–{offset + payments.length}</span><button className="secondary-button" disabled={payments.length < 50} onClick={() => setOffset(offset + 50)}>Next</button></div>
    </section>

    <section className="recent-panel"><div className="panel-heading"><div><h2>Refund history</h2><p>Refunds are considered complete only after provider confirmation.</p></div></div>
      {refunds.length === 0 ? <div className="small-empty">No refund requests recorded.</div> : <div className="table-scroll"><table className="data-table"><thead><tr><th>Refund</th><th>Payment</th><th>Amount</th><th>Reason</th><th>Provider reference</th><th>Status</th></tr></thead><tbody>{refunds.map((r) => <tr key={r.id}><td>{r.id}</td><td>{r.paymentId}</td><td>{inr(r.amountPaise)}</td><td>{r.reason}</td><td>{r.providerRefundId || "—"}</td><td>{r.status}</td></tr>)}</tbody></table></div>}
    </section>

    <section className="recent-panel"><div className="panel-heading"><div><h2>Financial audit history</h2><p>Administrative actions and provider-confirmed ledger events.</p></div></div>
      {audit.length === 0 ? <div className="small-empty">No financial audit events recorded.</div> : audit.map((row) => <div className="recent-row" key={row.id}><div><b>{row.eventType} · {row.resourceType}</b><small>{row.actorId || "System"} · {row.resourceId} · {row.createdAt ? new Date(row.createdAt).toLocaleString() : ""}</small></div><small>{JSON.stringify(row.details || {})}</small></div>)}
    </section>

    <section className="recent-grid"><article className="recent-panel"><div className="panel-heading"><div><h2>Worker wallets</h2><p>Ledger-derived balance and eligibility</p></div></div>{!can.has("wallet.read") ? <p>Wallet permission required.</p> : wallets.map((w) => <div className="recent-row" key={w.workerId}><div><b>{w.name || w.workerId}</b><small>{w.eligibleCompletedOrders} eligible paid orders · {w.withdrawalEligible ? "eligible" : w.eligibilityReasons?.join("; ")}</small></div><strong>{inr(w.availableBalancePaise)}</strong></div>)}</article>
      <article className="recent-panel"><div className="panel-heading"><div><h2>Withdrawal requests</h2><p>Approval queues external payout; completion requires an independently verified transfer reference.</p></div></div>{!can.has("withdrawals.read") ? <p>Withdrawal permission required.</p> : withdrawals.map((w) => <div className="recent-row" key={w.id}><div><b>{w.workerId}</b><small>{inr(w.amountPaise)} · {w.status}</small></div>{can.has("withdrawals.manage") ? w.status === "PENDING_EXTERNAL_PAYOUT" ? <div><button className="secondary-button" onClick={() => reviewWithdrawal(w, "APPROVED")}>Approve queue</button> <button className="secondary-button" onClick={() => reviewWithdrawal(w, "REJECTED")}>Reject</button></div> : w.status === "APPROVED" ? <button className="secondary-button" onClick={() => completeWithdrawal(w)}>Record verified transfer</button> : null : null}</div>)}</article></section>

    <section className="recent-grid"><article className="recent-panel"><div className="panel-heading"><div><h2>Payout methods and KYC</h2><p>Only provider references are stored; verification is a manual audited admin decision.</p></div></div>{methods.map((m) => <div className="recent-row" key={m.id}><div><b>{m.workerId}</b><small>…{m.providerReferenceSuffix} · {m.status} · KYC {m.kycVerified ? "verified" : "pending"}</small></div>{m.status === "PENDING_VERIFICATION" && can.has("withdrawals.manage") ? <button className="secondary-button" onClick={() => reviewMethod(m)}>Review</button> : null}</div>)}</article>
      <article className="recent-panel"><div className="panel-heading"><div><h2>Cash reconciliation</h2><p>Cash is separate from Razorpay. Reconciled records require both parties and commission evidence.</p></div></div>{reconciliation?.cashCollections?.length ? reconciliation.cashCollections.map((c) => <div className="recent-row" key={c.id}><div><b>{c.bookingId}</b><small>{inr(c.amountPaise)} · {c.status}</small></div>{can.has("reconciliation.manage") ? <button className="secondary-button" onClick={() => resolveCash(c)}>Resolve</button> : null}</div>) : <div className="small-empty">No cash items require reconciliation.</div>}</article></section>

    {can.has("payments.manage") && <section className="recent-panel"><div className="panel-heading"><div><h2>Company UPI QR asset</h2><p>Worker apps display this only after an admin verifies the supplied YES BANK asset. QR scans do not prove payment.</p></div></div><label className="form-field">Approved HTTPS QR image URL<input value={companyQrUrl} onChange={(e) => setCompanyQrUrl(e.target.value)} placeholder="https://approved-assets.example/errno-upi-qr.png" /></label><label className="checkbox-field"><input type="checkbox" checked={qrVerified} onChange={(e) => setQrVerified(e.target.checked)} />I verified the account destination and QR asset</label><p>Current state: {companyQr?.status || "UNCONFIGURED"}</p><button className="primary-button" disabled={!companyQrUrl.startsWith("https://")} onClick={saveCompanyQr}>Save QR configuration</button></section>}
  </>;
}
