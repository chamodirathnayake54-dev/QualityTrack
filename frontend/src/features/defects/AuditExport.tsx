import { Alert, Button } from '../../ui';
import { useAuditExport } from './useAuditExport';

// PUBLIC_INTERFACE
export function AuditExport({ record }: { record: Parameters<typeof useAuditExport>[0] }) {
  /** Present the export button, its progress, a photo note and the outcome; the hook owns the rules. */
  const audit = useAuditExport(record);
  if (!audit.visible) return null;
  return <section aria-label="Audit report" className="panel space-y-2">
    <Button variant={audit.readOnly ? 'primary' : 'secondary'} pending={audit.pending}
      onClick={() => { void audit.exportPdf(); }}>
      {audit.pending ? 'Preparing PDF…' : 'Export audit PDF'}
    </Button>
    <p className="text-sm text-muted">The report does not include photos.</p>
    {audit.message && <Alert tone={audit.success ? 'success' : 'warning'}><p>{audit.message}</p></Alert>}
  </section>;
}
