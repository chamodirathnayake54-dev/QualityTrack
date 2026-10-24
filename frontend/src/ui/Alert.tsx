import type { ReactNode } from 'react';

// PUBLIC_INTERFACE
export function Alert({ children, tone = 'info' }: {
  children: ReactNode; tone?: 'info' | 'success' | 'warning' | 'danger';
}) {
  /** Announce meaningful text; color is supplementary, never the only signal. */
  const color = { info: 'text-ink', success: 'text-success', warning: 'text-warning', danger: 'text-danger' }[tone];
  const icon = { info: 'ℹ', success: '✓', warning: '⚠', danger: '!' }[tone];
  return <div role={tone === 'danger' ? 'alert' : 'status'}
    className={`rounded-control border border-border bg-surface p-4 ${color}`}>
    <span aria-hidden="true">{icon}</span>{' '}{children}
  </div>;
}
