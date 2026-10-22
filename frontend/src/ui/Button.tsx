import type { ButtonHTMLAttributes } from 'react';

// PUBLIC_INTERFACE
export function Button({ pending = false, children, disabled, ...props }:
  ButtonHTMLAttributes<HTMLButtonElement> & { pending?: boolean }) {
  /** Native button with explicit pending state and duplicate-click prevention. */
  return <button type="button" {...props} disabled={disabled || pending} aria-busy={pending}
    className="min-h-11 rounded-control bg-primary px-4 py-2 font-semibold text-white hover:bg-primary-hover disabled:cursor-not-allowed disabled:bg-muted">
    {children}
  </button>;
}
