import { useId, type ReactNode } from 'react';

type FieldControl = { id: string; 'aria-describedby'?: string; 'aria-invalid': boolean };

// PUBLIC_INTERFACE
export function Field({ label, hint, error, children }: {
  label: string; hint?: string; error?: string; children: (props: FieldControl) => ReactNode;
}) {
  /** Supply stable label and description relationships to a caller-rendered control. */
  const id = useId();
  const describedBy = [hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(' ') || undefined;
  return <div className="space-y-2">
    <label htmlFor={id} className="block font-semibold">{label}</label>
    {hint && <p id={`${id}-hint`} className="text-sm text-muted">{hint}</p>}
    {children({ id, 'aria-describedby': describedBy, 'aria-invalid': Boolean(error) })}
    {error && <p id={`${id}-error`} className="text-danger">{error}</p>}
  </div>;
}
