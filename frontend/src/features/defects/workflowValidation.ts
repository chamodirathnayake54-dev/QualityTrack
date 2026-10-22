import type { Errors } from './validation';
import type { Owner } from '../../api/workflow';
export type { Owner } from '../../api/workflow';

export const actionStatuses = ['Open', 'In Progress', 'Complete'] as const;
export type ActionDraft = {
  description: string; owner_ref: string; due_date: string; status: string; completion_notes: string;
};

// PUBLIC_INTERFACE
export function validateCause(text: string): Errors {
  /** Mirror the trimmed nonblank and 2,000-character cause contract. */
  if (!text.trim()) return { text: 'Record at least one nonblank cause before moving to Under Investigation' };
  return [...text.trim()].length > 2000 ? { text: 'Cause must be at most 2,000 characters' } : {};
}

// PUBLIC_INTERFACE
export function validateAction(draft: ActionDraft, owners: Owner[]): Errors {
  /** Validate input completeness only; the server decides authority and eligibility. */
  const errors: Errors = {};
  if (!draft.description.trim()) errors.description = 'Enter an action description';
  else if ([...draft.description.trim()].length > 2000) errors.description = 'Description must be at most 2,000 characters';
  if (!owners.some((owner) => owner.ref === draft.owner_ref)) errors.owner_ref = 'Select an assignable owner';
  const date = draft.due_date;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || date.startsWith('0000') ||
      Number.isNaN(Date.parse(`${date}T00:00:00Z`)) ||
      new Date(`${date}T00:00:00Z`).toISOString().slice(0, 10) !== date) {
    errors.due_date = 'Enter a valid due date';
  }
  if (!actionStatuses.includes(draft.status as typeof actionStatuses[number])) errors.status = 'Select an action status';
  if (draft.status === 'Complete') {
    if (!draft.completion_notes.trim()) errors.completion_notes = 'Enter completion notes';
    else if ([...draft.completion_notes.trim()].length > 2000) errors.completion_notes = 'Completion notes must be at most 2,000 characters';
  }
  return errors;
}
