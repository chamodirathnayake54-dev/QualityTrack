import type { Capture, Lookup } from '../../api/defects';

export const severities = ['Critical', 'Major', 'Minor'];
export const statuses = ['Open', 'Under Investigation', 'Closed'];
export const lookupFields = [
  { key: 'defect_type_id', path: '/defect-types', label: 'Defect type' },
  { key: 'production_line_id', path: '/production-lines', label: 'Production line' },
  { key: 'shift_id', path: '/shifts', label: 'Shift' },
] as const;
export type LookupKey = typeof lookupFields[number]['key'];
export type Choices = Record<LookupKey, Lookup[]>;
export type Draft = Record<keyof Capture, string>;
export type Errors = Record<string, string>;

// PUBLIC_INTERFACE
export function validateCapture(draft: Draft, choices: Choices): Errors {
  /** Mirror documented input constraints for feedback; the API still decides acceptance. */
  const errors: Errors = {};
  const part = draft.part_number.trim();
  if (!part) errors.part_number = 'Enter a part number';
  else if (part.length > 50) errors.part_number = 'Part number must be 1–50 trimmed characters';
  const quantity = Number(draft.quantity_affected);
  if (!draft.quantity_affected.trim() || !Number.isInteger(quantity) || quantity < 1 || quantity > 1000000) {
    errors.quantity_affected = 'Enter a positive whole number from 1 to 1,000,000';
  }
  for (const field of lookupFields) {
    if (!choices[field.key].some((choice) => choice.id === draft[field.key] && !choice.retired)) {
      errors[field.key] = `Select an active ${field.label.toLowerCase()}`;
    }
  }
  if (!severities.includes(draft.severity)) errors.severity = 'Select Critical, Major, or Minor';
  return errors;
}

// PUBLIC_INTERFACE
export function validateFilters(params: URLSearchParams): Errors {
  /** Check paired calendar dates and the bounded page size before requesting. */
  const errors: Errors = {};
  const start = params.get('start_date') ?? '';
  const end = params.get('end_date') ?? '';
  const validDate = (value: string) => /^\d{4}-\d{2}-\d{2}$/.test(value) &&
    value.slice(0, 4) !== '0000' &&
    !Number.isNaN(Date.parse(`${value}T00:00:00Z`)) &&
    new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) === value;
  if (Boolean(start) !== Boolean(end)) errors.dates = 'Supply both start and end dates';
  else if (start && end && start > end) errors.dates = 'End date must be on or after the start date';
  else if (start && (!validDate(start) || !validDate(end) || end === '9999-12-31')) {
    errors.dates = 'Enter a valid date range ending before 9999-12-31';
  }
  const limit = Number(params.get('limit') ?? 50);
  if (!Number.isInteger(limit) || limit < 1 || limit > 100) errors.limit = 'Page size must be an integer from 1 to 100';
  if (params.get('severity') && !severities.includes(params.get('severity')!)) errors.severity = 'Select a supported severity';
  if (params.get('status') && !statuses.includes(params.get('status')!)) errors.status = 'Select a supported status';
  return errors;
}
