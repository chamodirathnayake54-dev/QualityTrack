import type { ApiResult, Problem } from './contracts';

type RequestOptions = {
  method?: 'GET' | 'POST';
  body?: unknown;
  signal?: AbortSignal;
  anonymous?: boolean;
  token?: string;
  etag?: string;
};

/** Transport failure with safe display text and a distinct uncertain-write outcome. */
// PUBLIC_INTERFACE
export class ApiError extends Error {
  // PUBLIC_INTERFACE
  constructor(
    public readonly problem: Problem,
    public readonly uncertain = false,
  ) {
    /** Initialize safe Problem metadata and the write-outcome uncertainty flag. */
    super(problem.title);
    this.name = 'ApiError';
  }
}

const fallbackTitles: Record<number, string> = {
  401: 'Your session has ended. Sign in again.',
  403: 'You do not have permission for this request.',
  404: 'The requested record was not found.',
  409: 'The request conflicts with the current record.',
  412: 'The record changed. Refresh and review before submitting again.',
  428: 'A reviewed record revision is required.',
  422: 'Check the submitted fields.',
  503: 'The service is unavailable. Try again later.',
};

/** Shared fetch adapter. Never retries writes or silently replaces a reviewed ETag. */
// PUBLIC_INTERFACE
export class ApiClient {
  private token: string | null = null;
  private generation = 0;
  private pending = new Set<AbortController>();
  private unauthorized?: () => void;
  private readonly base: string;

  // PUBLIC_INTERFACE
  constructor(baseUrl: string, private readonly transport: typeof fetch = fetch) {
    /** Require explicit same-origin configuration to avoid accidental credential forwarding. */
    if (!baseUrl || !/^\/(?!\/)/.test(baseUrl) || !baseUrl.endsWith('/api/v1')) {
      throw new Error('Set VITE_API_BASE_URL to a same-origin path ending in /api/v1.');
    }
    this.base = baseUrl;
  }

  // PUBLIC_INTERFACE
  setSession(token: string | null, onUnauthorized?: () => void) {
    /** Abort all previous-session requests and invalidate their late responses. */
    this.generation += 1;
    this.pending.forEach((controller) => controller.abort());
    this.pending.clear();
    this.token = token;
    this.unauthorized = onUnauthorized;
  }

  // PUBLIC_INTERFACE
  async request<T>(path: string, options: RequestOptions = {}): Promise<ApiResult<T>> {
    /** Send one request; preserve exact ETag and structured Problem metadata. */
    if (!path.startsWith('/') || path.startsWith('//') || path.includes('://')) {
      throw new Error('API paths must be relative to the configured API base.');
    }
    const method = options.method ?? 'GET';
    const controller = new AbortController();
    const generation = this.generation;
    const abort = () => controller.abort();
    options.signal?.addEventListener('abort', abort, { once: true });
    if (options.signal?.aborted) controller.abort();
    this.pending.add(controller);
    const headers = new Headers({ Accept: 'application/json' });
    const token = options.anonymous ? null : options.token ?? this.token;
    if (token) headers.set('Authorization', `Bearer ${token}`);
    if (options.etag !== undefined) headers.set('If-Match', options.etag);
    const isForm = options.body instanceof FormData;
    if (options.body !== undefined && !isForm) headers.set('Content-Type', 'application/json');

    try {
      const response = await this.transport(`${this.base}${path}`, {
        method, headers, signal: controller.signal, cache: 'no-store',
        credentials: 'omit',
        body: options.body === undefined ? undefined
          : isForm ? options.body as FormData : JSON.stringify(options.body),
      });
      if (generation !== this.generation || controller.signal.aborted) {
        throw new DOMException('Obsolete request', 'AbortError');
      }
      if (!response.ok) {
        let problem: Problem = {
          status: response.status,
          code: 'request_failed',
          title: fallbackTitles[response.status] ?? 'The request could not complete.',
        };
        // Only trust the documented Problem media type; never display an HTML/proxy error.
        if (response.headers.get('Content-Type')?.includes('application/problem+json')) {
          const body: unknown = await response.json().catch(() => null);
          if (body && typeof body === 'object' && 'code' in body && 'title' in body &&
              typeof body.code === 'string' && typeof body.title === 'string') {
            const fields = 'field_errors' in body ? body.field_errors : undefined;
            problem = { ...problem, code: body.code, title: body.title,
              field_errors: fields && typeof fields === 'object'
                ? Object.fromEntries(Object.entries(fields).filter(([, value]) => typeof value === 'string'))
                : undefined };
          }
        }
        if (response.status === 401 && token && generation === this.generation) this.unauthorized?.();
        throw new ApiError(problem);
      }
      const data = response.status === 204 ? undefined : await response.json();
      if (generation !== this.generation || controller.signal.aborted) {
        throw new DOMException('Obsolete request', 'AbortError');
      }
      return { data: data as T, etag: response.headers.get('ETag') };
    } catch (error) {
      if (generation !== this.generation || controller.signal.aborted) {
        throw new DOMException('Obsolete request', 'AbortError');
      }
      if (error instanceof ApiError ||
          (error && typeof error === 'object' && 'name' in error && error.name === 'AbortError')) throw error;
      throw new ApiError({
        status: 0, code: 'network_failure',
        title: method === 'POST'
          ? 'The result is unconfirmed. Check the record before trying again.'
          : 'Could not reach the service. Try again.',
      }, method === 'POST');
    } finally {
      this.pending.delete(controller);
      options.signal?.removeEventListener('abort', abort);
    }
  }
}
