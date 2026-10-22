import { ApiError } from '../../api/client';
import { Alert, Button, EmptyState, Skeleton } from '../../ui';

// PUBLIC_INTERFACE
export function ReadFeedback({ label, pending, error, empty, retry }: {
  label: string; pending: boolean; error: Error | null; empty: boolean; retry: () => void;
}) {
  /** Render caller-prepared read outcomes without fetching or deciding permission. */
  if (pending) return <Skeleton label={`Loading ${label}…`} />;
  if (error) return <Alert tone="danger">
    <p>{label}: {error instanceof ApiError && error.problem.status === 403
      ? 'Access denied. You do not have permission for this request.' : error.message}</p>
    <Button onClick={retry}>Retry {label}</Button>
  </Alert>;
  if (empty) return <EmptyState title={`No ${label} available`}>
    <p>Required capture choices are unavailable. Capture cannot proceed until choices are available.</p>
    <Button onClick={retry}>Refresh {label}</Button>
  </EmptyState>;
  return null;
}
