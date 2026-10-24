import type { ReactNode } from 'react';

// PUBLIC_INTERFACE
export function Alert({ children, tone = 'info' }: {
  children: ReactNode; tone?: 'info' | 'success' | 'warning' | 'danger';
}) {
  /** Announce meaningful text; decorative icons and color supplement the message. */
  const styles = {
    info: 'border-blue-200 bg-blue-50 text-ink',
    success: 'border-green-200 bg-green-50 text-success',
    warning: 'border-amber-200 bg-amber-50 text-warning',
    danger: 'border-red-200 bg-red-50 text-danger',
  };
  const icons = { info: 'ⓘ', success: '✓', warning: '⚠', danger: '!' };
  return <div role={tone === 'danger' ? 'alert' : 'status'}
    className={`flex items-start gap-3 rounded-control border p-4 ${styles[tone]}`}>
    <span aria-hidden="true" className="shrink-0 font-bold">{icons[tone]}</span>
    <div className="min-w-0 space-y-2">{children}</div>
  </div>;
}
