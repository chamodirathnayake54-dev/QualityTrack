import type { ReactNode } from 'react';

const tones: Record<string, string> = {
  Open: 'border-blue-200 bg-blue-50 text-blue-900',
  'Under Investigation': 'border-amber-200 bg-amber-50 text-amber-900',
  Closed: 'border-slate-300 bg-slate-100 text-slate-800',
  Complete: 'border-green-200 bg-green-50 text-green-900',
  'In Progress': 'border-blue-200 bg-blue-50 text-blue-900',
  Minor: 'border-slate-300 bg-slate-100 text-slate-800',
  Major: 'border-amber-200 bg-amber-50 text-amber-900',
  Critical: 'border-red-200 bg-red-50 text-red-900',
};

// PUBLIC_INTERFACE
export function StatusBadge({ children }: { children: ReactNode }) {
  /** Add supplementary colour to caller-supplied text, with a neutral fallback. */
  const tone = typeof children === 'string' ? tones[children] : undefined;
  return <span className={`inline-block whitespace-nowrap rounded-full border px-3 py-1 text-sm font-semibold ${tone ?? 'border-border bg-canvas text-ink'}`}>
    {children}
  </span>;
}
