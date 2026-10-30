import { useCallback } from "react";
import { Activity, BriefcaseBusiness, CheckCheck, Store, Users } from "lucide-react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useAuth } from "../auth/AuthContext";
import { api } from "../services/api";
import { useResource } from "../hooks/useResource";
import { PageHeader } from "../components/PageHeader";
import { LoadingRows, StatePanel } from "../components/StatePanel";

const number = (value) => new Intl.NumberFormat("en-IN").format(value || 0);

export function DashboardPage() {
  const { user } = useAuth();
  const loader = useCallback((signal) => api.dashboard(user, signal), [user]);
  const { data, loading, error, retry } = useResource(loader);
  if (loading && !data) return <><PageHeader title="Overview" description="Live totals from ERRNO users, shops, jobs and applications." onRefresh={retry} refreshing /><LoadingRows rows={4} /></>;
  if (error) return <><PageHeader title="Overview" description="Live totals from ERRNO users, shops, jobs and applications." onRefresh={retry} /><StatePanel title="Dashboard data is unavailable" detail={error.message} actionLabel="Retry" onAction={retry} /></>;

  const metrics = data?.metrics;
  const cards = [
    { label: "Total users", value: metrics.total_users, icon: Users, detail: `${number(metrics.total_workers)} workers · ${number(metrics.total_shop_owners)} shop owners` },
    { label: "Shop locations", value: metrics.total_shops, icon: Store, detail: "Canonical shops table" },
    { label: "Total jobs", value: metrics.total_jobs, icon: BriefcaseBusiness, detail: `${number(metrics.active_jobs)} active · ${number(metrics.completed_jobs)} completed` },
    { label: "Applications", value: metrics.total_applications, icon: Activity, detail: "Recorded worker applications" },
  ];

  return <>
    <PageHeader title="Overview" description="Live totals from ERRNO users, shops, jobs and applications." onRefresh={retry} refreshing={loading} />
    <section className="metric-grid live-metrics" aria-label="Live platform totals">{cards.map(({ label, value, icon: Icon, detail }) => <article className="metric-panel" key={label}><div className="metric-panel-top"><span>{label}</span><i><Icon size={17} /></i></div><strong>{number(value)}</strong><small>{detail}</small></article>)}</section>
    <section className="dashboard-grid">
      <article className="chart-panel"><div className="panel-heading"><div><h2>Registrations</h2><p>New user records · last 7 days</p></div><span className="live-indicator"><i /> LIVE</span></div><div className="chart-area"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data.registrations_by_day} margin={{ top: 12, right: 12, left: -20, bottom: 0 }}><defs><linearGradient id="registrationsFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#a7d84e" stopOpacity={0.26} /><stop offset="95%" stopColor="#a7d84e" stopOpacity={0.01} /></linearGradient></defs><CartesianGrid stroke="#edf0eb" vertical={false} /><XAxis dataKey="date" tickFormatter={(value) => new Date(value + "T00:00:00").toLocaleDateString("en-IN", { weekday: "short" })} axisLine={false} tickLine={false} tick={{ fill: "#89938a", fontSize: 11 }} /><YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: "#89938a", fontSize: 11 }} /><Tooltip labelFormatter={(value) => new Date(value + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short" })} /><Area type="monotone" dataKey="total" stroke="#698b3e" strokeWidth={2.4} fill="url(#registrationsFill)" /></AreaChart></ResponsiveContainer></div></article>
      <article className="chart-panel"><div className="panel-heading"><div><h2>Job activity</h2><p>New job records · last 7 days</p></div><span className="live-indicator"><i /> LIVE</span></div><div className="chart-area"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data.jobs_by_day} margin={{ top: 12, right: 12, left: -20, bottom: 0 }}><defs><linearGradient id="jobsFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#2c5140" stopOpacity={0.2} /><stop offset="95%" stopColor="#2c5140" stopOpacity={0.01} /></linearGradient></defs><CartesianGrid stroke="#edf0eb" vertical={false} /><XAxis dataKey="date" tickFormatter={(value) => new Date(value + "T00:00:00").toLocaleDateString("en-IN", { weekday: "short" })} axisLine={false} tickLine={false} tick={{ fill: "#89938a", fontSize: 11 }} /><YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: "#89938a", fontSize: 11 }} /><Tooltip labelFormatter={(value) => new Date(value + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short" })} /><Area type="monotone" dataKey="total" stroke="#2c5140" strokeWidth={2.4} fill="url(#jobsFill)" /></AreaChart></ResponsiveContainer></div></article>
    </section>
    <section className="recent-grid"><article className="recent-panel"><div className="panel-heading"><div><h2>Recent registrations</h2><p>Latest account records</p></div><Users size={17} /></div>{data.recent_registrations.length ? data.recent_registrations.map((person) => <div className="recent-row" key={person.id}><span className="mini-avatar">{(person.name || "?")[0].toUpperCase()}</span><div><b>{person.name || "Unnamed user"}</b><small>{person.role || "Role not selected"} · {person.email || person.phone_number || "No contact"}</small></div><time>{person.created_at ? new Date(person.created_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short" }) : "—"}</time></div>) : <div className="small-empty">No user records yet.</div>}</article>
      <article className="recent-panel"><div className="panel-heading"><div><h2>Recent jobs</h2><p>Latest created jobs · status changes are not timestamped in the schema</p></div><CheckCheck size={17} /></div>{data.recent_jobs.length ? data.recent_jobs.map((job) => <div className="recent-row" key={job.id}><span className="job-mini-icon"><BriefcaseBusiness size={15} /></span><div><b>{job.title}</b><small>{job.shop_name || "No shop linked"} · {job.status}</small></div><time>{job.created_at ? new Date(job.created_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short" }) : "—"}</time></div>) : <div className="small-empty">No job records yet.</div>}</article></section>
  </>;
}
