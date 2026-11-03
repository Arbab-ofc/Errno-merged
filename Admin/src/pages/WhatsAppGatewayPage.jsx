import { useCallback, useEffect, useState } from "react";
import { Activity, Link2, LogOut, Power, RefreshCw, Unplug } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { api } from "../services/api";
import { PageHeader } from "../components/PageHeader";
import { StatePanel } from "../components/StatePanel";

export function WhatsAppGatewayPage() {
  const { user, admin } = useAuth();
  const [status, setStatus] = useState(null);
  const [qr, setQr] = useState(null);
  const [monitoring, setMonitoring] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const canConnect = admin?.permissions?.includes("whatsapp.connect");
  const canManage = admin?.permissions?.includes("whatsapp.manage");
  const canMonitor = admin?.permissions?.includes("whatsapp.monitor");
  const refresh = useCallback(async () => {
    setError("");
    try {
      const result = await api.whatsappStatus(user);
      setStatus(result);
      if (result.status === "QR_REQUIRED") {
        const current = await api.whatsappQr(user).catch(() => null);
        setQr(current?.qrDataUrl ? current : null);
      } else setQr(null);
      if (canMonitor) setMonitoring(await api.whatsappMonitoring(user));
    } catch (e) { setError(e.message); }
  }, [user, canMonitor]);
  useEffect(() => { refresh(); const timer = setInterval(refresh, 4000); return () => clearInterval(timer); }, [refresh]);

  async function action(fn, confirmMessage) {
    if (confirmMessage && !window.confirm(confirmMessage)) return;
    setBusy(true); setError("");
    try { await fn(user); await refresh(); } catch (e) { setError(e.message); } finally { setBusy(false); }
  }

  return <>
    <PageHeader title="WhatsApp Gateway" description="Pair and monitor ERRNO’s QR linked WhatsApp session." onRefresh={refresh} />
    {error && <StatePanel tone="error" title="Gateway request failed" detail={error} actionLabel="Retry" onAction={refresh} />}
    {!status && !error && <StatePanel loading title="Loading WhatsApp status" detail="Checking the private gateway through the ERRNO API." />}
    {status && <>
      <section className="recent-panel pricing-panel">
        <div className="panel-heading"><div><h2>Connection overview</h2><p>Last updated {status.lastHeartbeatAt ? new Date(status.lastHeartbeatAt).toLocaleString() : "not reported"}</p></div><span className={"status-badge " + (status.status === "CONNECTED" ? "active" : "")}>{status.status}</span></div>
        <div className="pricing-settings">
          <div><b>WhatsApp number</b><p>{status.account?.phoneMasked ? `•••• ${status.account.phoneMasked}` : "Not connected"}</p></div>
          <div><b>Account name</b><p>{status.account?.displayName || "Not available"}</p></div>
          <div><b>Connected</b><p>{status.connectedAt ? new Date(status.connectedAt).toLocaleString() : "—"}</p></div>
          <div><b>Disconnected</b><p>{status.disconnectedAt ? new Date(status.disconnectedAt).toLocaleString() : "—"}</p></div>
          <div><b>Gateway health</b><p>{status.status === "ERROR" ? "Error" : "Responding"}</p></div>
          <div><b>Last error</b><p>{status.lastError || "None"}</p></div>
        </div>
        <div className="pricing-actions">
          {canConnect && status.status !== "CONNECTED" && <button disabled={busy} onClick={() => action(api.whatsappConnect)}><Link2 size={15} />Connect / reconnect</button>}
          {canManage && status.status === "CONNECTED" && <button className="secondary" disabled={busy} onClick={() => action(api.whatsappDisconnect)}><Unplug size={15} />Disconnect</button>}
          {canManage && <button className="danger" disabled={busy} onClick={() => action(api.whatsappLogout, "Unlink WhatsApp and permanently remove the saved pairing credentials?")}><LogOut size={15} />Logout / unlink</button>}
          {canConnect && status.status === "QR_REQUIRED" && <button className="secondary" disabled={busy} onClick={() => action(api.whatsappConnect)}><RefreshCw size={15} />Regenerate QR</button>}
        </div>
      </section>
      {status.status === "QR_REQUIRED" && <section className="recent-panel pricing-panel"><div className="panel-heading"><div><h2>Scan to pair</h2><p>Scan with the ERRNO WhatsApp account. The code expires automatically.</p></div></div>
        {qr?.qrDataUrl ? <div className="whatsapp-qr"><img src={qr.qrDataUrl} alt="WhatsApp pairing QR code" /><p>Expires {qr.expiresAt ? new Date(qr.expiresAt).toLocaleTimeString() : "soon"}</p></div> : <p>{canConnect ? "Waiting for a fresh pairing QR…" : "Your account does not have whatsapp.connect permission to view a pairing QR."}</p>}
      </section>}
      {canMonitor && <section className="recent-panel pricing-panel"><div className="panel-heading"><div><h2><Activity size={16} /> OTP delivery monitoring</h2><p>Only request and outcome metadata is retained; OTP content is never shown.</p></div></div>
        <div className="presence-metrics">{Object.entries(monitoring?.counts || {}).map(([key, value]) => <div key={key}><b>{value}</b><span>{key.replaceAll("_", " ")}</span></div>)}</div>
        <div className="pricing-table-wrap"><table className="pricing-table"><thead><tr><th>Event</th><th>Outcome</th><th>Recipient</th><th>Message ID</th><th>Time</th></tr></thead><tbody>{(monitoring?.events || []).map((event, index) => <tr key={`${event.created_at}-${index}`}><td>{event.event_type}</td><td>{event.outcome}</td><td>{event.destination_suffix ? `•••• ${event.destination_suffix}` : "—"}</td><td>{event.message_id || "—"}</td><td>{new Date(event.created_at).toLocaleString()}</td></tr>)}</tbody></table></div>
      </section>}
    </>}
  </>;
}
