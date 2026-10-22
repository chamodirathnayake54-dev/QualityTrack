import type { ReactNode } from 'react';
import type { Defect } from '../../api/defects';
import { Button, EmptyState, StatusBadge } from '../../ui';
import { ReadFeedback } from './ReadFeedback';

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
