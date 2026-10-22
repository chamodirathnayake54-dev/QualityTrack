import { useId } from 'react';

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
