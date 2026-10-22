import {
  useEffect, useId, useRef,
  type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode,
  type SelectHTMLAttributes, type TextareaHTMLAttributes,
} from 'react';

// PUBLIC_INTERFACE
export function Button({ pending = false, children, disabled, ...props }:
  ButtonHTMLAttributes<HTMLButtonElement> & { pending?: boolean }) {
  /** Native button with explicit pending state and duplicate-click prevention. */
  return <button type="button" {...props} disabled={disabled || pending} aria-busy={pending}
    className="min-h-11 rounded-control bg-primary px-4 py-2 font-semibold text-white hover:bg-primary-hover disabled:cursor-not-allowed disabled:bg-muted">
    {children}
  </button>;
}

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

// PUBLIC_INTERFACE
export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  /** Render a native input, preserving accessible and form attributes. */
  return <input {...props} className="control" />;
}

// PUBLIC_INTERFACE
export function TextArea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  /** Render a resizable multiline input without domain validation. */
  return <textarea rows={4} {...props} className="control" />;
}

// PUBLIC_INTERFACE
export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  /** Render a native keyboard-operable select. */
  return <select {...props} className="control" />;
}

// PUBLIC_INTERFACE
export function DateInput(props: Omit<InputHTMLAttributes<HTMLInputElement>, 'type'>) {
  /** Keep date values as calendar strings rather than converting to instants. */
  return <TextInput {...props} type="date" />;
}

// PUBLIC_INTERFACE
export function RadioGroup({ legend, name, options, value, onChange, error, disabled }: {
  legend: string; name: string; options: { value: string; label: string }[];
  value: string; onChange: (value: string) => void; error?: string; disabled?: boolean;
}) {
  /** Render a labelled native radio group with an explicit caller-owned selection. */
  const id = useId();
  return <fieldset disabled={disabled} aria-describedby={error ? `${id}-error` : undefined}
    aria-invalid={Boolean(error)} className="space-y-2">
    <legend className="font-semibold">{legend}</legend>
    {options.map((option) => <label key={option.value} className="flex min-h-11 items-center gap-3">
      <input type="radio" name={name} value={option.value} checked={value === option.value}
        onChange={() => onChange(option.value)} />{option.label}
    </label>)}
    {error && <p id={`${id}-error`} className="text-danger">{error}</p>}
  </fieldset>;
}

// PUBLIC_INTERFACE
export function ErrorSummary({ errors }: { errors: { label: string; href?: string }[] }) {
  /** Focus a newly rendered error summary; links may target caller-provided field IDs. */
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { ref.current?.focus(); }, [errors]);
  if (!errors.length) return null;
  return <div ref={ref} tabIndex={-1} role="alert" className="rounded-control border border-danger p-4">
    <h2>Check the following</h2>
    <ul className="list-inside list-disc">{errors.map((error, index) =>
      <li key={index}>{error.href ? <a href={error.href}>{error.label}</a> : error.label}</li>)}</ul>
  </div>;
}

// PUBLIC_INTERFACE
export function Alert({ children, tone = 'info' }: {
  children: ReactNode; tone?: 'info' | 'success' | 'warning' | 'danger';
}) {
  /** Announce meaningful text; color is supplementary, never the only signal. */
  const color = { info: 'text-ink', success: 'text-success', warning: 'text-warning', danger: 'text-danger' }[tone];
  return <div role={tone === 'danger' ? 'alert' : 'status'}
    className={`rounded-control border border-border bg-surface p-4 ${color}`}>{children}</div>;
}

// PUBLIC_INTERFACE
export function StatusBadge({ children }: { children: ReactNode }) {
  /** Display the caller-supplied status text without calculating lifecycle policy. */
  return <span className="inline-block rounded-control border border-border px-2 py-1 text-sm font-semibold">{children}</span>;
}

// PUBLIC_INTERFACE
export function Skeleton({ label = 'Loading…' }: { label?: string }) {
  /** Announce a labelled read-in-progress state with motion-safe decoration. */
  return <div role="status" className="rounded-control bg-canvas p-4">
    <span className="motion-safe:animate-pulse">{label}</span>
  </div>;
}

// PUBLIC_INTERFACE
export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  /** Describe an empty or unavailable view without inventing business outcomes. */
  return <section className="space-y-3 rounded-control border border-border bg-surface p-6">
    <h2>{title}</h2>{children}
  </section>;
}

// PUBLIC_INTERFACE
export function DataTable<T>({ caption, columns, rows, rowKey }: {
  caption: string; columns: { key: string; heading: string; render: (row: T) => ReactNode }[];
  rows: T[]; rowKey: (row: T) => string;
}) {
  /** Render semantic tabular data in a keyboard-scrollable narrow-screen region. */
  return <div role="region" aria-label={caption} tabIndex={0} className="overflow-x-auto">
    <table className="w-full border-collapse bg-surface">
      <caption className="p-3 text-left font-semibold">{caption}</caption>
      <thead><tr>{columns.map((column) => <th key={column.key} scope="col">{column.heading}</th>)}</tr></thead>
      <tbody>{rows.map((row) => <tr key={rowKey(row)}>{columns.map((column) =>
        <td key={column.key}>{column.render(row)}</td>)}</tr>)}</tbody>
    </table>
  </div>;
}
