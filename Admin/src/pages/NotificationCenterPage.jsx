import { useCallback, useEffect, useState } from "react";
import { Bell, RefreshCw, CheckCheck, RotateCcw } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { api } from "../services/api";
import { PageHeader } from "../components/PageHeader";
import { StatePanel } from "../components/StatePanel";

export function NotificationCenterPage() {
  const { user, admin } = useAuth();
  const [items, setItems] = useState([]); const [delivery, setDelivery] = useState(null);
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const canAudit = (admin?.permissions || []).includes("notifications.audit");
  const canManage = (admin?.permissions || []).includes("notifications.manage");
  const load = useCallback(async () => { setBusy(true); setError(""); try {
    const [inbox, status] = await Promise.all([api.notificationInbox(user), canAudit ? api.notificationDelivery(user) : Promise.resolve(null)]);
    setItems(inbox.items || []); setDelivery(status);
  } catch (e) { setError(e.message || "Unable to load notifications."); } finally { setBusy(false); } }, [user, canAudit]);
  useEffect(() => { load(); }, [load]);
  async function markAll() { await api.markAllNotificationsRead(user); await load(); }
  async function retry(id) { await api.retryNotification(user, id); await load(); }
  return <section className="page-stack"><PageHeader eyebrow="OPERATIONS" title="Notifications" description="Operational alerts and push delivery status." actions={<button className="button-secondary" onClick={load}><RefreshCw size={15}/> Refresh</button>} />
    {error && <StatePanel tone="error" title="Notifications unavailable" detail={error} actionLabel="Retry" onAction={load}/>}
    {!error && <><div className="panel"><div className="panel-heading"><h2><Bell size={17}/> Admin inbox</h2><button className="button-secondary" onClick={markAll}><CheckCheck size={15}/> Mark all read</button></div>
      {busy ? <p>Loading…</p> : items.length === 0 ? <p>No operational notifications.</p> : items.map((item) => <article className="notification-row" key={item.id}><div><b>{item.title}</b><p>{item.body}</p><small>{item.eventType} · {new Date(item.createdAt).toLocaleString()}</small></div>{!item.readAt && <button className="button-secondary" onClick={async()=>{await api.markNotificationRead(user,item.id);await load();}}>Mark read</button>}</article>)}
    </div>{canAudit && <div className="panel"><div className="panel-heading"><h2>Push delivery monitoring</h2><small>FCM acceptance does not confirm device display or receipt.</small></div>
      <pre>{JSON.stringify(delivery?.queue || {}, null, 2)}</pre><p>Oldest queued age: {delivery?.queueLatencySeconds ?? "—"} seconds · Active device tokens: {delivery?.activeDevices ?? "—"} · Invalid FCM tokens: {delivery?.invalidTokens ?? "—"}</p>
      {(delivery?.recentAttempts || []).map((attempt, i) => <article className="notification-row" key={`${attempt.notificationId}-${i}`}><div><b>{attempt.status}</b><p>{attempt.errorCode || "Provider accepted request"} · {attempt.notificationId}</p></div>{canManage && attempt.status === "failed" && <button className="button-secondary" onClick={()=>retry(attempt.outboxId)}><RotateCcw size={15}/> Retry</button>}</article>)}
    </div>}</>}
  </section>;
}
