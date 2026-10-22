import type { ReactNode } from 'react';

// PUBLIC_INTERFACE
export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  /** Describe an empty or unavailable view without inventing business outcomes. */
  return <section className="space-y-3 rounded-control border border-border bg-surface p-6">
    <h2>{title}</h2>{children}
  </section>;
}
