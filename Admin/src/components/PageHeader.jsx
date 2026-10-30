import { RefreshCw } from "lucide-react";

export function PageHeader({ eyebrow = "OPERATIONS", title, description, onRefresh, refreshing = false }) {
  return <div className="page-header">
    <div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>
    {onRefresh && <button className="button secondary refresh-button" onClick={onRefresh} disabled={refreshing}><RefreshCw size={15} className={refreshing ? "spin" : ""} />Refresh</button>}
  </div>;
}
