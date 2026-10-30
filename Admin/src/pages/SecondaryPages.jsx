import { useCallback } from "react";
import { useAuth } from "../auth/AuthContext";
import { api } from "../services/api";
import { useResource } from "../hooks/useResource";
import { PageHeader } from "../components/PageHeader";
import { StatePanel } from "../components/StatePanel";

const descriptions = {
  bookings: "Booking records are not part of the canonical ERRNO database contract.",
  categories: "Category administration is not available in the canonical runtime schema.",
  attendance: "Attendance records and validation rules are not defined in the canonical API.",
  ratings: "Ratings are not part of the canonical ERRNO database contract.",
  disputes: "Dispute and support case models have not been defined for the shared backend.",
  notifications: "A notification service and persistence contract have not been defined.",
};

export function UnavailablePage({ name }) {
  return <><PageHeader title={name} description="This module is retained for navigation and is not connected to production data." /><StatePanel title="Unavailable in this release" detail={descriptions[name.toLowerCase()] || "This module has no production API contract."} /></>;
}

export function SystemHealthPage() {
  const loader = useCallback((signal) => api.health(undefined, signal), []);
  const { data, loading, error, retry } = useResource(loader);
  return <><PageHeader title="System health" description="Live response from the shared FastAPI service." onRefresh={retry} refreshing={loading} />
    {loading && !data ? <StatePanel title="Checking API health" detail="Requesting the public health endpoint…" loading /> : error ? <StatePanel title="API is unavailable" detail={error.message} actionLabel="Retry" onAction={retry} tone="denied" /> : <section className="health-panel"><div className="health-led" /><div><h2>{data?.status === "ok" ? "API and database are connected" : "API is responding with a database issue"}</h2><p>{data?.message}</p></div><span className="status-pill success">{data?.database || data?.status}</span></section>}
  </>;
}

export function SettingsPage() {
  const { admin } = useAuth();
  return <><PageHeader title="Settings" description="Administrator access details and local interface preferences." />
    <section className="settings-panel"><div className="settings-heading"><div className="brand-mark">E</div><div><h2>Server permissions</h2><p>Current authorization comes from the FastAPI server.</p></div></div>
      <div className="permission-list">{(admin?.permissions || []).map((permission) => <span key={permission} className="permission-tag">{permission}</span>)}</div>
      <div className="local-preference"><b>Local preferences</b><p>Sidebar and display settings affect this browser only. No user, shop or job records are stored in browser localStorage.</p><span>Preferences are not currently persisted.</span></div>
    </section>
  </>;
}
