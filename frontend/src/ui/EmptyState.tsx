import type { ReactNode } from 'react';

// PUBLIC_INTERFACE
export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  /** Describe an empty or unavailable view without inventing business outcomes. */
  return <section className="panel space-y-3 border-dashed py-8">
    <h2>{title}</h2>{children}
  </section>;
}
