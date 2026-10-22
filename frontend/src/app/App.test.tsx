import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { ApiClient } from '../api/client';
import { AuthProvider } from '../features/auth/AuthProvider';
import { App } from './App';

const response = (data: unknown, status = 200) => new Response(JSON.stringify(data), {
  status, headers: { 'Content-Type': status >= 400 ? 'application/problem+json' : 'application/json' },
});
const identity = { ref: 'u1', display_name: 'Engineer', scope: 'plant', permissions: ['defect.read'], plant_zone: 'Europe/London' };

function mount(transport: typeof fetch, path = '/defects') {
  const query = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={query}><MemoryRouter initialEntries={[path]}
    future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <AuthProvider client={new ApiClient('/api/v1', transport)}><App /></AuthProvider>
  </MemoryRouter></QueryClientProvider>);
  return query;
}

describe('login and shell', () => {
  it('redirects protected direct links and validates fields before requesting', async () => {
    const transport = vi.fn<typeof fetch>();
    mount(transport, '/defects/record/causes');
    expect(screen.getByRole('heading', { name: 'Sign in to QualityTrack' })).toBeVisible();
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(screen.getByRole('alert')).toHaveFocus();
    expect(screen.getByLabelText('Username')).toHaveAttribute('aria-invalid', 'true');
    expect(transport).not.toHaveBeenCalled();
  });

  it('loads identity before entering shell and clears protected cache on sign-out', async () => {
    let finishMe!: (value: Response) => void;
    const transport = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(response({ access_token: 'token', token_type: 'bearer', expires_in: 3600 }))
      .mockImplementationOnce(() => new Promise((resolve) => { finishMe = resolve; }))
      .mockImplementation(async () => response({ items: [], next_cursor: null }));
    const query = mount(transport);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('Username'), 'engineer');
    await user.type(screen.getByLabelText('Password'), ' p ');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));
    await waitFor(() => expect(transport).toHaveBeenCalledTimes(2));
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Signing in…' })).toBeDisabled();
    finishMe(response(identity));
    expect(await screen.findByRole('navigation', { name: 'Main navigation' })).toBeVisible();
    expect(screen.getByText(/Engineer · Plant timezone: Europe\/London/)).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Defects' })).toHaveFocus();
    expect(await screen.findByText('No matching defects')).toBeVisible();
    query.setQueryData(['protected'], { private: true });
    await user.click(screen.getByRole('button', { name: 'Sign out' }));
    expect(await screen.findByRole('heading', { name: 'Sign in to QualityTrack' })).toBeVisible();
    expect(query.getQueryData(['protected'])).toBeUndefined();
    expect(screen.getByLabelText('Password')).toHaveValue('');
    expect(transport).toHaveBeenCalledTimes(6);
  });

  it('does not enter shell when identity is denied after token issuance', async () => {
    const transport = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(response({ access_token: 'token', token_type: 'bearer', expires_in: 3600 }))
      .mockResolvedValueOnce(response({ status: 403, code: 'permission_denied', title: 'Access denied' }, 403));
    mount(transport);
    await userEvent.type(screen.getByLabelText('Username'), 'engineer');
    await userEvent.type(screen.getByLabelText('Password'), 'password');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByText('Access denied')).toBeVisible();
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toHaveValue('');
  });
});
