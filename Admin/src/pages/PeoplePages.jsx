import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ExternalLink, Search, ShieldOff, ShieldCheck } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { api } from "../services/api";
import { useResource } from "../hooks/useResource";
import { DataTable, Pagination } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { LoadingRows, StatePanel } from "../components/StatePanel";

const PAGE_SIZE = 20;
const formatDate = (value) => value ? new Date(value).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—";

export function PeopleListPage({ kind }) {
  const isWorker = kind === "workers";
  const title = isWorker ? "Workers" : "Shop Owners";
  const { user, admin } = useAuth();
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [active, setActive] = useState("");
  const [offset, setOffset] = useState(0);
  useEffect(() => { const timer = setTimeout(() => { setQuery(search.trim()); setOffset(0); }, 250); return () => clearTimeout(timer); }, [search]);
  const loader = useCallback((signal) => {
    const params = { limit: PAGE_SIZE, offset };
    if (query) params.q = query;
    if (active !== "") params.active = active;
    return isWorker ? api.workers(user, params, signal) : api.shopOwners(user, params, signal);
  }, [user, isWorker, query, active, offset]);
  const { data, loading, error, retry } = useResource(loader);
  const canManage = admin?.permissions?.includes("users.manage");
  const columns = isWorker ? [
    { key: "name", label: "Worker", render: (row) => <div className="person-cell"><b>{row.name || "Unnamed user"}</b><small>{row.email || row.phone_number || "No contact detail"}</small></div> },
    { key: "application_count", label: "Applications" },
    { key: "created_at", label: "Joined", render: (row) => formatDate(row.created_at) },
    { key: "is_active", label: "Access", render: (row) => <span className={"status-pill " + (row.is_active ? "success" : "muted")}>{row.is_active ? "Active" : "Suspended"}</span> },
    { key: "view", label: "", render: (row) => <Link className="table-link" to={`/admin/workers/${row.id}`}>View <ExternalLink size={13} /></Link> },
  ] : [
    { key: "name", label: "Shop owner", render: (row) => <div className="person-cell"><b>{row.name || "Unnamed user"}</b><small>{row.email || row.phone_number || "No contact detail"}</small></div> },
    { key: "shop_count", label: "Shops" },
    { key: "job_count", label: "Jobs" },
    { key: "created_at", label: "Joined", render: (row) => formatDate(row.created_at) },
    { key: "is_active", label: "Access", render: (row) => <span className={"status-pill " + (row.is_active ? "success" : "muted")}>{row.is_active ? "Active" : "Suspended"}</span> },
    { key: "view", label: "", render: (row) => <Link className="table-link" to={`/admin/shop-owners/${row.id}`}>View <ExternalLink size={13} /></Link> },
  ];

  return <>
    <PageHeader title={title} description={isWorker ? "Worker profiles and their application history." : "Shop owner accounts, associated shops and job activity."} onRefresh={retry} refreshing={loading} />
    <div className="toolbar-row">
      <label className="search-field"><Search size={16} /><input aria-label={`Search ${title.toLowerCase()}`} value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search name, email or phone" /></label>
      <select className="filter-select" aria-label="Account status" value={active} onChange={(event) => { setActive(event.target.value); setOffset(0); }}><option value="">All accounts</option><option value="true">Active</option><option value="false">Suspended</option></select>
      <span className="result-total">{data?.total ?? "—"} records</span>
    </div>
    <section className="table-panel">
      {error ? <StatePanel title="Could not load records" detail={error.message} actionLabel="Retry" onAction={retry} /> : loading && !data ? <LoadingRows /> : <DataTable columns={columns} rows={data?.items || []} emptyTitle={`No ${title.toLowerCase()} found`} emptyDetail="There are no records matching this search." />}
      {data && <Pagination total={data.total} limit={data.limit} offset={data.offset} onChange={setOffset} />}
    </section>
  </>;
}

export function PersonDetailPage({ kind }) {
  const { user, admin } = useAuth();
  const { userId } = useParams();
  const isWorker = kind === "workers";
  const [offset, setOffset] = useState(0);
  const loader = useCallback((signal) => isWorker ? api.worker(user, userId, { limit: 50, offset }, signal) : api.shopOwner(user, userId, signal), [user, userId, isWorker, offset]);
  const { data, loading, error, retry } = useResource(loader);
  const [mutationError, setMutationError] = useState("");
  const [saving, setSaving] = useState(false);
  if (loading && !data) return <><PageHeader title={isWorker ? "Worker profile" : "Shop owner profile"} /><LoadingRows /></>;
  if (error) return <><PageHeader title="Profile" /><StatePanel title="Could not load profile" detail={error.message} actionLabel="Retry" onAction={retry} /></>;
  const person = data?.user;
  if (!person) return null;
  const update = async () => {
    setSaving(true); setMutationError("");
    try {
      if (isWorker) await api.updateWorker(user, userId, !person.is_active);
      else await api.updateShopOwner(user, userId, !person.is_active);
      retry();
    } catch (reason) { setMutationError(reason.message); }
    finally { setSaving(false); }
  };
  return <>
    <PageHeader title={isWorker ? "Worker profile" : "Shop owner profile"} description="Verified account details from the ERRNO database." onRefresh={retry} />
    <Link to={isWorker ? "/admin/workers" : "/admin/shop-owners"} className="back-link"><ArrowLeft size={15} /> Back to {isWorker ? "workers" : "shop owners"}</Link>
    <section className="profile-panel"><div className="profile-initial">{(person.name || "?")[0].toUpperCase()}</div><div className="profile-main"><div className="profile-title"><div><h2>{person.name || "Unnamed user"}</h2><span className={"status-pill " + (person.is_active ? "success" : "muted")}>{person.is_active ? "Active account" : "Suspended"}</span></div>
      {admin?.permissions?.includes("users.manage") && <button className={"button " + (person.is_active ? "danger" : "primary")} onClick={update} disabled={saving}>{person.is_active ? <ShieldOff size={15} /> : <ShieldCheck size={15} />}{saving ? "Saving…" : person.is_active ? "Suspend account" : "Reactivate account"}</button>}</div>
      <div className="profile-facts"><div><small>Email</small><b>{person.email || "Not provided"}</b></div><div><small>Phone</small><b>{person.phone_number || "Not provided"}</b></div><div><small>Joined</small><b>{formatDate(person.created_at)}</b></div><div><small>ERRNO user ID</small><b className="mono">{person.id}</b></div></div>
      {mutationError && <p className="inline-error" role="alert">{mutationError}</p>}
    </div></section>
    {isWorker ? <section className="table-panel detail-table"><div className="section-heading"><div><h2>Application history</h2><p>{data.total_applications} applications</p></div></div><DataTable columns={[
      { key: "job_title", label: "Job" }, { key: "job_status", label: "Job status" }, { key: "status", label: "Application status" }, { key: "created_at", label: "Applied", render: (row) => formatDate(row.created_at) },
    ]} rows={data.applications} emptyTitle="No applications" emptyDetail="This worker has no recorded applications." /><Pagination total={data.total_applications} limit={data.limit} offset={data.offset} onChange={setOffset} /></section> : <>
      <section className="table-panel detail-table"><div className="section-heading"><div><h2>Shops</h2><p>{data.shops.length} associated shops</p></div></div><DataTable columns={[{ key: "shop_name", label: "Shop" }, { key: "category", label: "Category" }, { key: "address", label: "Address" }, { key: "created_at", label: "Created", render: (row) => formatDate(row.created_at) }]} rows={data.shops} emptyTitle="No shops" emptyDetail="No shop is linked to this account." /></section>
      <section className="table-panel detail-table"><div className="section-heading"><div><h2>Recent jobs</h2><p>Latest associated job records{data.jobs_truncated ? " (showing first 100)" : ""}</p></div></div><DataTable columns={[{ key: "title", label: "Job" }, { key: "status", label: "Status" }, { key: "shop_name", label: "Shop" }, { key: "created_at", label: "Created", render: (row) => formatDate(row.created_at) }]} rows={data.jobs} emptyTitle="No jobs" emptyDetail="No jobs are linked to this account." /></section>
    </>}
  </>;
}
