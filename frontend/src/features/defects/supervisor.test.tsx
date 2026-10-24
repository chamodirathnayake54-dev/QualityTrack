import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { ApiClient } from '../../api/client';
import { App } from '../../app/App';
import { AuthProvider } from '../auth/AuthProvider';

const lookup = { id: 'l', code_at_capture: 'L', label_at_capture: 'Line one' };
const response = (data: unknown, status = 200, etag?: string) => new Response(JSON.stringify(data), {
  status, headers: { 'Content-Type': status >= 400 ? 'application/problem+json' : 'application/json',
    ...(etag ? { ETag: etag } : {}) },
});

async function mount({ permissions, status = 'Under Investigation', actionStatus = 'Complete', refusal = false, route = '', failureStatus,
  actorRef = 'sample-supervisor', ownerRef = 'u' }: {
  permissions: string[]; status?: string; actionStatus?: string; refusal?: boolean; route?: string; failureStatus?: number;
  actorRef?: string; ownerRef?: string;
}) {
  let current = status;
  let revision = 9;
  let savedAction = actionStatus;
  const transport = vi.fn<typeof fetch>(async (url, init) => {
    const path = String(url);
    if (path.endsWith('/auth/login')) return response({ access_token: 't', expires_in: 3600 });
    if (path.endsWith('/me')) return response({ ref: actorRef, display_name: 'Reader', plant_zone: 'America/New_York', permissions });
    if (init?.method === 'POST') {
      if (failureStatus) {
        revision++;
        return response({ code: 'refused', title: 'Refused' }, failureStatus);
      }
      if (refusal) return response({ code: 'actions_incomplete', title: 'Incomplete' }, 409);
      const body = JSON.parse(init.body as string);
      if (path.includes('/actions/a/')) savedAction = body.target_status;
      else current = body.target_status;
      revision++;
      return response({}, 200, `"${revision}"`);
    }
    if (path.endsWith('/defects/d')) return response({
      id: 'd', part_number: 'P1', quantity_affected: 2, severity: 'Major', status: current,
      defect_type: lookup, production_line: lookup, shift: lookup, created_by_ref: 'logger',
      created_at: '2026-01-01T12:00:00Z', revision, has_photo: false,
    }, 200, `"${revision}"`);
    if (path.includes('/actions?')) return response({ items: [{
      id: 'a', defect_id: 'd', description: 'Fix clamp', owner_ref: ownerRef, due_date: '2026-01-02',
      status: savedAction, revision: 1,
    }], next_cursor: null });
    if (path.includes('/actions/a/history?')) return response({ items: [{
      id: 'h', old_status: 'Open', new_status: 'Complete', actor_ref: 'worker',
      occurred_at: '2026-01-01T12:00:00Z', completion_notes: 'Clamp checked', reopen_reason: null,
    }], next_cursor: null });
    if (path.includes('/causes?')) return response({ items: [{
      id: 'c', defect_id: 'd', text: 'Loose clamp', recorded_by_ref: 'cause-author',
      recorded_at: '2026-01-01T12:00:00Z', revision,
    }, {
      id: 'c2', defect_id: 'd', text: 'Worn seal', recorded_by_ref: 'second-author',
      recorded_at: '2026-01-02T12:00:00Z', revision,
    }], next_cursor: null });
    return response({ items: [], next_cursor: null });
  });
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter initialEntries={[`/defects/d${route}`]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider client={new ApiClient('/api/v1', transport)}><App /></AuthProvider>
    </MemoryRouter>
  </QueryClientProvider>);
  const user = userEvent.setup();
  await user.type(screen.getByLabelText('Username'), 'reader');
  await user.type(screen.getByLabelText('Password'), 'password');
  await user.click(screen.getByRole('button', { name: 'Sign in' }));
  if (route === '/causes' && permissions.includes('cause.create')) {
    await screen.findByLabelText('Why did this defect occur?');
  } else await screen.findByText('Quantity affected: 2');
  const writes = () => transport.mock.calls.filter(([url, init]) =>
    init?.method === 'POST' && !String(url).endsWith('/auth/login'));
  return { user, transport, writes };
}

async function confirm(user: ReturnType<typeof userEvent.setup>, label: string) {
  const region = await screen.findByRole('region', { name: label });
  const checkbox = within(region).getByRole('checkbox');
  await waitFor(() => expect(checkbox).toBeEnabled());
  await user.click(checkbox);
  await user.click(within(region).getByRole('button', { name: `Confirm ${label.toLowerCase()}` }));
}

describe('supervisor workflows and read-only summary', () => {
  it.each(['sample-engineer', 'sample-supervisor'])('shows completion to owner or supervisor %s', async (actorRef) => {
    await mount({ permissions: ['defect.read', 'action.complete'], actionStatus: 'In Progress',
      actorRef, ownerRef: 'sample-engineer' });
    expect(await screen.findByLabelText('Completion notes *')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Confirm complete action' })).toBeVisible();
  });

  it('hides all update controls from an engineer on a supervisor-owned action', async () => {
    const { writes } = await mount({ permissions: ['defect.read', 'action.progress', 'action.complete', 'action.reopen'],
      actionStatus: 'Open', actorRef: 'sample-engineer', ownerRef: 'sample-supervisor' });
    const card = await screen.findByRole('article', { name: 'Fix clamp' });
    expect(within(card).getByText('Only sample-supervisor or a supervisor can update this action.')).toBeVisible();
    expect(card.querySelector('form')).toBeNull();
    expect(within(card).queryByRole('checkbox')).not.toBeInTheDocument();
    expect(within(card).queryByRole('button')).not.toBeInTheDocument();
    expect(writes()).toHaveLength(0);
  });

  it.each(['', '/causes'])('attributes every cause in plant time at %s', async (route) => {
    await mount({ permissions: ['defect.read', 'cause.create'], route });
    for (const [author, at] of [['cause-author', '2026-01-01T12:00:00Z'], ['second-author', '2026-01-02T12:00:00Z']]) {
      const attribution = await screen.findByText(new RegExp(`Recorded by ${author}`));
      expect(attribution).toHaveTextContent(new Intl.DateTimeFormat(undefined, {
        dateStyle: 'medium', timeStyle: 'long', timeZone: 'America/New_York',
      }).format(new Date(at)));
    }
  });

  it.each([
    ['Open', 'action.progress', 'Start action'],
    ['Complete', 'action.reopen', 'Reopen action'],
  ])('transitions an action from %s with the required grant and evidence', async (actionStatus, permission, label) => {
    const { user, writes } = await mount({ permissions: ['defect.read', permission], actionStatus });
    if (actionStatus === 'Complete') {
      await user.type(await screen.findByLabelText('Reason for reopening *'), 'Needs more work');
    }
    await confirm(user, label);
    expect(await screen.findByText(`${label} saved.`)).toBeVisible();
    expect(writes()).toHaveLength(1);
    expect(JSON.parse(writes()[0][1]?.body as string)).toEqual({
      target_status: 'In Progress', ...(actionStatus === 'Complete' ? { reopen_reason: 'Needs more work' } : {}),
    });
  });

  it.each([403, 412])('handles server %s without retrying a transition', async (failureStatus) => {
    const { user, writes } = await mount({ permissions: ['defect.read', 'defect.close'], failureStatus });
    await confirm(user, 'Close defect');
    expect(await screen.findByText(failureStatus === 403
      ? "You don't have permission to do this. Your role does not allow this action."
      : 'Someone else updated this defect. We loaded the latest details. Please check them and try again.')).toBeVisible();
    await waitFor(() => expect(screen.getByRole('checkbox')).not.toBeChecked());
    expect(writes()).toHaveLength(1);
    expect(screen.queryByRole('button', { name: /Retry/ })).not.toBeInTheDocument();
    if (failureStatus === 412) {
      await confirm(user, 'Close defect');
      expect(new Headers(writes()[1][1]?.headers).get('If-Match')).toBe('"10"');
    }
  });

  it('closes with all actions complete, then reopens using each reviewed parent revision', async () => {
    const { user, writes } = await mount({ permissions: ['defect.read', 'defect.close', 'defect.reopen'] });
    await confirm(user, 'Close defect');
    expect(await screen.findByText('Closed', { selector: 'span' })).toBeVisible();
    await confirm(user, 'Reopen defect');
    expect(await screen.findByText('Under Investigation', { selector: 'span' })).toBeVisible();
    expect(writes()).toHaveLength(2);
    expect(new Headers(writes()[0][1]?.headers).get('If-Match')).toBe('"9"');
    expect(new Headers(writes()[1][1]?.headers).get('If-Match')).toBe('"10"');
    expect(JSON.parse(writes()[0][1]?.body as string)).toEqual({ target_status: 'Closed' });
  });

  it('shows the exact closure refusal, never retries, and requires renewed review', async () => {
    const { user, writes } = await mount({ permissions: ['defect.read', 'defect.close'], actionStatus: 'Open', refusal: true });
    await confirm(user, 'Close defect');
    expect(await screen.findByText("This can't be closed yet: all corrective actions must be completed first.")).toBeVisible();
    expect(writes()).toHaveLength(1);
    expect(screen.getByRole('checkbox')).not.toBeChecked();
    expect(screen.getByRole('button', { name: 'Confirm close defect' })).toBeDisabled();
  });

  it.each(['Under Investigation', 'Closed'])('does not show supervisor controls to an engineer at %s', async (status) => {
    await mount({ permissions: ['defect.read', 'cause.create', 'defect.investigate', 'action.assign'], status });
    expect(screen.queryByRole('region', { name: 'Close defect' })).not.toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Reopen defect' })).not.toBeInTheDocument();
  });

  it.each(['', '/causes', '/investigation', '/actions'])('shows an auditor no forms at %s', async (route) => {
    const { writes } = await mount({ permissions: ['defect.read'], route });
    expect(await screen.findByText('Completion notes: Clamp checked')).toBeVisible();
    expect(document.querySelector('form')).toBeNull();
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Add corrective action' })).not.toBeInTheDocument();
    expect(writes()).toHaveLength(0);
  });

  it('requires completion notes and uses the parent ETag rather than the action revision', async () => {
    const { user, writes } = await mount({ permissions: ['defect.read', 'action.complete'], actionStatus: 'In Progress' });
    await confirm(user, 'Complete action');
    expect(await screen.findByText('Add notes between 1 and 2000 characters before confirming.')).toBeVisible();
    expect(writes()).toHaveLength(0);
    await user.type(screen.getByLabelText('Completion notes *'), 'Clamp repaired');
    await user.click(screen.getByRole('button', { name: 'Confirm complete action' }));
    await waitFor(() => expect(writes()).toHaveLength(1));
    expect(new Headers(writes()[0][1]?.headers).get('If-Match')).toBe('"9"');
    expect(JSON.parse(writes()[0][1]?.body as string)).toEqual({ target_status: 'Complete', completion_notes: 'Clamp repaired' });
  });
});
