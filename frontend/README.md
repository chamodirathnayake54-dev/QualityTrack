# QualityTrack frontend — Batch 1

React/TypeScript foundation with Vite, Tailwind, React Router and TanStack Query.
Direct dependencies are exact-pinned in `package.json`.

## Configure and run

Use Node.js 22 LTS and npm. Run these commands from `QualityTrack/frontend`:

```sh
npm ci
npm run dev
```

Ask the environment owner to supply these settings (see `.env.example`, names only):

- `VITE_API_BASE_URL`: required public same-origin path ending in `/api/v1`.
  For the supplied development proxy use `/api/v1`.
- `API_PROXY_TARGET`: optional development-only backend origin, for example
  `http://127.0.0.1:8000` (also the proxy default). Never include credentials.

Missing/invalid API-base configuration produces a visible setup message. Vite
proxies `/api` to the running backend with no path rewrite and no backend/CORS
change. Start the backend separately using its existing instructions. No backend
or database service is started by frontend tests.

```sh
npm test
npm run build
```

Tests are non-interactive and cover shared UI, API transport, and login/shell
integration with mocked HTTP responses. Production output is `dist/`. Production
hosting must route `/api` to the backend and fall back to `index.html` for SPA
deep links; do not send API errors through the SPA fallback. A direct cross-origin
deployment is not configured by this batch.

## Implemented boundaries

- `src/ui/`: accessible, presentation-only shared controls and feedback.
- `src/api/`: bearer transport, exact ETag return metadata, explicit opt-in
  If-Match, abort support, Problem/field-error handling and uncertain write errors.
  No automatic write retries or automatic stale-request replay.
- `src/features/auth/`: JSON login followed by `/me` before entering the shell.
  Backend identity/grants are authoritative; tokens are not decoded for grants.
- `src/app/`: guarded shell, caller/timezone, sign-out, route focus, and named
  placeholders for future defect list and S1–S4 pages. Placeholders do not fetch
  records, capture photos, or perform mutations.

The bearer token, identity, and query cache live in memory only. Reload requires
sign-in. Sign-out, token expiry, and authenticated 401 clear the session and
protected query data and cancel old requests. Late previous-session responses
are ignored. Sign-out does not revoke an issued backend token. There is no
refresh-token, persistent storage, offline service worker, or invented logout API.

Use response ETags exactly as returned. Pass `etag` explicitly only for requests
whose backend contract requires If-Match; capture/cause/action creation has no
invented precondition. Future transition controllers must bind revisions to
reviewed context and require renewed review on 412, not replay automatically.
FormData is supported without setting a multipart boundary manually.

Batch 0's approved photo-free deviation remains binding for later S1:
“Photo upload is not available in this version”, with no file control. Batch 1
does not implement S1, defect listing, S2–S4, pagination, permission-aware journey
controls, or their acceptance checks. Accessibility conformance, UX alignment
percentages, cross-page reuse targets and live backend/browser integration are
not claimed by these foundation tests.
