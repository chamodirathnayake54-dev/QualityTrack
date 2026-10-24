import type { ReactNode } from 'react';
import type { Defect } from '../../api/defects';
import type { Action, Cause, DefectEvent } from '../../api/workflow';
import { Button, EmptyState, StatusBadge } from '../../ui';
import { ReadFeedback } from './ReadFeedback';

// PUBLIC_INTERFACE
export function RecordAttribution({ label, actor, at, zone }: {
  label: string; actor: string; at: string; zone?: string;
}) {
  /** Present server attribution consistently in plant time, without resolving or guessing usernames. */
  return <span>{label} {actor} ·{' '}
    {new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'long', timeZone: zone }).format(new Date(at))}
  </span>;
}

// PUBLIC_INTERFACE
export function CauseList({ causes, zone }: { causes: Cause[]; zone?: string }) {
  /** Show every saved cause with its server-recorded author and plant-zone timestamp. */
  return <ul className="space-y-2">{causes.map((cause) => <li key={cause.id}>
    {cause.text}
    <p><RecordAttribution label="Recorded by" actor={cause.recorded_by_ref} at={cause.recorded_at} zone={zone} /></p>
  </li>)}</ul>;
}

// PUBLIC_INTERFACE
export function EventList({ events, zone }: {
  events: (DefectEvent & { completion_notes?: string | null; reopen_reason?: string | null })[];
  zone?: string;
}) {
  /** Present immutable history with attribution, plant-zone time and optional action evidence. */
  return <ul className="space-y-2">{events.map((entry) => <li key={entry.id}>
    {entry.old_status ?? 'Created'} → {entry.new_status} ·{' '}
    <RecordAttribution label="Changed by" actor={entry.actor_ref} at={entry.occurred_at} zone={zone} />
    {entry.completion_notes && <p>Completion notes: {entry.completion_notes}</p>}
    {entry.reopen_reason && <p>Reason for reopening: {entry.reopen_reason}</p>}
  </li>)}</ul>;
}

// PUBLIC_INTERFACE
export function InvestigationSummary() {
  /** Explain the requested transition; the controller and API own acceptance. */
  return <>
    <p>You are about to move this defect to Under Investigation. At least one cause must be recorded first. Nothing changes until you confirm.</p>
  </>;
}

// PUBLIC_INTERFACE
export function AssociatedActionList({ actions }: { actions: Action[] }) {
  /** Render confirmed action fields without deriving eligibility or effectiveness. */
  return <ul className="space-y-3">{actions.map((action) => <li key={action.id}>
    {action.description} · {action.due_date} · {action.status}
    {' · '}Owner: {action.owner_ref}
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
