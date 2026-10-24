import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { ApiClient } from '../../api/client';
import { App } from '../../app/App';
import { AuthProvider } from '../auth/AuthProvider';
import { validateAction, validateCause } from './workflowValidation';

const response = (data: unknown, status = 200, etag?: string) => new Response(JSON.stringify(data), {
  status, headers: { 'Content-Type': status >= 400 ? 'application/problem+json' : 'application/json',
    ...(etag ? { ETag: etag } : {}) },
});
const captured = { id: 'a', code_at_capture: 'OLD', label_at_capture: 'Scratch' };
const defect = { id: 'd1', part_number: 'P1', quantity_affected: 1, severity: 'Major', status: 'Open',
  defect_type: captured, production_line: captured, shift: captured, revision: 7, has_photo: false };
const cause = { id: 'c1', defect_id: 'd1', text: 'Loose clamp', recorded_by_ref: 'u1' };
const action = { id: 'a1', defect_id: 'd1', description: 'Inspect clamp', owner_ref: 'owner',
  due_date: '2020-01-01', status: 'Open', revision: 8 };
const owner = { ref: 'owner', display_name: 'Assignable Owner' };
const empty = () => response({ items: [], next_cursor: null });
const failure = (status: number) => response({ code: `problem_${status}`, title: `Rejected ${status}` }, status);

async function mount(kind: string, handle?: (url: string, init?: RequestInit) => Promise<Response | undefined>) {
  const transport = vi.fn<typeof fetch>(async (url, init) => {
    const path = String(url);
    if (path.endsWith('/auth/login')) return response({ access_token: 't', token_type: 'bearer', expires_in: 3600 });
    if (path.endsWith('/me')) return response({ ref: 'u1', display_name: 'Engineer', plant_zone: 'UTC',
      permissions: ['defect.read', 'cause.create', 'defect.investigate', 'action.assign', 'action.complete'], scope: 'plant' });
    const custom = await handle?.(path, init);
    if (custom) return custom;
    if (path.endsWith('/defects/d1')) return response(defect, 200, '"7"');
    if (path.includes('/assignable-users?')) return response({ items: [owner], next_cursor: null });
    return empty();
  });
  const query = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(<QueryClientProvider client={query}><MemoryRouter initialEntries={[`/defects/d1/${kind}`]}
    future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <AuthProvider client={new ApiClient('/api/v1', transport)}><App /></AuthProvider>
  </MemoryRouter></QueryClientProvider>);
  const user = userEvent.setup();
  await user.type(screen.getByLabelText('Username'), 'engineer');
  await user.type(screen.getByLabelText('Password'), 'password');
  await user.click(screen.getByRole('button', { name: 'Sign in' }));
  await screen.findByRole('navigation', { name: 'Main navigation' });
  return { user, transport, query };
}

const writes = (transport: ReturnType<typeof vi.fn<typeof fetch>>) =>
  transport.mock.calls.filter(([url, init]) => !String(url).endsWith('/auth/login') && init?.method === 'POST');

async function fillAction(user: ReturnType<typeof userEvent.setup>, status = 'Open') {
  await screen.findByRole('option', { name: owner.display_name });
  await user.type(screen.getByLabelText('Description *'), ' Inspect clamp ');
  await user.selectOptions(screen.getByLabelText('Owner *'), 'owner');
  await user.type(screen.getByLabelText('Due date *'), '2020-01-01');
  await user.selectOptions(screen.getByLabelText('Status *'), status);
}

describe('workflow feedback constraints', () => {
  it('checks cause blank and max length while allowing a preliminary single answer', () => {
    expect(validateCause(' ')).toHaveProperty('text');
    expect(validateCause('x'.repeat(2001))).toHaveProperty('text');
    expect(validateCause(` ${'x'.repeat(2000)} `)).toEqual({});
  });
  it('checks all action fields, calendar validity, explicit status and conditional notes', () => {
    const valid = { description: 'Work', owner_ref: 'owner', due_date: '2020-01-01', status: 'Open', completion_notes: '' };
    expect(validateAction(valid, [owner])).toEqual({});
    expect(validateAction({ ...valid, description: '', owner_ref: '', due_date: '', status: '' }, [owner]))
      .toEqual(expect.objectContaining({ description: expect.any(String), owner_ref: expect.any(String), due_date: expect.any(String), status: expect.any(String) }));
    expect(validateAction({ ...valid, due_date: '2026-02-30', status: 'Complete' }, [owner]))
      .toEqual(expect.objectContaining({ due_date: expect.any(String), completion_notes: expect.any(String) }));
    expect(validateAction({ ...valid, description: 'x'.repeat(2001), status: 'Complete', completion_notes: 'x'.repeat(2001) }, [owner]))
      .toEqual(expect.objectContaining({ description: expect.any(String), completion_notes: expect.any(String) }));
  });
});

describe('workflow read states', () => {
  it('shows history usernames and journey state without exposing record UUIDs', async () => {
    const historyId = '11111111-1111-4111-8111-111111111111';
    await mount('investigation', async (url) => {
      if (url.includes('/causes?')) return response({ items: [cause], next_cursor: null });
      if (url.includes('/history?')) return response({ items: [{
        id: historyId, old_status: 'Open', new_status: 'Under Investigation',
        actor_ref: 'sample-engineer', occurred_at: '2026-01-01T12:00:00Z', aggregate_revision: 8,
      }], next_cursor: null });
      return undefined;
    });
    expect(await screen.findByText(/Changed by sample-engineer/)).toBeVisible();
    expect(screen.queryByText(new RegExp(historyId))).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Record or review cause' })).toHaveTextContent('completed');
    expect(screen.getByRole('link', { name: 'Investigation' })).toHaveAttribute('aria-current', 'step');
    expect(screen.getByRole('link', { name: 'Investigation' })).toHaveAccessibleDescription('Current step');
    const next = screen.getByRole('link', { name: 'Add corrective action' });
    expect(next).toHaveAttribute('href', '/defects/d1/actions');
    expect(next).not.toHaveAttribute('aria-current');
  });

  it('shows the saved owner even when that user is not currently assignable', async () => {
    const actionId = '22222222-2222-4222-8222-222222222222';
    await mount('actions', async (url) => url.includes('/actions?')
      ? response({ items: [{ ...action, id: actionId, owner_ref: 'sample-supervisor' }], next_cursor: null })
      : undefined);
    expect(await screen.findByText(/Owner: sample-supervisor/)).toBeVisible();
    expect(screen.queryByText(new RegExp(actionId))).not.toBeInTheDocument();
  });

  it.each(['causes', 'investigation', 'actions'])('shows parent loading at direct %s links without mutations', async (kind) => {
    await mount(kind, async (url) => url.endsWith('/defects/d1') ? new Promise(() => {}) : undefined);
    expect(screen.getByText('Loading defect…')).toBeVisible();
    expect(screen.getByRole('link', { name: 'Back to defect' })).toHaveAttribute('href', '/defects/d1');
    expect(screen.queryByText(/Part: P1/)).not.toBeInTheDocument();
  });
  it.each([403, 404, 503])('withholds protected context on parent error %s', async (status) => {
    const { transport } = await mount('causes', async (url) => url.endsWith('/defects/d1') ? failure(status) : undefined);
    if (status === 403) {
      await screen.findByText("You don't have permission to do this. Your role does not allow this action.");
      expect(screen.queryByRole('button', { name: 'Retry defect' })).not.toBeInTheDocument();
    } else await screen.findByRole('button', { name: 'Retry defect' });
    expect(screen.queryByText(/Part: P1/)).not.toBeInTheDocument();
    expect(transport.mock.calls.some(([url]) => String(url).includes('/causes?'))).toBe(false);
  });
  it.each(['loading', 'empty', 'error', 'denied'])('shows independent owner %s state', async (state) => {
    await mount('actions', async (url) => {
      if (!url.includes('/assignable-users?')) return undefined;
      if (state === 'loading') return new Promise(() => {});
      return state === 'empty' ? empty() : failure(state === 'denied' ? 403 : 503);
    });
    await screen.findByText('No corrective actions yet');
    expect(screen.getByRole('button', { name: 'Add action' })).toBeDisabled();
    if (state === 'loading') expect(screen.getByText('Loading assignable owners…')).toBeVisible();
    else if (state === 'empty') expect(await screen.findByText('No assignable owners available')).toBeVisible();
    else if (state === 'denied') {
      expect(await screen.findByText("You don't have permission to assign actions.")).toBeVisible();
      expect(screen.queryByRole('button', { name: 'Retry assignable owners' })).not.toBeInTheDocument();
    } else expect(await screen.findByRole('button', { name: 'Retry assignable owners' })).toBeVisible();
  });
  it.each(['causes', 'history', 'actions'])('shows collection error distinctly for %s', async (collection) => {
    const kind = collection === 'history' ? 'investigation' : collection;
    await mount(kind, async (url) => url.includes(`/${collection}?`) ? failure(503) : undefined);
    const label = collection === 'causes' ? 'recorded causes' : collection === 'history' ? 'status history' : 'associated actions';
    expect(await screen.findByRole('button', { name: `Retry ${label}` })).toBeVisible();
  });
});

describe('S2 record cause', () => {
  it('asks before saving a duplicate on a later page, ignoring case and extra spaces', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
    try {
      const { user, transport } = await mount('causes', async (url, init) => {
        if (url.endsWith('/causes') && init?.method === 'POST') return response(cause, 201);
        if (url.includes('/causes?')) return response({
          items: url.includes('cursor=') ? [cause] : [],
          next_cursor: url.includes('cursor=') ? null : 'later',
        });
        return undefined;
      });
      await screen.findByText('No cause recorded yet');
      await user.type(screen.getByLabelText('Why did this defect occur?'), '  LOOSE   clamp  ');
      await user.click(screen.getByRole('button', { name: 'Record cause' }));
      await waitFor(() => expect(confirm).toHaveBeenCalledOnce());
      expect(writes(transport)).toHaveLength(0);
      expect(screen.getByLabelText('Why did this defect occur?')).toHaveValue('  LOOSE   clamp  ');
      confirm.mockReturnValue(true);
      await user.click(screen.getByRole('button', { name: 'Record cause' }));
      await screen.findByText('Cause recorded');
      expect(writes(transport)).toHaveLength(1);
      expect(confirm).toHaveBeenCalledTimes(2);
    } finally {
      confirm.mockRestore();
    }
  });

  it('validates blank and max length, then confirms one additive write without If-Match', async () => {
    let saved = false;
    const { user, transport } = await mount('causes', async (url, init) => {
      if (url.endsWith('/causes') && init?.method === 'POST') { saved = true; return response(cause, 201, '"8"'); }
      if (url.includes('/causes?')) return response({ items: saved ? [cause] : [], next_cursor: null });
      return undefined;
    });
    await screen.findByText('No cause recorded yet');
    await user.click(screen.getByRole('button', { name: 'Record cause' }));
    expect(screen.getByRole('alert')).toHaveFocus();
    expect(writes(transport)).toHaveLength(0);
    fireEvent.change(screen.getByLabelText('Why did this defect occur?'), { target: { value: 'x'.repeat(2001) } });
    await user.click(screen.getByRole('button', { name: 'Record cause' }));
    expect(screen.getByLabelText('Why did this defect occur?')).toHaveAttribute('aria-invalid', 'true');
    expect(writes(transport)).toHaveLength(0);
    await user.clear(screen.getByLabelText('Why did this defect occur?'));
    await user.type(screen.getByLabelText('Why did this defect occur?'), 'Loose clamp');
    await user.click(screen.getByRole('button', { name: 'Record cause' }));
    expect(await screen.findByText('Cause recorded')).toBeVisible();
    expect(await screen.findByText('Loose clamp', { selector: 'li' })).toBeVisible();
    expect(screen.getAllByRole('link', { name: 'Investigation' })[0]).toHaveAttribute('href', '/defects/d1/investigation');
    expect(screen.getByRole('link', { name: 'Back to defect' })).toHaveAttribute('href', '/defects/d1');
    const init = writes(transport)[0][1]!;
    expect(JSON.parse(init.body as string)).toEqual({ text: 'Loose clamp' });
    expect(new Headers(init.headers).has('If-Match')).toBe(false);
  });
  it('preserves draft and maps server validation without claiming a save', async () => {
    const { user } = await mount('causes', async (_url, init) => init?.method === 'POST'
      ? response({ code: 'invalid', title: 'Check cause', field_errors: { text: 'Server cause feedback' } }, 422) : undefined);
    await screen.findByText('No cause recorded yet');
    await user.type(screen.getByLabelText('Why did this defect occur?'), 'Draft');
    await user.click(screen.getByRole('button', { name: 'Record cause' }));
    expect(await screen.findByText('Server cause feedback', { selector: 'p' })).toBeVisible();
    expect(screen.getByLabelText('Why did this defect occur?')).toHaveValue('Draft');
    expect(screen.queryByText('Cause recorded')).not.toBeInTheDocument();
  });
  it('exposes opaque child continuation rather than treating a first page as complete', async () => {
    const { user, transport } = await mount('causes', async (url) => url.includes('/causes?')
      ? response({ items: [{ ...cause, id: url.includes('cursor=') ? 'c2' : 'c1' }], next_cursor: url.includes('cursor=') ? null : 'opaque+/=' }) : undefined);
    await user.click(await screen.findByRole('button', { name: 'Load more recorded causes' }));
    await waitFor(() => expect(transport.mock.calls.some(([url]) => String(url).includes('cursor=opaque%2B%2F%3D'))).toBe(true));
  });
});

describe('S3 reviewed transition', () => {
  it.each([null, 'W/"7"', 'bad'])('blocks submission with invalid parent ETag %s', async (etag) => {
    const { user, transport } = await mount('investigation', async (url) => url.endsWith('/defects/d1')
      ? response(defect, 200, etag ?? undefined) : undefined);
    const check = await screen.findByRole('checkbox');
    await waitFor(() => expect(check).toBeEnabled());
    await user.click(check);
    await user.click(screen.getByRole('button', { name: 'Move to Under Investigation' }));
    expect(await screen.findByText(/Reload latest details, then check them/)).toBeVisible();
    expect(writes(transport)).toHaveLength(0);
  });
  it('leaves status unchanged on denied transition without inventing persona authority', async () => {
    const { user, transport } = await mount('investigation', async (_url, init) =>
      init?.method === 'POST' ? failure(403) : undefined);
    const check = await screen.findByRole('checkbox');
    await waitFor(() => expect(check).toBeEnabled());
    await user.click(check);
    await user.click(screen.getByRole('button', { name: 'Move to Under Investigation' }));
    expect(await screen.findByText("You don't have permission to move this defect to Under Investigation.")).toBeVisible();
    expect(screen.getByText('Open', { selector: 'span' })).toBeVisible();
    expect(writes(transport)).toHaveLength(1);
    expect(screen.queryByText('Moved to Under Investigation')).not.toBeInTheDocument();
  });
  it.each([400, 409, 412, 428])('handles %s without replay and requires renewed review', async (status) => {
    let revision = 7;
    const { user, transport } = await mount('investigation', async (url, init) => {
      if (url.endsWith('/defects/d1')) return response({ ...defect, revision }, 200, `"${revision}"`);
      if (url.endsWith('/transitions') && init?.method === 'POST') { revision = 8; return failure(status); }
      return undefined;
    });
    const check = await screen.findByRole('checkbox');
    await waitFor(() => expect(check).toBeEnabled());
    const submit = screen.getByRole('button', { name: 'Move to Under Investigation' });
    await user.click(submit);
    expect(writes(transport)).toHaveLength(0);
    await user.click(check);
    await user.click(submit);
    await screen.findByText(status === 412 ? /Someone else updated this defect/
      : status === 409 ? /This can't be done right now/ : status === 400 ? /Something went wrong with this request/ : /Please tick the box/);
    await waitFor(() => expect(screen.getByRole('checkbox')).toBeEnabled());
    expect(screen.getByRole('checkbox')).not.toBeChecked();
    expect(writes(transport)).toHaveLength(1);
    expect(new Headers(writes(transport)[0][1]!.headers).get('If-Match')).toBe('"7"');
    await user.click(screen.getByRole('button', { name: 'Move to Under Investigation' }));
    expect(writes(transport)).toHaveLength(1);
    await user.click(screen.getByRole('checkbox'));
    await user.click(screen.getByRole('button', { name: 'Move to Under Investigation' }));
    await waitFor(() => expect(writes(transport)).toHaveLength(2));
    expect(new Headers(writes(transport)[1][1]!.headers).get('If-Match')).toBe('"8"');
  });
  it('does not mutate on entry and displays actual committed status and attributable history', async () => {
    let transitioned = false;
    const { user, transport } = await mount('investigation', async (url, init) => {
      if (url.endsWith('/transitions') && init?.method === 'POST') { transitioned = true; return response({ ...defect, status: 'Under Investigation' }, 200, '"8"'); }
      if (url.endsWith('/defects/d1')) return response({ ...defect, status: transitioned ? 'Under Investigation' : 'Open' }, 200, transitioned ? '"8"' : '"7"');
      if (url.includes('/history?')) return response({ items: transitioned ? [{
        id: 'h1', old_status: 'Open', new_status: 'Under Investigation', actor_ref: 'actor',
        occurred_at: '2026-01-01T12:00:00Z', aggregate_revision: 8,
      }] : [], next_cursor: null });
      return undefined;
    });
    const check = await screen.findByRole('checkbox');
    await waitFor(() => expect(check).toBeEnabled());
    expect(writes(transport)).toHaveLength(0);
    await user.click(check);
    await user.click(screen.getByRole('button', { name: 'Move to Under Investigation' }));
    expect(await screen.findByText('Moved to Under Investigation')).toBeVisible();
    expect(await screen.findByText(/Open → Under Investigation ·/)).toBeVisible();
    expect(screen.getByRole('checkbox')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Move to Under Investigation' })).toBeDisabled();
    expect(screen.getByRole('heading', { name: 'Investigation' })).toBeVisible();
    expect(screen.getAllByRole('link', { name: 'Add corrective action' })[0]).toHaveAttribute('href', '/defects/d1/actions');
    expect(JSON.parse(writes(transport)[0][1]!.body as string)).toEqual({ target_status: 'Under Investigation' });
  });
});

describe('S4 add corrective action', () => {
  it('keeps confirmed success distinct from a subsequent failed parent refresh', async () => {
    let saved = false;
    const { user } = await mount('actions', async (url, init) => {
      if (init?.method === 'POST') { saved = true; return response(action, 201, '"8"'); }
      if (saved && url.endsWith('/defects/d1')) return failure(503);
      return undefined;
    });
    await fillAction(user);
    await user.click(screen.getByRole('button', { name: 'Add action' }));
    expect(await screen.findByText('Corrective action added')).toBeVisible();
    expect(await screen.findByRole('button', { name: 'Retry defect' })).toBeVisible();
    expect(screen.getByText('Corrective action added')).toBeVisible();
  });
  it('retains action fields and does not show success after assignment denial', async () => {
    const { user, transport } = await mount('actions', async (_url, init) => init?.method === 'POST' ? failure(403) : undefined);
    await fillAction(user);
    await user.click(screen.getByRole('button', { name: 'Add action' }));
    expect(await screen.findByText("You don't have permission to add corrective actions.")).toBeVisible();
    expect(screen.getByLabelText('Description *')).toHaveValue(' Inspect clamp ');
    expect(screen.queryByText('Corrective action added')).not.toBeInTheDocument();
    expect(writes(transport)).toHaveLength(1);
  });
  it('validates required input and conditional notes, preserves actions and sends explicit status without If-Match', async () => {
    let saved = false;
    const { user, transport } = await mount('actions', async (url, init) => {
      if (url.endsWith('/actions') && init?.method === 'POST') { saved = true; return response({ ...action, status: 'Complete' }, 201, '"8"'); }
      if (url.includes('/actions?')) return response({ items: saved ? [action, { ...action, id: 'a2', description: 'Second action' }] : [action], next_cursor: null });
      return undefined;
    });
    await screen.findByRole('option', { name: owner.display_name });
    expect(screen.getByLabelText('Status *')).toHaveValue('');
    await user.click(screen.getByRole('button', { name: 'Add action' }));
    expect(screen.getByLabelText('Description *')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByLabelText('Owner *')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByLabelText('Due date *')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByLabelText('Status *')).toHaveAttribute('aria-invalid', 'true');
    await fillAction(user, 'Complete');
    await user.click(screen.getByRole('button', { name: 'Add action' }));
    expect(screen.getByLabelText('Completion notes *')).toHaveAttribute('aria-invalid', 'true');
    expect(writes(transport)).toHaveLength(0);
    await user.type(screen.getByLabelText('Completion notes *'), ' Done ');
    await user.click(screen.getByRole('button', { name: 'Add action' }));
    expect(await screen.findByText('Corrective action added')).toBeVisible();
    expect(await screen.findByText(/Second action · 2020/)).toBeVisible();
    expect(screen.getByText(/Inspect clamp · 2020/)).toBeVisible();
    expect(screen.getAllByRole('link', { name: 'Back to defect' })[0]).toHaveAttribute('href', '/defects/d1');
    const init = writes(transport)[0][1]!;
    expect(new Headers(init.headers).has('If-Match')).toBe(false);
    expect(JSON.parse(init.body as string)).toEqual({ description: 'Inspect clamp', owner_ref: 'owner', due_date: '2020-01-01', status: 'Complete', completion_notes: 'Done' });
  });
  it('disables duplicate pending writes, then labels network uncertainty and preserves the draft', async () => {
    let reject!: (reason: Error) => void;
    const { user, transport } = await mount('actions', async (_url, init) =>
      init?.method === 'POST' ? new Promise((_resolve, fail) => { reject = fail; }) : undefined);
    await fillAction(user);
    await user.click(screen.getByRole('button', { name: 'Add action' }));
    expect(screen.getByRole('button', { name: 'Adding corrective action…' })).toBeDisabled();
    reject(new TypeError('Network'));
    expect(await screen.findByText(/We couldn't confirm whether this was saved/)).toBeVisible();
    await waitFor(() => expect(screen.getByLabelText('Description *')).toHaveValue(' Inspect clamp '));
    expect(writes(transport)).toHaveLength(1);
    expect(screen.queryByText('Corrective action added')).not.toBeInTheDocument();
  });
});
