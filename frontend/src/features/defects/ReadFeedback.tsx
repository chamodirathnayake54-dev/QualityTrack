import { ApiError } from '../../api/client';
import { Alert, Button, EmptyState, Skeleton } from '../../ui';

// PUBLIC_INTERFACE
export function ReadFeedback({ label, pending, error, empty, retry }: {
  label: string; pending: boolean; error: Error | null; empty: boolean; retry: () => void;
}) {
  /** Render caller-prepared read outcomes without fetching or deciding permission. */
  if (pending) return <Skeleton label={`Loading ${label}…`} />;
  const forbidden = error instanceof ApiError && error.problem.status === 403;
  if (error) return <Alert tone="danger">
    <p>{forbidden
      ? label === 'assignable owners' ? "You don't have permission to assign actions."
        : label === 'recorded causes' ? "You don't have permission to read causes."
        : "You don't have permission to do this. Your role does not allow this action."
      : `${label}: ${error.message}`}</p>
    {!forbidden && <Button onClick={retry}>Retry {label}</Button>}
  </Alert>;
  if (empty) return <EmptyState title={`No ${label} available`}>
    <p>Required capture choices are unavailable. Capture cannot proceed until choices are available.</p>
    <Button onClick={retry}>Refresh {label}</Button>
  </EmptyState>;
  return null;
}
