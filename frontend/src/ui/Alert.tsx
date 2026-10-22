import type { ReactNode } from 'react';

// PUBLIC_INTERFACE
export function Alert({ children, tone = 'info' }: {
  children: ReactNode; tone?: 'info' | 'success' | 'warning' | 'danger';
}) {
  /** Announce meaningful text; colour and hidden decorative icons supplement it. */
  const appearance = {
    info: 'border-blue-200 bg-blue-50 text-blue-900',
    success: 'border-green-200 bg-green-50 text-green-900',
    warning: 'border-amber-200 bg-amber-50 text-amber-900',
    danger: 'border-red-200 bg-red-50 text-red-900',
  }[tone];
  const icon = { info: 'ⓘ', success: '✓', warning: '△', danger: '!' }[tone];
  return <div role={tone === 'danger' ? 'alert' : 'status'}
    className={`flex items-start gap-3 rounded-control border p-4 ${appearance}`}>
    <span aria-hidden="true" className="text-xl font-bold">{icon}</span>
    <div className="min-w-0 space-y-2">{children}</div>
  </div>;
}
