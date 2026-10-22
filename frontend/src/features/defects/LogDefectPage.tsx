import { Link } from 'react-router-dom';
import { ApiError } from '../../api/client';
import { Alert, Button, ErrorSummary } from '../../ui';
import { CaptureFields } from './CaptureFields';
import { ReadFeedback } from './ReadFeedback';
import { useCapture } from './useCapture';
import { lookupFields } from './validation';

// PUBLIC_INTERFACE
export function LogDefectPage() {
  /** Present photo-free S1; only confirmed capture exposes the saved record's next step. */
  const controller = useCapture();
  return <section className="max-w-form space-y-6">
    <h1 tabIndex={-1}>Log defect</h1>
    <p>Required: production context and severity. Fields marked * are required.</p>
    <p>Photo upload is not available in this version</p>
    {controller.saved ? <>
      <Alert tone="success">Defect logged. Part: {controller.saved.data.part_number}. Status: {controller.saved.data.status}.</Alert>
      <Link to={`/defects/${encodeURIComponent(controller.saved.data.id)}/causes`}>Continue to record cause</Link>
      <p><Link to="/defects">Return to defects</Link></p>
    </> : <>
      {lookupFields.map((field, index) => {
        const query = controller.lookups[index];
        return <ReadFeedback key={field.key} label={field.label.toLowerCase()} pending={query.isPending}
          error={query.error} empty={query.isSuccess && !controller.choices[field.key].length}
          retry={() => { void query.refetch(); }} />;
      })}
      <form noValidate className="space-y-6" onSubmit={(event) => { event.preventDefault(); void controller.submit(); }}>
        <ErrorSummary errors={Object.values(controller.errors).map((label) => ({ label }))} />
        <fieldset disabled={controller.pending} className="space-y-6">
          <CaptureFields draft={controller.draft} errors={controller.errors} choices={controller.choices} update={controller.update} />
        </fieldset>
        {controller.error && <Alert tone="danger">
          {controller.error instanceof ApiError && controller.error.problem.status === 403
            ? "You don't have permission to log a defect." : controller.error.message}
          {controller.error instanceof ApiError && controller.error.uncertain &&
            <p><Link to="/defects">We couldn't confirm the defect was saved. Check the defect list before logging it again to avoid a duplicate.</Link></p>}
        </Alert>}
        <Button type="submit" pending={controller.pending} disabled={!controller.ready}>
          {controller.pending ? 'Logging defect…' : 'Log defect'}
        </Button>
      </form>
    </>}
  </section>;
}
