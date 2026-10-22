import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { ApiClient } from '../../api/client';
import { App } from '../../app/App';
import { AuthProvider } from '../auth/AuthProvider';
import { validateCapture, validateFilters, type Choices, type Draft } from './validation';

const response = (data: unknown, status = 200, etag?: string) => new Response(JSON.stringify(data), {
  status, headers: { 'Content-Type': status >= 400 ? 'application/problem+json' : 'application/json', ...(etag ? { ETag: etag } : {}) },
});
const choice = { id: 'a', code: 'A', label: 'Active' };
const captured = { id: 'a', code_at_capture: 'OLD', label_at_capture: 'Historical' };
const defect = { id: 'd1', part_number: 'P1', quantity_affected: 1, severity: 'Major', status: 'Open',
  defect_type: captured, production_line: captured, shift: captured, created_at: '2026-01-01T12:00:00Z',
  created_by_ref: 'u1', revision: 1, has_photo: false };
const choices: Choices = { defect_type_id: [choice], production_line_id: [choice], shift_id: [choice] };
const valid: Draft = { part_number: ' P1 ', quantity_affected: '1', severity: 'Major',
  defect_type_id: 'a', production_line_id: 'a', shift_id: 'a' };

async function mount(path: string, handle: (url: string, init?: RequestInit) => Promise<Response>, permissions = ['defect.read', 'defect.capture']) {
  const transport = vi.fn<typeof fetch>(async (url, init) => {
    const path = String(url);
    if (path.endsWith('/auth/login')) return response({ access_token: 't', expires_in: 3600, token_type: 'bearer' });
    if (path.endsWith('/me')) return response({ ref: 'u1', display_name: 'Engineer', plant_zone: 'UTC', scope: 'plant', permissions });
    return handle(path, init);
  });
  const query = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(<QueryClientProvider client={query}><MemoryRouter initialEntries={[path]}
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

const lookupResponse = async () => response({ items: [choice, { ...choice, id: 'retired', label: 'Retired', retired: true }], next_cursor: null });

async function fill(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText('Part number *'), ' P1 ');
  await user.type(screen.getByLabelText('Quantity affected *'), '3');
  for (const label of ['Defect type *', 'Production line *', 'Shift *']) await user.selectOptions(screen.getByLabelText(label), 'a');
  await user.click(screen.getByLabelText('Major'));
}

describe('capture validation contract', () => {
  it('accepts trimmed boundaries and requires explicit active choices and severity', () => {
    expect(validateCapture(valid, choices)).toEqual({});
    expect(validateCapture({ ...valid, part_number: ` ${'x'.repeat(50)} `, quantity_affected: '1000000' }, choices)).toEqual({});
    const errors = validateCapture({ ...valid, part_number: ' ', severity: '', defect_type_id: 'retired' }, choices);
    expect(errors).toHaveProperty('part_number');
    expect(errors).toHaveProperty('severity');
    expect(errors).toHaveProperty('defect_type_id');
    expect(validateCapture({ ...valid, part_number: 'x'.repeat(51) }, choices)).toHaveProperty('part_number');
  });
  it.each(['0', '-1', '1.5', '1000001', '', 'Infinity'])('rejects quantity %s', (quantity_affected) => {
    expect(validateCapture({ ...valid, quantity_affected }, choices)).toHaveProperty('quantity_affected');
  });
  it.each(['start_date=2026-01-01', 'start_date=2026-02-02&end_date=2026-02-01',
    'start_date=2026-01-01&end_date=9999-12-31', 'start_date=2026-02-30&end_date=2026-03-01', 'limit=101', 'limit=0', 'limit=1.5'])('rejects invalid filters %s', (params) => {
    expect(Object.keys(validateFilters(new URLSearchParams(params))).length).toBeGreaterThan(0);
  });
});

describe('defect list component', () => {
  it('shows loading then empty without depending on lookup access', async () => {
    let finish!: (response: Response) => void;
    await mount('/defects', async (url) => url.includes('/defects?')
      ? new Promise((resolve) => { finish = resolve; })
      : response({ code: 'denied', title: 'Denied' }, 403), ['defect.read']);
    expect(screen.getByText('Loading defects…')).toBeVisible();
    finish(response({ items: [], next_cursor: null }));
    expect(await screen.findByText('No matching defects')).toBeVisible();
    expect(screen.queryByRole('link', { name: 'Log defect' })).not.toBeInTheDocument();
    expect(await screen.findByText(/Defect type filter choices unavailable/)).toBeVisible();
  });
  it.each([403, 503])('distinguishes list error %s from empty and withholds records', async (status) => {
    await mount('/defects', async (url) => url.includes('/defects?')
      ? response({ code: 'failed', title: 'Service unavailable' }, status) : lookupResponse());
    expect(await screen.findByRole('button', { name: 'Retry defects' })).toBeVisible();
    expect(screen.queryByText('No matching defects')).not.toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    if (status === 403) expect(screen.getByText(/Access denied.*read defects/)).toBeVisible();
  });
  it('uses opaque cursors, historical labels and resets continuation on changed filters', async () => {
    const { user, transport } = await mount('/defects', async (url) => url.includes('/defects?')
      ? response({ items: [defect], next_cursor: url.includes('cursor=') ? null : 'opaque+/=' }) : lookupResponse());
    expect(await screen.findByRole('link', { name: 'P1' })).toBeVisible();
    expect(screen.getAllByText('OLD — Historical')).toHaveLength(3);
    await user.click(screen.getByRole('button', { name: 'Next page' }));
    await waitFor(() => expect(transport.mock.calls.some(([url]) => String(url).includes('cursor=opaque%2B%2F%3D'))).toBe(true));
    await screen.findByRole('button', { name: 'First page' });
    await user.type(screen.getByLabelText('Part number'), 'NEW');
    await user.click(screen.getByRole('button', { name: 'Apply filters' }));
    await waitFor(() => expect(transport.mock.calls.some(([url]) => String(url).includes('part_number=NEW') && !String(url).includes('cursor='))).toBe(true));
  });
  it('blocks invalid filter requests before fetching', async () => {
    const { transport } = await mount('/defects?start_date=2026-01-01', lookupResponse);
    expect(await screen.findByText('Supply both start and end dates')).toBeVisible();
    expect(transport.mock.calls.some(([url]) => String(url).includes('/defects?'))).toBe(false);
  });
});

describe('S1 component', () => {
  it.each(['loading', 'empty', 'denied', 'error'])('shows independent lookup %s and blocks submission', async (state) => {
    await mount('/defects/new', async (url) => {
      if (!url.endsWith('/defect-types')) return lookupResponse();
      if (state === 'loading') return new Promise(() => {});
      return state === 'empty' ? response({ items: [], next_cursor: null })
        : response({ code: 'failed', title: 'Service unavailable' }, state === 'denied' ? 403 : 503);
    });
    expect(screen.getByText('Photo upload is not available in this version')).toBeVisible();
    expect(document.querySelector('input[type=file]')).toBeNull();
    expect(screen.getByRole('button', { name: 'Log defect' })).toBeDisabled();
    if (state === 'loading') expect(screen.getByText('Loading defect type…')).toBeVisible();
    if (state === 'empty') expect(await screen.findByText('No defect type available')).toBeVisible();
    if (state === 'denied') expect(await screen.findByText(/defect type: Access denied/)).toBeVisible();
    if (state === 'error') expect(await screen.findByText('defect type: Service unavailable')).toBeVisible();
  });
  it('focuses validation summary, retains values, excludes retired choices and maps server fields', async () => {
    const { user, transport } = await mount('/defects/new', async (_url, init) => init?.method === 'POST'
      ? response({ code: 'capture_validation_failed', title: 'Capture input is invalid', field_errors: { part_number: 'Server rejected part' } }, 422)
      : lookupResponse());
    await waitFor(() => expect(screen.getByRole('button', { name: 'Log defect' })).toBeEnabled());
    await user.click(screen.getByRole('button', { name: 'Log defect' }));
    expect(screen.getByRole('alert')).toHaveFocus();
    expect(screen.getByLabelText('Part number *')).toHaveAttribute('aria-invalid', 'true');
    expect(transport.mock.calls.filter(([, init]) => init?.method === 'POST')).toHaveLength(1); // Login only.
    expect(screen.queryByRole('option', { name: /Retired/ })).not.toBeInTheDocument();
    await fill(user);
    await user.click(screen.getByRole('button', { name: 'Log defect' }));
    expect(await screen.findByText('Server rejected part')).toBeVisible();
    expect(screen.getByLabelText('Part number *')).toHaveValue(' P1 ');
    expect(screen.queryByText(/Defect logged/)).not.toBeInTheDocument();
  });
  it('sends only capture JSON, disables pending resubmission and retains the confirmed ETag', async () => {
    let finish!: (response: Response) => void;
    const { user, transport, query } = await mount('/defects/new', async (_url, init) => init?.method === 'POST'
      ? new Promise((resolve) => { finish = resolve; }) : lookupResponse());
    await waitFor(() => expect(screen.getByRole('button', { name: 'Log defect' })).toBeEnabled());
    await fill(user);
    await user.click(screen.getByRole('button', { name: 'Log defect' }));
    expect(screen.getByRole('button', { name: 'Logging defect…' })).toBeDisabled();
    const init = transport.mock.calls.find(([url, init]) => String(url).endsWith('/defects') && init?.method === 'POST')![1]!;
    expect(Array.from((init.body as FormData).keys())).toEqual(['capture']);
    expect(JSON.parse((init.body as FormData).get('capture') as string)).toEqual({
      part_number: 'P1', quantity_affected: 3, severity: 'Major', defect_type_id: 'a', production_line_id: 'a', shift_id: 'a',
    });
    expect(new Headers(init.headers).has('Content-Type')).toBe(false);
    finish(response(defect, 201, '"1"'));
    expect(await screen.findByText(/Defect logged/)).toBeVisible();
    expect(screen.getByRole('link', { name: 'Continue to record cause' })).toHaveAttribute('href', '/defects/d1/causes');
    expect(query.getQueryData(['defect', 'u1', 'd1'])).toEqual({ data: defect, etag: '"1"' });
  });
  it('labels interrupted writes unconfirmed, does not retry and preserves input', async () => {
    const { user, transport } = await mount('/defects/new', async (_url, init) => {
      if (init?.method === 'POST') throw new TypeError('Network failure');
      return lookupResponse();
    });
    await waitFor(() => expect(screen.getByRole('button', { name: 'Log defect' })).toBeEnabled());
    await fill(user);
    await user.click(screen.getByRole('button', { name: 'Log defect' }));
    expect(await screen.findByText(/The result is unconfirmed/)).toBeVisible();
    expect(screen.getByLabelText('Part number *')).toHaveValue(' P1 ');
    expect(transport.mock.calls.filter(([url]) => String(url).endsWith('/defects'))).toHaveLength(1);
    expect(screen.queryByText(/Defect logged/)).not.toBeInTheDocument();
  });
});
