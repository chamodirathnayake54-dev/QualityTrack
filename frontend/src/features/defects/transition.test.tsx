import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { transitionChoices } from './useTransition';
import { EventList } from './WorkflowViews';

describe('transition choices', () => {
  const permissions = ['action.progress', 'action.complete', 'action.reopen', 'defect.close', 'defect.reopen'];
  it.each([
    ['Open', true, ['Start action', 'Complete action']],
    ['In Progress', true, ['Complete action']],
    ['Complete', true, ['Reopen action']],
    ['Open', false, []],
    ['Under Investigation', false, ['Close defect']],
    ['Closed', false, ['Reopen defect']],
  ] as const)('prepares choices for %s (action=%s)', (status, action, labels) => {
    expect(transitionChoices(status, permissions, action).map((choice) => choice.label)).toEqual(labels);
    expect(transitionChoices(status, [], action)).toEqual([]);
  });

  it('requires distinct evidence for completion and reopening', () => {
    expect(transitionChoices('Open', ['action.complete'], true)).toEqual([
      { label: 'Complete action', target: 'Complete', evidence: 'completion_notes' },
    ]);
    expect(transitionChoices('Complete', ['action.reopen'], true)).toEqual([
      { label: 'Reopen action', target: 'In Progress', evidence: 'reopen_reason' },
    ]);
  });
});

describe('shared history presentation', () => {
  it('shows creation, actor, plant-zone timestamp and optional action evidence', () => {
    const occurred_at = '2026-01-01T12:00:00Z';
    render(<EventList zone="America/New_York" events={[{
      id: 'hidden-event-id', old_status: null as unknown as string, new_status: 'Complete',
      actor_ref: 'worker', occurred_at, aggregate_revision: 3,
      completion_notes: 'Repair checked', reopen_reason: 'More work needed',
    }]} />);
    expect(screen.getByText(/Created → Complete · Changed by worker/)).toBeVisible();
    expect(screen.getByText(/Created → Complete/)).toHaveTextContent(
      new Intl.DateTimeFormat(undefined, {
        dateStyle: 'medium', timeStyle: 'long', timeZone: 'America/New_York',
      }).format(new Date(occurred_at)),
    );
    expect(screen.getByText('Completion notes: Repair checked')).toBeVisible();
    expect(screen.getByText('Reason for reopening: More work needed')).toBeVisible();
    expect(screen.queryByText('hidden-event-id')).not.toBeInTheDocument();
  });
});
