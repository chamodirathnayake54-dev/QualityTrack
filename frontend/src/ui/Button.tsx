import type { ButtonHTMLAttributes } from 'react';

// PUBLIC_INTERFACE
export function Button({ pending = false, children, disabled, ...props }:
  ButtonHTMLAttributes<HTMLButtonElement> & { pending?: boolean }) {
  /** Native button with explicit pending state and duplicate-click prevention. */
  return <button type="button" {...props} disabled={disabled || pending} aria-busy={pending}
    className={`ui-button ${props.className ?? ''}`}>
    {children}
  </button>;
}
