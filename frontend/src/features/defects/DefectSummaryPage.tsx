import { useRef, useState } from 'react';
import { useInfiniteQuery, useIsMutating, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { ApiError } from '../../api/client';
import type { Page } from '../../api/defects';
import type { Action, Cause, DefectEvent } from '../../api/workflow';
import { Alert, Button, Field, TextArea } from '../../ui';
import { ReadFeedback } from './ReadFeedback';
import { DefectContextSummary, WorkflowCollection } from './WorkflowViews';
import { useWorkflowPages, useWorkflowRecord } from './useWorkflow';

type RecordState = ReturnType<typeof useWorkflowRecord>;
type ActionEvent = DefectEvent & { completion_notes: string | null; reopen_reason: string | null };

function EventList({ events, zone }: { events: ActionEvent[] | DefectEvent[]; zone?: string }) {
  return <ul className="space-y-2">{events.map((entry) => <li key={entry.id}>
    {entry.old_status ?? 'Created'} → {entry.new_status} · Changed by {entry.actor_ref} ·{' '}
    {new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'long', timeZone: zone }).format(new Date(entry.occurred_at))}
    {'completion_notes' in entry && entry.completion_notes && <p>Completion notes: {entry.completion_notes}</p>}
    {'reopen_reason' in entry && entry.reopen_reason && <p>Reason for reopening: {entry.reopen_reason}</p>}
  </li>)}</ul>;
}

function TransitionControl({ record, label, target, actionId, evidence, ready, context, refresh, reportSuccess }: {
  record: RecordState; label: string; target: string; actionId?: string;
  evidence?: 'completion_notes' | 'reopen_reason'; ready: boolean; context: string;
  refresh: () => Promise<unknown>;
  reportSuccess: (message: string) => void;
}) {
  const queryClient = useQueryClient();
  const [review, setReview] = useState<{ etag: string; context: string } | null>(null);
  const [notes, setNotes] = useState('');
  const [message, setMessage] = useState('');
  const [success, setSuccess] = useState(false);
  const lock = useRef(false);
  const mutationKey = ['workflow-write', record.identity?.ref, record.defectId];
  const pending = useIsMutating({ mutationKey }) > 0;
  const mutation = useMutation({
    mutationKey, retry: false,
    mutationFn: ({ etag, body }: { etag: string; body: unknown }) => record.client.request(
      actionId ? `/actions/${encodeURIComponent(actionId)}/transitions` : `${record.base}/transitions`,
      { method: 'POST', etag, body },
    ),
  });
  const checked = Boolean(review && review.etag === record.parent.data?.etag && review.context === context);
  const available = ready && !record.parent.isFetching && !pending;
  const submit = async () => {
    if (lock.current || pending || !available) return;
    if (!checked || !review || !/^"[0-9]+"$/.test(review.etag)) {
      setMessage('Reload latest details, then check them and tick the box before confirming.');
      return;
    }
    if (evidence && (!notes.trim() || notes.trim().length > 2000)) {
      setMessage('Add notes between 1 and 2000 characters before confirming.');
      return;
    }
    lock.current = true;
    setSuccess(false);
    setMessage('');
    try {
      await mutation.mutateAsync({
        etag: review.etag,
        body: { target_status: target, ...(evidence ? { [evidence]: notes.trim() } : {}) },
      });
      setSuccess(true);
      setMessage(`${label} saved.`);
      reportSuccess(`${label} saved.`);
      setNotes('');
      setReview(null);
      await refresh();
      void queryClient.invalidateQueries({ queryKey: ['defects', record.identity?.ref] });
    } catch (error) {
      setReview(null);
      if (error instanceof ApiError) {
        setMessage(error.uncertain
          ? "We couldn't confirm whether this was saved. Please check the page before trying again so nothing is saved twice."
          : error.problem.code === 'actions_incomplete' && target === 'Closed'
            ? "This can't be closed yet: all corrective actions must be completed first."
            : error.message);
        if (error.uncertain || [400, 409, 412, 428].includes(error.problem.status)) await refresh();
      } else setMessage("We couldn't save this change. Please check the latest details before trying again.");
    } finally {
      lock.current = false;
    }
  };
  return <section aria-label={label} className="panel space-y-3">
    <h3>{label}</h3>
    <p>Check the defect details and history above. Nothing changes until you confirm.</p>
    {message && <Alert tone={success ? 'success' : 'warning'}>
      <p>{message}</p>
      {success && <><Link to={record.base}>Back to defect</Link>{' · '}
        <Link to="/defects">View all defects</Link></>}
    </Alert>}
    <form noValidate onSubmit={(event) => { event.preventDefault(); void submit(); }}>
      {evidence && <Field label={evidence === 'completion_notes' ? 'Completion notes *' : 'Reason for reopening *'}>
        {(props) => <TextArea {...props} value={notes} disabled={pending}
          onChange={(event) => setNotes(event.target.value)} />}
      </Field>}
      <label className="flex min-h-11 items-center gap-3"><input type="checkbox"
        checked={checked} disabled={!available}
        onChange={(event) => setReview(event.target.checked && record.parent.data?.etag
          ? { etag: record.parent.data.etag, context } : null)} />
        I have checked the latest details for {label.toLowerCase()}.
      </label>
      <Button type="button" disabled={pending} onClick={() => { setReview(null); void refresh(); }}>Reload latest details</Button>
      <Button type="submit" disabled={!available || !checked} pending={pending}>Confirm {label.toLowerCase()}</Button>
    </form>
  </section>;
}

function ActionCard({ action, record, context, ready, refresh, reportSuccess }: {
  action: Action; record: RecordState; context: string; ready: boolean; refresh: () => Promise<unknown>;
  reportSuccess: (message: string) => void;
}) {
  const history = useInfiniteQuery({
    queryKey: ['action-history', record.identity?.ref, record.defectId, action.id],
    initialPageParam: '',
    queryFn: async ({ signal, pageParam }) => (await record.client.request<Page<ActionEvent>>(
      `/actions/${encodeURIComponent(action.id)}/history?${new URLSearchParams({ limit: '50', ...(pageParam ? { cursor: pageParam } : {}) })}`,
      { signal },
    )).data,
    getNextPageParam: (page) => page.next_cursor ?? undefined,
    retry: false, refetchOnWindowFocus: false, refetchOnReconnect: false,
  });
  const can = (permission: string) => record.identity?.permissions.includes(permission);
  const control = (label: string, target: string, evidence?: 'completion_notes' | 'reopen_reason') =>
    <TransitionControl key={`${action.status}-${label}`} record={record} label={label} target={target}
      actionId={action.id} evidence={evidence} ready={ready && history.isSuccess && !history.isFetching}
      context={JSON.stringify([context, action, history.data])} refresh={refresh} reportSuccess={reportSuccess} />;
  return <article className="panel space-y-3" aria-label={action.description}>
    <h3>{action.description}</h3>
    <p>Status: {action.status} · Due: {action.due_date} · Owner: {action.owner_ref}</p>
    <WorkflowCollection title="Action history" empty="No action history yet" query={history}>
      <EventList events={history.data?.pages.flatMap((page) => page.items) ?? []} zone={record.identity?.plant_zone} />
    </WorkflowCollection>
    {action.status === 'Open' && can('action.progress') && control('Start action', 'In Progress')}
    {action.status !== 'Complete' && can('action.complete') && control('Complete action', 'Complete', 'completion_notes')}
    {action.status === 'Complete' && can('action.reopen') && control('Reopen action', 'In Progress', 'reopen_reason')}
  </article>;
}

// PUBLIC_INTERFACE
export function DefectSummaryPage() {
  /** Show saved defect context to every reader and grant-gated, reviewed transitions to writers. */
  const record = useWorkflowRecord();
  const [successMessage, setSuccessMessage] = useState('');
  const causes = useWorkflowPages<Cause>(record, 'causes');
  const actions = useWorkflowPages<Action>(record, 'actions');
  const history = useWorkflowPages<DefectEvent>(record, 'history');
  const queryClient = useQueryClient();
  const can = (permission: string) => record.identity?.permissions.includes(permission);
  const ready = [causes, actions, history].every((query) => query.isSuccess && !query.isFetching);
  const context = JSON.stringify([record.parent.data, causes.data, actions.data, history.data]);
  const refresh = async () => {
    await Promise.all([record.parent.refetch(), causes.refetch(), actions.refetch(), history.refetch(),
      queryClient.invalidateQueries({ queryKey: ['action-history', record.identity?.ref, record.defectId] })]);
  };
  const defect = record.parent.data?.data;
  return <div className="space-y-6">
    <h1 tabIndex={-1}>Defect summary</h1>
    <Link to="/defects">Back to defects</Link>
    {successMessage && <Alert tone="success"><p>{successMessage}</p>
      <Link to={record.base}>Back to defect</Link>{' · '}
      <Link to="/defects">View all defects</Link>
    </Alert>}
    <ReadFeedback label="defect" pending={record.parent.isPending || record.parent.isFetching}
      error={record.parent.error} empty={false} retry={() => { void refresh(); }} />
    {record.parent.isSuccess && defect && <>
      <DefectContextSummary defect={defect} />
      <section className="panel" aria-label="Defect details">
        <h2>Defect details</h2>
        <p>Quantity affected: {defect.quantity_affected}</p>
        <p>Production line: {defect.production_line.label_at_capture} · Shift: {defect.shift.label_at_capture}</p>
        <p>Logged by {defect.created_by_ref} · {new Intl.DateTimeFormat(undefined, {
          dateStyle: 'medium', timeStyle: 'long', timeZone: record.identity?.plant_zone,
        }).format(new Date(defect.created_at))}</p>
      </section>
      <nav aria-label="Available next steps" className="flex flex-wrap gap-4">
        {can('cause.create') && <Link to={`${record.base}/causes`}>Record cause</Link>}
        {can('defect.investigate') && <Link to={`${record.base}/investigation`}>Investigation</Link>}
        {can('action.assign') && <Link to={`${record.base}/actions`}>Add corrective action</Link>}
      </nav>
      <WorkflowCollection title="Recorded causes" empty="No cause recorded yet" query={causes}>
        <ul>{causes.data?.pages.flatMap((page) => page.items).map((cause) => <li key={cause.id}>{cause.text}</li>)}</ul>
      </WorkflowCollection>
      <WorkflowCollection title="Status history" empty="No status history yet" query={history}>
        <EventList events={history.data?.pages.flatMap((page) => page.items) ?? []} zone={record.identity?.plant_zone} />
      </WorkflowCollection>
      <WorkflowCollection title="Associated actions" empty="No corrective actions yet" query={actions}>
        {actions.data?.pages.flatMap((page) => page.items).map((action) =>
          <ActionCard key={action.id} action={action} record={record} context={context} ready={ready} refresh={refresh} reportSuccess={setSuccessMessage} />)}
      </WorkflowCollection>
      {defect.status === 'Under Investigation' && can('defect.close') &&
        <TransitionControl record={record} label="Close defect" target="Closed" ready={ready} context={context} refresh={refresh} reportSuccess={setSuccessMessage} />}
      {defect.status === 'Closed' && can('defect.reopen') &&
        <TransitionControl record={record} label="Reopen defect" target="Under Investigation" ready={ready} context={context} refresh={refresh} reportSuccess={setSuccessMessage} />}
    </>}
  </div>;
}
