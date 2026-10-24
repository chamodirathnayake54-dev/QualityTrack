import { Link } from 'react-router-dom';
import type { Action } from '../../api/workflow';
import { Alert, Button, Field, TextArea } from '../../ui';
import { ReadFeedback } from './ReadFeedback';
import { DefectContextSummary, EventList, WorkflowCollection } from './WorkflowViews';
import { useActionSummary, useDefectSummary, useTransition, type TransitionOptions } from './useTransition';

// Presentation only: the controller hooks in useTransition.ts own validation, review and saving.
function TransitionControl(options: TransitionOptions) {
  const { label, evidence, record } = options;
  const t = useTransition(options);
  return <section aria-label={label} className="panel space-y-3">
    <h3>{label}</h3>
    <p>Check the defect details and history above. Nothing changes until you confirm.</p>
    {t.message && <Alert tone={t.success ? 'success' : 'warning'}>
      <p>{t.message}</p>
      {t.success && <><Link to={record.base}>Back to defect</Link>{' · '}
        <Link to="/defects">View all defects</Link></>}
    </Alert>}
    <form noValidate onSubmit={(event) => { event.preventDefault(); void t.submit(); }}>
      {evidence && <Field label={evidence === 'completion_notes' ? 'Completion notes *' : 'Reason for reopening *'}>
        {(props) => <TextArea {...props} value={t.notes} disabled={t.pending}
          onChange={(event) => t.setNotes(event.target.value)} />}
      </Field>}
      <label className="flex min-h-11 items-center gap-3"><input type="checkbox"
        checked={t.checked} disabled={!t.available}
        onChange={(event) => t.review(event.target.checked)} />
        I have checked the latest details for {label.toLowerCase()}.
      </label>
      <Button type="button" disabled={t.pending} onClick={() => { void t.reload(); }}>Reload latest details</Button>
      <Button type="submit" disabled={t.confirmDisabled} pending={t.pending}>Confirm {label.toLowerCase()}</Button>
    </form>
  </section>;
}

function ActionCard({ action, record, context, ready, refresh, reportSuccess }: {
  action: Action; record: TransitionOptions['record']; context: string; ready: boolean;
  refresh: () => Promise<unknown>; reportSuccess: (message: string) => void;
}) {
  const summary = useActionSummary(action, record, context, ready);
  return <article className="panel space-y-3" aria-label={action.description}>
    <h3>{action.description}</h3>
    <p>Status: {action.status} · Due: {action.due_date} · Owner: {action.owner_ref}</p>
    <WorkflowCollection title="Action history" empty="No action history yet" query={summary.history}>
      <EventList events={summary.history.data?.pages.flatMap((page) => page.items) ?? []} zone={record.identity?.plant_zone} />
    </WorkflowCollection>
    {summary.choices.map((choice) => <TransitionControl key={`${action.status}-${choice.label}`} {...choice}
      record={record} actionId={action.id} ready={summary.ready} context={summary.context}
      refresh={refresh} reportSuccess={reportSuccess} />)}
  </article>;
}

// PUBLIC_INTERFACE
export function DefectSummaryPage() {
  /** Show saved defect context to every reader and grant-gated, reviewed transitions to writers. */
  const s = useDefectSummary();
  const { record, causes, actions, history } = s;
  const defect = record.parent.data?.data;
  return <div className="space-y-6">
    <h1 tabIndex={-1}>Defect summary</h1>
    <Link to="/defects">Back to defects</Link>
    {s.successMessage && <Alert tone="success"><p>{s.successMessage}</p>
      <Link to={record.base}>Back to defect</Link>{' · '}
      <Link to="/defects">View all defects</Link>
    </Alert>}
    <ReadFeedback label="defect" pending={record.parent.isPending || record.parent.isFetching}
      error={record.parent.error} empty={false} retry={() => { void s.refresh(); }} />
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
        {s.links.map((link) => <Link key={link.path} to={`${record.base}/${link.path}`}>{link.label}</Link>)}
      </nav>
      <WorkflowCollection title="Recorded causes" empty="No cause recorded yet" query={causes}>
        <ul>{causes.data?.pages.flatMap((page) => page.items).map((cause) => <li key={cause.id}>{cause.text}</li>)}</ul>
      </WorkflowCollection>
      <WorkflowCollection title="Status history" empty="No status history yet" query={history}>
        <EventList events={history.data?.pages.flatMap((page) => page.items) ?? []} zone={record.identity?.plant_zone} />
      </WorkflowCollection>
      <WorkflowCollection title="Associated actions" empty="No corrective actions yet" query={actions}>
        {actions.data?.pages.flatMap((page) => page.items).map((action) =>
          <ActionCard key={action.id} action={action} record={record} context={s.context} ready={s.ready}
            refresh={s.refresh} reportSuccess={s.setSuccessMessage} />)}
      </WorkflowCollection>
      {s.choices.map((choice) => <TransitionControl key={choice.label} {...choice} record={record}
        ready={s.ready} context={s.context} refresh={s.refresh} reportSuccess={s.setSuccessMessage} />)}
    </>}
  </div>;
}
