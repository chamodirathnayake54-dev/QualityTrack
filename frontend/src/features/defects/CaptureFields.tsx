import { Field, RadioGroup, Select, TextInput } from '../../ui';
import { lookupFields, severities, type Choices, type Draft, type Errors } from './validation';

// PUBLIC_INTERFACE
export function CaptureFields({ draft, errors, choices, update }: {
  draft: Draft; errors: Errors; choices: Choices; update: (key: keyof Draft, value: string) => void;
}) {
  /** Render prepared capture values and errors; no requests or business acceptance decisions. */
  return <>
    <Field label="Part number *" error={errors.part_number}>{(props) =>
      <TextInput {...props} value={draft.part_number} onChange={(event) => update('part_number', event.target.value)} />}</Field>
    <Field label="Quantity affected *" error={errors.quantity_affected}>{(props) =>
      <TextInput {...props} type="number" min={1} max={1000000} step={1} value={draft.quantity_affected}
        onChange={(event) => update('quantity_affected', event.target.value)} />}</Field>
    {lookupFields.map((field) => <Field key={field.key} label={`${field.label} *`} error={errors[field.key]}>{(props) =>
      <Select {...props} value={draft[field.key]} onChange={(event) => update(field.key, event.target.value)}>
        <option value="">Select {field.label.toLowerCase()}</option>
        {choices[field.key].map((choice) => <option key={choice.id} value={choice.id}>{choice.code} — {choice.label}</option>)}
      </Select>}</Field>)}
    <RadioGroup legend="Severity *" name="severity" options={severities.map((value) => ({ value, label: value }))}
      value={draft.severity} onChange={(value) => update('severity', value)} error={errors.severity} />
  </>;
}
