import { Link } from 'react-router-dom';
import { Alert, Button, DateInput, EmptyState, ErrorSummary, Field, Select, TextArea } from '../../ui';
import { useWorkflow } from './useWorkflow';
import { AuditExport } from './AuditExport';
import { ReadFeedback } from './ReadFeedback';
import { AssociatedActionList, CauseList, DefectContextSummary, EventList, InvestigationSummary, WorkflowCollection } from './WorkflowViews';
import { actionStatuses, type ActionDraft, type Owner } from './workflowValidation';
import type { Errors } from './validation';

// PUBLIC_INTERFACE
export function CauseEditor({ text, change, errors, disabled }: {
  text: string; change: (value: string) => void; errors: Errors; disabled: boolean;
}) {
  /** Render preliminary cause input without deciding lifecycle eligibility. */
  return <Field label="Why did this defect occur?" error={errors.text}
    hint="A first answer is enough. You can add more whys later.">
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
    <p>To mark an action Complete you need permission and must add notes. Complete means the work is done, not yet proven to have worked.</p>
    {draft.status === 'Complete' && <Field label="Completion notes *" error={errors.completion_notes}>{(props) =>
      <TextArea {...props} disabled={disabled} value={draft.completion_notes} onChange={(event) => update('completion_notes', event.target.value)} />}
    </Field>}
  </>;
}

// PUBLIC_INTERFACE
export function WorkflowPage({ kind }: { kind: 'causes' | 'investigation' | 'actions' }) {
  /** Render S2–S4 from controller-prepared state; never infer grants, gates or assignability. */
  const w = useWorkflow(kind);
  const title = kind === 'causes' ? 'Record cause' : kind === 'investigation' ? 'Investigation' : 'Add corrective action';
  const link = `/defects/${encodeURIComponent(w.defectId)}`;
  const busy = w.pending || w.parent.isFetching;
  const ownerReady = w.owners.isSuccess && w.owners.data.items.length > 0;
  const steps = [
    { key: 'causes', label: 'Record or review cause', href: `${link}/causes`,
      complete: Boolean(w.causes.data?.pages.some((page) => page.items.length > 0)) },
    { key: 'investigation', label: 'Investigation', href: `${link}/investigation`,
      complete: w.investigationReached },
    { key: 'actions', label: 'Add corrective action', href: `${link}/actions`,
      complete: Boolean(w.actions.data?.pages.some((page) => page.items.length > 0)) },
  ];
  return <div className="space-y-6">
    <h1 tabIndex={-1}>{title}</h1>
    {kind === 'causes' && <p>Describe why this defect happened. Your best answer is fine for now; you can add more later.</p>}
    {kind === 'actions' && <p>Fields marked * are required.</p>}
    {w.message && <Alert tone={w.succeeded ? 'success' : 'warning'}>
      <p>{w.message}</p>
      {w.succeeded && <Link to={kind === 'causes' ? `${link}/investigation` : kind === 'investigation' ? `${link}/actions` : link}>
        {kind === 'causes' ? 'Investigation' : kind === 'investigation' ? 'Add corrective action' : 'Back to defect'}
      </Link>}
    </Alert>}
    <ErrorSummary errors={Object.values(w.errors).map((label) => ({ label }))} />
    <ReadFeedback label="defect" pending={w.parent.isPending || w.parent.isFetching} error={w.parent.error}
      empty={false} retry={() => { void w.refresh(); }} />
    <nav aria-label="Defect journey" className="space-y-3">
      <Link to={link}>Back to defect</Link>
      <ol className="journey">
        {steps.filter((step) => w.identity?.permissions.includes(
          step.key === 'causes' ? 'cause.create' : step.key === 'investigation' ? 'defect.investigate' : 'action.assign',
        )).map((step, index) => <li key={step.key}>
          <Link to={step.href} aria-label={step.label}
            aria-describedby={step.key === kind || step.complete ? `journey-${step.key}` : undefined}
            aria-current={step.key === kind ? 'step' : undefined}>
            <span aria-hidden="true" className="font-semibold">{step.complete ? '✓' : index + 1}</span>
            {step.label}
            {step.key === kind
              ? <span id={`journey-${step.key}`} className="sr-only">Current step</span>
              : step.complete && <span id={`journey-${step.key}`} className="text-sm text-success"> — completed</span>}
          </Link>
        </li>)}
      </ol>
    </nav>
    {w.parent.isSuccess && !w.parent.isFetching && <>
      <DefectContextSummary defect={w.parent.data.data} />
      <AuditExport record={w} />
      {(kind === 'causes' || kind === 'investigation') && <WorkflowCollection title="Recorded causes"
        empty={kind === 'investigation' ? 'No recorded cause. Record a cause before starting investigation' : 'No cause recorded yet'} query={w.causes}>
        <CauseList causes={w.causes.data?.pages.flatMap((page) => page.items) ?? []} zone={w.identity?.plant_zone} />
        <p>These are the causes recorded so far. They are not yet confirmed.</p>
      </WorkflowCollection>}
      {kind === 'causes' && <form className="panel space-y-4" noValidate onSubmit={(event) => { event.preventDefault(); void w.submit(); }}>
        <CauseEditor text={w.text} change={w.setText} errors={w.errors} disabled={busy} />
        <Button type="submit" disabled={busy} pending={w.pending}>{w.pending ? 'Recording cause…' : 'Record cause'}</Button>
      </form>}
      {kind === 'investigation' && <>
        <WorkflowCollection title="Status history" empty="No status history yet" query={w.history}>
          <EventList events={w.history.data?.pages.flatMap((page) => page.items) ?? []} zone={w.identity?.plant_zone} />
        </WorkflowCollection>
        <form className="panel space-y-4" noValidate onSubmit={(event) => { event.preventDefault(); void w.submit(); }}>
          {w.investigationReached ? <p>This defect is Under Investigation. You can add a corrective action next.</p> : <InvestigationSummary />}
          <label className="flex min-h-11 items-center gap-3"><input type="checkbox" checked={w.reviewed} disabled={busy || !w.reviewReady || w.investigationReached}
            onChange={(event) => w.review(event.target.checked)} /> I have checked the defect details and causes above.</label>
          <Button type="button" disabled={busy} onClick={() => { void w.refresh(); }}>Reload latest details</Button>
          <Button type="submit" disabled={busy || !w.reviewReady || w.investigationReached} pending={w.pending}>
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
