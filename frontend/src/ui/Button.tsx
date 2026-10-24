import type { ButtonHTMLAttributes } from 'react';

// PUBLIC_INTERFACE
export function Button({ pending = false, variant = 'secondary', children, disabled, ...props }:
  ButtonHTMLAttributes<HTMLButtonElement> & { pending?: boolean; variant?: 'primary' | 'secondary' }) {
  /** Native button with explicit pending state and duplicate-click prevention. */
  return <button type="button" {...props} disabled={disabled || pending} aria-busy={pending}
    className={`ui-button ${variant === 'primary' ? 'ui-button-primary' : ''} ${props.className ?? ''}`}>
    {children}
  </button>;
}
