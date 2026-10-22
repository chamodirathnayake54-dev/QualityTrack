import type { ReactNode } from 'react';

// PUBLIC_INTERFACE
export function StatusBadge({ children }: { children: ReactNode }) {
  /** Display caller-supplied status without calculating lifecycle policy. */
  return <span className="inline-block rounded-control border border-border px-2 py-1 text-sm font-semibold">{children}</span>;
}
