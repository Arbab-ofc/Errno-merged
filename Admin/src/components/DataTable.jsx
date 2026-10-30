export function DataTable({ columns, rows, emptyTitle = "No records found", emptyDetail = "Try changing the search or filters." }) {
  if (!rows?.length) return <div className="empty-table"><span className="empty-mark">—</span><h3>{emptyTitle}</h3><p>{emptyDetail}</p></div>;
  return <div className="data-table-wrap"><table className="data-table"><thead><tr>{columns.map((column) => <th key={column.key}>{column.label}</th>)}</tr></thead>
    <tbody>{rows.map((row) => <tr key={row.id}>{columns.map((column) => <td key={column.key}>{column.render ? column.render(row) : row[column.key] ?? "—"}</td>)}</tr>)}</tbody>
  </table></div>;
}

export function Pagination({ total, limit, offset, onChange }) {
  const page = Math.floor(offset / limit) + 1;
  const pages = Math.max(1, Math.ceil(total / limit));
  return <div className="pagination-bar"><span>{total ? `Showing ${offset + 1}–${Math.min(offset + limit, total)} of ${total}` : "0 records"}</span><div><button className="button secondary" disabled={page <= 1} onClick={() => onChange(Math.max(0, offset - limit))}>Previous</button><span>Page {page} of {pages}</span><button className="button secondary" disabled={page >= pages} onClick={() => onChange(offset + limit)}>Next</button></div></div>;
}
