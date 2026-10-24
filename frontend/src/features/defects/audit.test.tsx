import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiClient } from '../../api/client';
import { App } from '../../app/App';
import { AuthProvider } from '../auth/AuthProvider';
import { auditFileName } from './useAuditExport';

const lookup = { id: 'l', code_at_capture: 'L', label_at_capture: 'Line one' };
const response = (data: unknown, status = 200) => new Response(JSON.stringify(data), {
  status, headers: { 'Content-Type': status >= 400 ? 'application/problem+json' : 'application/json', ETag: '"3"' },
});

async function mount({ permissions, route = '', pdfStatus = 200, pdfDelay }: {
  permissions: string[]; route?: string; pdfStatus?: number; pdfDelay?: Promise<void>;
}) {
  const transport = vi.fn<typeof fetch>(async (url) => {
    const path = String(url);
    if (path.endsWith('/auth/login')) return response({ access_token: 't', expires_in: 3600 });
    if (path.endsWith('/me')) return response({ ref: 'u', display_name: 'Reader', plant_zone: 'UTC', permissions });
    if (path.endsWith('/audit.pdf')) {
      await pdfDelay;
      return pdfStatus === 200
        ? new Response('%PDF-1.4', { status: 200, headers: { 'Content-Type': 'application/pdf' } })
        : response({ code: pdfStatus === 403 ? 'forbidden' : 'internal_error', title: 'Refused' }, pdfStatus);
    }
    if (path.endsWith('/defects/d')) return response({
      id: 'd', part_number: 'P 1/A', quantity_affected: 2, severity: 'Major', status: 'Closed',
      defect_type: lookup, production_line: lookup, shift: lookup, created_by_ref: 'logger',
      created_at: '2026-01-01T12:00:00Z', revision: 3, has_photo: false,
    });
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
  await screen.findByText(/Part: P 1\/A/);
  return { user, transport };
}

describe('audit PDF export', () => {
  const click = vi.fn();
  beforeEach(() => {
    URL.createObjectURL = vi.fn(() => 'blob:report');
    URL.revokeObjectURL = vi.fn();
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(click);
  });
  afterEach(() => { click.mockClear(); vi.restoreAllMocks(); });

  it('builds a safe file name from the part number and date', () => {
    expect(auditFileName('P 1/A', new Date('2026-10-24T09:00:00Z'))).toBe('QualityTrack-defect-P-1-A-2026-10-24.pdf');
    expect(auditFileName('///', new Date('2026-10-24T09:00:00Z'))).toBe('QualityTrack-defect-defect-2026-10-24.pdf');
  });

  it.each(['/causes', '/investigation', '/actions', ''])('shows the button with defect.export on %s', async (route) => {
    await mount({ permissions: ['defect.read', 'defect.export', 'cause.create', 'defect.investigate', 'action.assign'], route });
    expect(await screen.findByRole('button', { name: 'Export audit PDF' })).toBeVisible();
    expect(screen.getByText('The report does not include photos.')).toBeVisible();
  });

  it('hides the button without defect.export', async () => {
    await mount({ permissions: ['defect.read'] });
    expect(screen.queryByRole('button', { name: 'Export audit PDF' })).not.toBeInTheDocument();
    expect(screen.queryByText('The report does not include photos.')).not.toBeInTheDocument();
  });

  it('is the main action for a read-only user and secondary for a writer', async () => {
    await mount({ permissions: ['defect.read', 'defect.export'] });
    expect(await screen.findByRole('button', { name: 'Export audit PDF' })).toHaveClass('ui-button-primary');
  });

  it('is not the main action for a user who can change the record', async () => {
    await mount({ permissions: ['defect.read', 'defect.export', 'defect.reopen'] });
    expect(await screen.findByRole('button', { name: 'Export audit PDF' })).not.toHaveClass('ui-button-primary');
  });

  it('downloads the PDF once, shows progress and the file name', async () => {
    let release = () => {};
    const pdfDelay = new Promise<void>((resolve) => { release = resolve; });
    const { user, transport } = await mount({ permissions: ['defect.read', 'defect.export'], pdfDelay });
    const button = await screen.findByRole('button', { name: 'Export audit PDF' });
    await user.click(button);
    const busy = await screen.findByRole('button', { name: 'Preparing PDF…' });
    expect(busy).toBeDisabled();
    await user.click(busy);
    release();
    expect(await screen.findByText('The audit PDF was downloaded.')).toBeVisible();
    const calls = transport.mock.calls.filter(([url]) => String(url).endsWith('/defects/d/audit.pdf'));
    expect(calls).toHaveLength(1);
    expect(new Headers(calls[0][1]?.headers).get('Accept')).toBe('application/pdf');
    expect(new Headers(calls[0][1]?.headers).get('Authorization')).toBe('Bearer t');
    expect(click).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(screen.getByRole('button', { name: 'Export audit PDF' })).toBeEnabled());
  });

  it.each([
    [500, "We couldn't create the PDF. Please try again."],
    [403, "You don't have permission to export this report."],
  ])('shows a friendly message when the server answers %s and keeps the page usable', async (pdfStatus, text) => {
    const { user } = await mount({ permissions: ['defect.read', 'defect.export'], pdfStatus });
    await user.click(await screen.findByRole('button', { name: 'Export audit PDF' }));
    expect(await screen.findByText(text)).toBeVisible();
    expect(click).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Export audit PDF' })).toBeEnabled();
    expect(screen.getByText(/Part: P 1\/A/)).toBeVisible();
  });
});
