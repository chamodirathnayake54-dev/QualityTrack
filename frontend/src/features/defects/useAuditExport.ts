import { useRef, useState } from 'react';
import { ApiError } from '../../api/client';
import type { useWorkflowRecord } from './useWorkflow';

type RecordState = Pick<ReturnType<typeof useWorkflowRecord>, 'client' | 'identity' | 'base' | 'parent'>;

// Any of these grants means the person can change the record, so the page is not read-only for them.
const WRITE_GRANTS = ['cause.create', 'defect.investigate', 'action.assign', 'action.progress',
  'action.complete', 'action.reopen', 'defect.close', 'defect.reopen'];

// PUBLIC_INTERFACE
export function auditFileName(part: string, now: Date = new Date()): string {
  /** Build QualityTrack-defect-<part>-<date>.pdf using only safe file-name characters. */
  const safe = part.replace(/[^A-Za-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '') || 'defect';
  return `QualityTrack-defect-${safe}-${now.toISOString().slice(0, 10)}.pdf`;
}

function saveFile(file: Blob, name: string) {
  const url = URL.createObjectURL(file);
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

// PUBLIC_INTERFACE
export function useAuditExport(record: RecordState) {
  /** Decide visibility from grants, download the PDF once at a time and describe the outcome. */
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState('');
  const [success, setSuccess] = useState(false);
  const lock = useRef(false);
  const permissions = record.identity?.permissions ?? [];
  const defect = record.parent.data?.data;
  const exportPdf = async () => {
    if (lock.current || !defect) return;
    lock.current = true;
    setPending(true);
    setMessage('');
    setSuccess(false);
    try {
      const { data } = await record.client.request<Blob>(`${record.base}/audit.pdf`, { responseType: 'blob' });
      saveFile(data, auditFileName(defect.part_number));
      setSuccess(true);
      setMessage('The audit PDF was downloaded.');
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return;
      setMessage(error instanceof ApiError && error.problem.status === 403
        ? "You don't have permission to export this report."
        : "We couldn't create the PDF. Please try again.");
    } finally {
      lock.current = false;
      setPending(false);
    }
  };
  return {
    visible: permissions.includes('defect.export') && Boolean(defect),
    readOnly: !WRITE_GRANTS.some((grant) => permissions.includes(grant)),
    pending, message, success, exportPdf,
  };
}
