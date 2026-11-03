import { LoaderCircle, RefreshCw, ShieldAlert } from "lucide-react";

export function StatePanel({ title, detail, loading = false, actionLabel, onAction, tone = "normal" }) {
  const Icon = tone === "denied" ? ShieldAlert : loading ? LoaderCircle : RefreshCw;
  return (
    <section className={"state-panel " + tone} role={tone === "denied" ? "alert" : "status"}>
      <Icon className={loading ? "spin" : ""} size={22} aria-hidden="true" />
      <div><h2>{title}</h2><p>{detail}</p></div>
      {actionLabel && <button className="button secondary" onClick={onAction}>{actionLabel}</button>}
    </section>
  );
}

export function LoadingRows({ rows = 5 }) {
  return <div className="loading-rows" aria-label="Loading data">{Array.from({ length: rows }, (_, index) => <div key={index} />)}</div>;
}
