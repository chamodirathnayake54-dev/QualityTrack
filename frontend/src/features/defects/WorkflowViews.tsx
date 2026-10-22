import type { ReactNode } from 'react';
import type { Defect } from '../../api/defects';
import type { Action } from '../../api/workflow';
import { Button, EmptyState, StatusBadge } from '../../ui';
import { ReadFeedback } from './ReadFeedback';

// PUBLIC_INTERFACE
export function InvestigationSummary() {
  /** Explain the requested transition; the controller and API own acceptance. */
  return <>
    <p>Requested status: Under Investigation</p>
    <p>The server decides permissions, recorded-cause presence and transition legality. Entering this screen does not change status.</p>
  </>;
}

// PUBLIC_INTERFACE
export function AssociatedActionList({ actions }: { actions: Action[] }) {
  /** Render confirmed action fields without deriving eligibility or effectiveness. */
  return <ul className="space-y-3">{actions.map((action) => <li key={action.id}>
    {action.description} · {action.owner_ref} · {action.due_date} · {action.status}
  </li>)}</ul>;
}

// PUBLIC_INTERFACE
export function DefectContextSummary({ defect }: { defect: Defect }) {
  /** Display server context using captured historical labels. */
  return <section aria-label="Defect context" className="panel space-y-2">
    <p>Part: {defect.part_number} · Type: {defect.defect_type.label_at_capture} · Severity: {defect.severity}</p>
    <p>Current status: <StatusBadge>{defect.status}</StatusBadge></p>
  </section>;
}

// PUBLIC_INTERFACE
export function WorkflowCollection({ title, empty, query, children }: {
  title: string; empty: string; children: ReactNode;
  query: {
    isPending: boolean; isError: boolean; error: Error | null; isFetching: boolean;
    data?: { pages: { items: unknown[] }[] }; hasNextPage: boolean;
    refetch: () => unknown; fetchNextPage: () => unknown;
  };
}) {
  /** Display collection states and opaque continuation without interpreting gates. */
  const count = query.data?.pages.reduce((sum, page) => sum + page.items.length, 0) ?? 0;
  return <section className="panel space-y-4" aria-label={title}>
    <h2>{title}</h2>
    <ReadFeedback label={title.toLowerCase()} pending={query.isPending} error={query.error}
      empty={false} retry={() => { void query.refetch(); }} />
    {!query.isPending && !query.isError && <>
      {count ? children : <EmptyState title={empty} />}
      {query.hasNextPage && <Button pending={query.isFetching} onClick={() => { void query.fetchNextPage(); }}>Load more {title.toLowerCase()}</Button>}
    </>}
  </section>;
}
