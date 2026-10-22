import type { SelectHTMLAttributes } from 'react';

// PUBLIC_INTERFACE
export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  /** Render a native keyboard-operable select. */
  return <select {...props} className="control" />;
}
