import { useCallback, useState, useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Search } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { api } from "../services/api";
import { useResource } from "../hooks/useResource";
import { DataTable, Pagination } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { LoadingRows, StatePanel } from "../components/StatePanel";

const PAGE_SIZE = 20;
const transitions = {
  open: ["cancelled"],
  assigned: ["cancelled"],
  in_progress: [],
  inProgress: [],
  completed: [],
  cancelled: [],
};
const dateLabel = (value) => value ? new Date(value).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—";

export function JobsPage() {
  const { user, admin } = useAuth();
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);
  const [actionError, setActionError] = useState("");
  const [savingId, setSavingId] = useState(null);
  useEffect(() => { const timer = setTimeout(() => { setQuery(search.trim()); setOffset(0); }, 250); return () => clearTimeout(timer); }, [search]);
  const loader = useCallback((signal) => {
    const params = { limit: PAGE_SIZE, offset };
    if (query) params.q = query;
    if (status) params.status_filter = status;
    return api.jobs(user, params, signal);
  }, [user, query, status, offset]);
  const { data, loading, error, retry } = useResource(loader);
  const canManage = admin?.permissions?.includes("jobs.manage");

  const updateStatus = async (jobId, nextStatus) => {
    setSavingId(jobId); setActionError("");
    try { await api.updateJobStatus(user, jobId, nextStatus); retry(); }
    catch (reason) { setActionError(reason.message); }
    finally { setSavingId(null); }
  };
  const columns = [
    { key: "title", label: "Job", render: (row) => <div className="person-cell"><Link className="job-title-link" to={`/admin/jobs/${row.id}`}>{row.title}</Link><small>{row.shop_name || "No shop linked"}</small></div> },
    { key: "owner_name", label: "Shop owner" },
    { key: "status", label: "Status", render: (row) => <span className={"status-pill " + (row.status === "completed" ? "success" : row.status === "cancelled" ? "muted" : "warning")}>{row.status.replace("_", " ")}</span> },
    { key: "application_count", label: "Applications" },
    { key: "created_at", label: "Created", render: (row) => dateLabel(row.created_at) },
    { key: "actions", label: "Admin action", render: (row) => canManage && transitions[row.status]?.length ? <select aria-label={`Change status for ${row.title}`} className="row-action-select" disabled={savingId === row.id} value="" onChange={(event) => event.target.value && updateStatus(row.id, event.target.value)}><option value="">Change status…</option>{transitions[row.status].map((value) => <option key={value} value={value}>{value.replace("_", " ")}</option>)}</select> : <span className="quiet-text">{canManage ? "Final status" : "Read only"}</span> },
  ];
  return <>
    <PageHeader title="Jobs" description="All job records, current lifecycle status and linked applications." onRefresh={retry} refreshing={loading} />
    <div className="toolbar-row"><label className="search-field"><Search size={16} /><input aria-label="Search jobs" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search title, shop or owner" /></label>
      <select className="filter-select" aria-label="Job status" value={status} onChange={(event) => { setStatus(event.target.value); setOffset(0); }}><option value="">All statuses</option>{["open", "assigned", "in_progress", "completed", "cancelled"].map((value) => <option key={value}>{value}</option>)}</select>
      <span className="result-total">{data?.total ?? "—"} jobs</span></div>
    {actionError && <p className="inline-error" role="alert">{actionError}</p>}
    <section className="table-panel">{error ? <StatePanel title="Could not load jobs" detail={error.message} actionLabel="Retry" onAction={retry} /> : loading && !data ? <LoadingRows /> : <DataTable columns={columns} rows={data?.items || []} emptyTitle="No jobs found" emptyDetail="No canonical job records match this search." />}
      {data && <Pagination total={data.total} limit={data.limit} offset={data.offset} onChange={setOffset} />}</section>
  </>;
}

export function JobDetailPage() {
  const { jobId } = useParams();
  const { user, admin } = useAuth();
  const [nextStatus, setNextStatus] = useState("");
  const [actionError, setActionError] = useState("");
  const [saving, setSaving] = useState(false);
  const loader = useCallback((signal) => api.job(user, jobId, signal), [user, jobId]);
  const { data, loading, error, retry } = useResource(loader);
  if (loading && !data) return <><PageHeader title="Job details" /><LoadingRows /></>;
  if (error) return <><PageHeader title="Job details" /><StatePanel title="Could not load job" detail={error.message} actionLabel="Retry" onAction={retry} /></>;
  if (!data) return null;
  const options = transitions[data.status] || [];
  const submit = async () => {
    setSaving(true); setActionError("");
    try { await api.updateJobStatus(user, jobId, nextStatus); setNextStatus(""); retry(); }
    catch (reason) { setActionError(reason.message); }
    finally { setSaving(false); }
  };
  return <>
    <PageHeader title="Job details" description="Job record and application history." onRefresh={retry} />
    <Link to="/admin/jobs" className="back-link"><ArrowLeft size={15} /> Back to jobs</Link>
    <section className="profile-panel job-detail"><div className="profile-main"><div className="profile-title"><div><h2>{data.title}</h2><span className="status-pill warning">{data.status.replace("_", " ")}</span></div>
      {admin?.permissions?.includes("jobs.manage") && options.length > 0 && <div className="status-mutation"><select className="filter-select" aria-label="New job status" value={nextStatus} onChange={(event) => setNextStatus(event.target.value)}><option value="">Choose status</option>{options.map((value) => <option key={value}>{value}</option>)}</select><button className="button primary" onClick={submit} disabled={!nextStatus || saving}>{saving ? "Saving…" : "Update status"}</button></div>}</div>
      <div className="profile-facts"><div><small>Shop</small><b>{data.shop_name || "Not linked"}</b></div><div><small>Owner</small><b>{data.owner_name || "Not available"}</b></div><div><small>Category</small><b>{data.category || "—"}</b></div><div><small>Pay</small><b>{data.pay_amount ?? "—"}</b></div><div><small>Created</small><b>{dateLabel(data.created_at)}</b></div><div><small>Assigned worker</small><b>{data.assigned_worker_id || "Not assigned"}</b></div></div>
      {data.description && <p className="job-description">{data.description}</p>}{actionError && <p className="inline-error" role="alert">{actionError}</p>}
    </div></section>
    <section className="table-panel detail-table"><div className="section-heading"><div><h2>Applications</h2><p>Latest application records linked to this job.</p></div></div><DataTable columns={[{ key: "worker_name", label: "Worker" }, { key: "status", label: "Application status" }, { key: "created_at", label: "Applied", render: (row) => dateLabel(row.created_at) }]} rows={data.applications || []} emptyTitle="No applications" emptyDetail="No worker applications are recorded for this job." /></section>
  </>;
}
