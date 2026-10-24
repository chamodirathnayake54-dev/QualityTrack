import type { ReactNode } from 'react';

// PUBLIC_INTERFACE
export function DataTable<T>({ caption, columns, rows, rowKey }: {
  caption: string; columns: { key: string; heading: string; render: (row: T) => ReactNode }[];
  rows: T[]; rowKey: (row: T) => string;
}) {
  /** Render semantic tabular data in a keyboard-scrollable narrow-screen region. */
  return <div role="region" aria-label={caption} tabIndex={0} className="overflow-x-auto rounded-control border border-border shadow-card">
    <table className="w-full min-w-[72rem] border-collapse bg-surface">
      <caption className="p-3 text-left font-semibold">{caption}</caption>
      <thead><tr>{columns.map((column) => <th key={column.key} scope="col">{column.heading}</th>)}</tr></thead>
      <tbody>{rows.map((row) => <tr key={rowKey(row)}>{columns.map((column) =>
        <td key={column.key}>{column.render(row)}</td>)}</tr>)}</tbody>
    </table>
  </div>;
}
