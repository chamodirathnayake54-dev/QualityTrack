import { useEffect, useRef } from 'react';

// PUBLIC_INTERFACE
export function ErrorSummary({ errors }: { errors: { label: string; href?: string }[] }) {
  /** Focus a newly rendered error summary; links may target caller-provided field IDs. */
  const ref = useRef<HTMLDivElement>(null);
  const signature = JSON.stringify(errors);
  useEffect(() => { ref.current?.focus(); }, [signature]);
  if (!errors.length) return null;
  return <div ref={ref} tabIndex={-1} role="alert" className="rounded-control border border-danger p-4">
    <h2>Check the following</h2>
    <ul className="list-inside list-disc">{errors.map((error, index) =>
      <li key={index}>{error.href ? <a href={error.href}>{error.label}</a> : error.label}</li>)}</ul>
  </div>;
}
