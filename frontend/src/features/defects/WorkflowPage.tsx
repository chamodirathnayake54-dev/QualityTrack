import { Link } from 'react-router-dom';
import { Alert, Button, DateInput, EmptyState, ErrorSummary, Field, Select, TextArea } from '../../ui';
import { useWorkflow } from './useWorkflow';
import { ReadFeedback } from './ReadFeedback';
import { AssociatedActionList, DefectContextSummary, InvestigationSummary, WorkflowCollection } from './WorkflowViews';
import { actionStatuses, type ActionDraft, type Owner } from './workflowValidation';
import type { Errors } from './validation';

// PUBLIC_INTERFACE
export function CauseEditor({ text, change, errors, disabled }: {
  text: string; change: (value: string) => void; errors: Errors; disabled: boolean;
}) {
  /** Render preliminary cause input without deciding lifecycle eligibility. */
  return <Field label="Why did this defect occur?" error={errors.text}
    hint="A preliminary cause is acceptable. You do not need five answers to meet the presence gate.">
    {(props) => <TextArea {...props} value={text} disabled={disabled} onChange={(event) => change(event.target.value)} />}
  </Field>;
}

// PUBLIC_INTERFACE
export function CorrectiveActionFields({ draft, update, errors, owners, disabled }: {
  draft: ActionDraft; update: (key: keyof ActionDraft, value: string) => void;
  errors: Errors; owners: Owner[]; disabled: boolean;
}) {
  /** Render explicit action fields; completion authority remains a server decision. */
  return <>
    <Field label="Description *" error={errors.description}>{(props) =>
      <TextArea {...props} disabled={disabled} value={draft.description} onChange={(event) => update('description', event.target.value)} />}
    </Field>
    <Field label="Owner *" error={errors.owner_ref}>{(props) =>
      <Select {...props} disabled={disabled} value={draft.owner_ref} onChange={(event) => update('owner_ref', event.target.value)}>
        <option value="">Choose an assignable user</option>
        {owners.map((owner) => <option key={owner.ref} value={owner.ref}>{owner.display_name}</option>)}
      </Select>}
    </Field>
    <Field label="Due date *" error={errors.due_date}>{(props) =>
      <DateInput {...props} disabled={disabled} value={draft.due_date} onChange={(event) => update('due_date', event.target.value)} />}
    </Field>
    <Field label="Status *" error={errors.status}>{(props) =>
      <Select {...props} disabled={disabled} value={draft.status} onChange={(event) => update('status', event.target.value)}>
        <option value="">Choose an action status</option>
        {actionStatuses.map((status) => <option key={status}>{status}</option>)}
      </Select>}
    </Field>
    <p>Complete requires applicable authority and notes; completion does not mean effectiveness verified.</p>
    {draft.status === 'Complete' && <Field label="Completion notes *" error={errors.completion_notes}>{(props) =>
      <TextArea {...props} disabled={disabled} value={draft.completion_notes} onChange={(event) => update('completion_notes', event.target.value)} />}
    </Field>}
  </>;
}

// PUBLIC_INTERFACE
export function WorkflowPage({ kind }: { kind: 'causes' | 'investigation' | 'actions' }) {
  /** Render S2–S4 from controller-prepared state; never infer grants, gates or assignability. */
  const w = useWorkflow(kind);
  const title = kind === 'causes' ? 'Record cause' : kind === 'investigation' ? 'Start investigation' : 'Add corrective action';
  const link = `/defects/${encodeURIComponent(w.defectId)}`;
  const busy = w.pending || w.parent.isFetching;
  const ownerReady = w.owners.isSuccess && w.owners.data.items.length > 0;
  return <div className="space-y-6">
    <h1 tabIndex={-1}>{title}</h1>
    {kind === 'causes' && <p>Record a cause using the initial 5-Why prompt. A nonblank cause is required.</p>}
    {kind === 'actions' && <p>Fields marked * are required. Select a status explicitly.</p>}
    {w.message && <Alert tone={w.mutationError ? 'warning' : 'success'}>{w.message}</Alert>}
    <ErrorSummary errors={Object.values(w.errors).map((label) => ({ label }))} />
    <ReadFeedback label="defect" pending={w.parent.isPending || w.parent.isFetching} error={w.parent.error}
      empty={false} retry={() => { void w.refresh(); }} />
    {w.parent.isSuccess && !w.parent.isFetching && <>
      <DefectContextSummary defect={w.parent.data.data} />
      <nav aria-label="Defect journey" className="flex flex-wrap gap-4">
        <Link to={`${link}/causes`}>Record or review cause</Link>
        <Link to={`${link}/investigation`}>Review investigation step</Link>
        <Link to={`${link}/actions`}>Add corrective action</Link>
      </nav>
      {(kind === 'causes' || kind === 'investigation') && <WorkflowCollection title="Recorded causes"
        empty={kind === 'investigation' ? 'No recorded cause. Record a cause before starting investigation' : 'No cause recorded yet'} query={w.causes}>
        <ul>{w.causes.data?.pages.flatMap((page) => page.items).map((cause) =>
          <li key={cause.id}>{cause.text} — Recorded by {cause.recorded_by_ref}</li>)}</ul>
        <p>Preliminary recorded cause; validity is not established. The API checks the presence gate.</p>
      </WorkflowCollection>}
      {kind === 'causes' && <form className="panel space-y-4" noValidate onSubmit={(event) => { event.preventDefault(); void w.submit(); }}>
        <CauseEditor text={w.text} change={w.setText} errors={w.errors} disabled={busy} />
        <Button type="submit" disabled={busy} pending={w.pending}>{w.pending ? 'Recording cause…' : 'Record cause'}</Button>
      </form>}
      {kind === 'investigation' && <>
        <WorkflowCollection title="Transition history" empty="No transition history yet" query={w.history}>
          <ul>{w.history.data?.pages.flatMap((page) => page.items).map((entry) =>
            <li key={entry.id}>{entry.old_status} → {entry.new_status} · {entry.actor_ref} ·
              {' '}{new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'long', timeZone: w.identity?.plant_zone }).format(new Date(entry.occurred_at))}
              {' '}({w.identity?.plant_zone})</li>)}</ul>
        </WorkflowCollection>
        <form className="panel space-y-4" noValidate onSubmit={(event) => { event.preventDefault(); void w.submit(); }}>
          <InvestigationSummary />
          <label className="flex min-h-11 items-center gap-3"><input type="checkbox" checked={w.reviewed} disabled={busy || !w.reviewReady}
            onChange={(event) => w.review(event.target.checked)} /> I have reviewed the current defect and saved context</label>
          <Button type="button" disabled={busy} onClick={() => { void w.refresh(); }}>Refresh for review</Button>
          <Button type="submit" disabled={busy || !w.reviewReady} pending={w.pending}>
            {w.pending ? 'Moving to Under Investigation…' : 'Move to Under Investigation'}
          </Button>
        </form>
      </>}
      {kind === 'actions' && <>
        <WorkflowCollection title="Associated actions" empty="No corrective actions yet" query={w.actions}>
          <AssociatedActionList actions={w.actions.data?.pages.flatMap((page) => page.items) ?? []} />
        </WorkflowCollection>
        <ReadFeedback label="assignable owners" pending={w.owners.isPending} error={w.owners.error}
          empty={false} retry={() => { void w.owners.refetch(); }} />
        {w.owners.isSuccess && !ownerReady && <EmptyState title="No assignable owners available" />}
        <form className="panel space-y-4" noValidate onSubmit={(event) => { event.preventDefault(); void w.submit(); }}>
          <CorrectiveActionFields draft={w.draft} update={w.update} errors={w.errors}
            owners={w.owners.isSuccess ? w.owners.data.items : []} disabled={busy || !ownerReady} />
          <Button type="submit" disabled={busy || !ownerReady} pending={w.pending}>
            {w.pending ? 'Adding corrective action…' : 'Add action'}
          </Button>
        </form>
      </>}
    </>}
  </div>;
}
