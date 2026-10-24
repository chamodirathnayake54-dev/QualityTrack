import { describe, expect, it, vi } from 'vitest';
import { ApiClient, ApiError, friendlyProblem } from './client';

const json = (data: unknown, init: ResponseInit = {}) =>
  new Response(JSON.stringify(data), { ...init, headers: { 'Content-Type': 'application/json', ...init.headers } });

describe('API client', () => {
  it.each([
    [401, 'invalid_credentials', 'Username or password is incorrect.'],
    [403, 'forbidden', "You don't have permission to do this. Your role does not allow this action."],
    [409, 'actions_incomplete', "This can't be done yet: all corrective actions must be completed first."],
    [409, 'cause_required', "This can't be done right now because of the defect's current status."],
    [412, 'precondition_failed', 'Someone else updated this defect. We loaded the latest details. Please check them and try again.'],
    [428, 'precondition_required', 'Please tick the box to confirm you have checked the latest details, then try again.'],
    [400, 'invalid_cursor', 'Something went wrong with this request. We reloaded the page, please try again.'],
    [499, 'unknown', 'The request could not complete. Please try again later.'],
    [500, 'internal_error', 'The request could not complete. Please try again later.'],
    [502, 'proxy_error', 'The request could not complete. Please try again later.'],
  ])('translates %s %s without changing backend text', (status, code, expected) => {
    const problem = { status: Number(status), code: String(code), title: 'Original fallback' };
    expect(friendlyProblem(problem)).toBe(expected);
    expect(problem.title).toBe('Original fallback');
  });

  it('rejects missing or cross-origin configuration visibly', () => {
    expect(() => new ApiClient('')).toThrow('VITE_API_BASE_URL');
    expect(() => new ApiClient('https://other.test/api/v1')).toThrow('same-origin');
  });

  it('attaches bearer auth, disables caching, and retains the exact ETag', async () => {
    const transport = vi.fn<typeof fetch>().mockResolvedValue(json({ id: 'a' }, { headers: { ETag: '"7"' } }));
    const client = new ApiClient('/api/v1', transport);
    client.setSession('secret');
    expect(await client.request('/defects/a')).toEqual({ data: { id: 'a' }, etag: '"7"' });
    const [url, init] = transport.mock.calls[0];
    expect(url).toBe('/api/v1/defects/a');
    expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer secret');
    expect(init?.cache).toBe('no-store');
    expect(init?.credentials).toBe('omit');
  });

  it('sends only explicitly supplied If-Match and never invents one for additive writes', async () => {
    const transport = vi.fn<typeof fetch>().mockImplementation(async () => json({}));
    const client = new ApiClient('/api/v1', transport);
    await client.request('/defects/a/transitions', { method: 'POST', body: { target_status: 'Under Investigation' }, etag: '"7"' });
    await client.request('/defects/a/causes', { method: 'POST', body: { text: 'Cause' } });
    expect(new Headers(transport.mock.calls[0][1]?.headers).get('If-Match')).toBe('"7"');
    expect(new Headers(transport.mock.calls[1][1]?.headers).has('If-Match')).toBe(false);
  });

  it('omits auth for login and leaves multipart content type to the browser', async () => {
    const transport = vi.fn<typeof fetch>().mockImplementation(async () => json({}));
    const client = new ApiClient('/api/v1', transport);
    client.setSession('secret');
    await client.request('/auth/login', { method: 'POST', anonymous: true, body: { username: 'user', password: ' p ' } });
    expect(new Headers(transport.mock.calls[0][1]?.headers).has('Authorization')).toBe(false);
    expect(transport.mock.calls[0][1]?.body).toBe('{"username":"user","password":" p "}');
    const form = new FormData();
    form.append('capture', JSON.stringify({ part_number: 'P-1' }));
    await client.request('/defects', { method: 'POST', body: form });
    expect(new Headers(transport.mock.calls[1][1]?.headers).has('Content-Type')).toBe(false);
    expect(transport.mock.calls[1][1]?.body).toBe(form);
  });

  it.each([400, 403, 404, 409, 412, 422, 428, 500, 503])('retains Problem status %i without retry', async (status) => {
    const problem = { status, code: `code_${status}`, title: 'Safe explanation', field_errors: { text: 'Required' } };
    const transport = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify(problem), {
      status, headers: { 'Content-Type': 'application/problem+json' },
    }));
    const client = new ApiClient('/api/v1', transport);
    await expect(client.request('/resource', { method: 'POST', body: {} })).rejects.toMatchObject({ problem });
    expect(transport).toHaveBeenCalledTimes(1);
  });

  it('never renders raw non-Problem response bodies', async () => {
    const client = new ApiClient('/api/v1', vi.fn<typeof fetch>().mockResolvedValue(new Response('<script>secret</script>', { status: 500 })));
    await expect(client.request('/resource')).rejects.toMatchObject({ message: 'The request could not complete. Please try again later.' });
  });

  it('keeps unknown server metadata for diagnostics without displaying it', async () => {
    const problem = { status: 500, code: 'unknown', title: 'Internal database exception' };
    const client = new ApiClient('/api/v1', vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify(problem), {
      status: 500, headers: { 'Content-Type': 'application/problem+json' },
    })));
    await expect(client.request('/resource')).rejects.toMatchObject({
      problem, message: 'The request could not complete. Please try again later.',
    });
  });

  it('clears the session on authenticated 401, but not anonymous login rejection', async () => {
    const transport = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 401 }));
    const unauthorized = vi.fn();
    const client = new ApiClient('/api/v1', transport);
    client.setSession('secret', unauthorized);
    await expect(client.request('/auth/login', { method: 'POST', anonymous: true })).rejects.toBeInstanceOf(ApiError);
    expect(unauthorized).not.toHaveBeenCalled();
    await expect(client.request('/me')).rejects.toBeInstanceOf(ApiError);
    expect(unauthorized).toHaveBeenCalledOnce();
  });

  it('marks lost write responses unconfirmed and never automatically retries', async () => {
    const transport = vi.fn<typeof fetch>().mockRejectedValue(new TypeError('offline'));
    const client = new ApiClient('/api/v1', transport);
    await expect(client.request('/resource', { method: 'POST', body: {} })).rejects.toMatchObject({
      uncertain: true, problem: { code: 'network_failure' },
    });
    expect(transport).toHaveBeenCalledOnce();
    await expect(client.request('/resource')).rejects.toMatchObject({ uncertain: false });
  });

  it('aborts obsolete requests and ignores late responses after session change', async () => {
    let resolve!: (response: Response) => void;
    const transport = vi.fn<typeof fetch>().mockImplementation(() => new Promise((done) => { resolve = done; }));
    const client = new ApiClient('/api/v1', transport);
    client.setSession('old');
    const pending = client.request('/me');
    client.setSession(null);
    expect(transport.mock.calls[0][1]?.signal?.aborted).toBe(true);
    resolve(json({ ref: 'old' }));
    await expect(pending).rejects.toMatchObject({ name: 'AbortError' });
  });

  it('propagates caller cancellation', async () => {
    const transport = vi.fn<typeof fetch>().mockImplementation(async (_url, init) => {
      expect(init?.signal?.aborted).toBe(true);
      throw new DOMException('Cancelled', 'AbortError');
    });
    const controller = new AbortController();
    controller.abort();
    const client = new ApiClient('/api/v1', transport);
    await expect(client.request('/me', { signal: controller.signal })).rejects.toMatchObject({ name: 'AbortError' });
  });
});
