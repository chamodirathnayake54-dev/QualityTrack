# QualityTrack frontend

React/TypeScript, Vite, Tailwind, React Router and TanStack Query frontend for
the bounded Quality Engineer S1–S4 journey. Dependencies are exact-pinned.

## Run against the backend

Use **Node.js 22 LTS** and npm. From `QualityTrack/frontend`:

```sh
npm ci
npm run dev
```

Request these public settings from the environment owner (see `.env.example`):

- `VITE_API_BASE_URL=/api/v1`: required same-origin API base.
- `API_PROXY_TARGET`: optional development-only backend origin; defaults to
  `http://127.0.0.1:8000`. Do not include credentials.

The owner must supply configuration before Vite starts; restart Vite after
configuration changes. Frontend variables are public, never secrets.

Start the backend separately following [backend setup](../backend/README.md),
including its Python 3.11/PostgreSQL 16 prerequisites and securely injected
configuration. For an already provisioned disposable demo, its documented API
command from `backend/` is `python scripts/demo_db.py api`. Database recreation
is destructive and is not needed to start this frontend.

Open the URL printed by Vite. The browser sends `/api/v1/...` to Vite; the dev
proxy forwards `/api` to `API_PROXY_TARGET` **without rewriting the path**.
Bearer authorization, multipart bodies, If-Match and ETag travel through that
same-origin proxy. No backend CORS changes are needed. Use an existing permitted
backend account; never put credentials in frontend environment variables.

If setup is missing, the app displays “Configuration required”. If requests
fail, confirm the backend is running at the proxy target and inspect its safe
health/configuration diagnostics. A 403 means authority is absent, not an empty
record set. Do not grant permissions merely to suppress a frontend message.

Production `dist/` needs same-origin `/api` routing to the backend plus SPA
fallback to `index.html` for application deep links. API errors must not use the
SPA fallback. The Vite development proxy is not a production proxy.

## Verification

```sh
npm test
npm run build
npm run test:e2e:install
CI=true npm run test:e2e
npm audit
```

The unit/component suite uses mocked HTTP. Playwright manages its Vite server
on loopback port 4173 and supplies a test-only API base. Its one critical-path
scenario runs in desktop and mobile Chromium projects against a stateful,
fully mocked API. No backend/database is started by the tests. Browser binaries
must match the pinned Playwright version. If using a custom browser cache,
use the same `PLAYWRIGHT_BROWSERS_PATH` for installation and execution.

E2E verifies login, photo-free multipart capture, cause recording, reviewed
investigation with exact If-Match, history, and a confirmed Open action.
Generated traces/results are ignored by Git. A passing mocked journey does not
prove real-backend integration, all browsers, assistive-technology conformance,
or production readiness. Audit findings remain open; see the reports below.

## Implemented boundaries

- `src/ui/`: shared presentation controls and accessible feedback.
- `src/api/`: DTOs, bearer transport, exact response ETags, Problem handling,
  cancellation and uncertain-write outcomes; no automatic POST retries.
- `src/features/auth/`: login followed by `/me`, memory-only session.
- `src/features/defects/`: live filtered/paginated list, photo-free S1 capture,
  S2 causes, S3 reviewed investigation/history, S4 action capture/association.
  Hooks own validation and orchestration; the server owns authorization,
  eligible owners, lifecycle gates and committed state.
- `src/app/`: guarded routing, shell, sign-out and route-heading focus.

Reload requires sign-in. Sign-out clears local protected state but does not
revoke an issued backend token. No persistent tokens, offline queue, refresh
token, autosave, photo upload, closure/reopening, action progression, analytics,
or export UI is introduced.

Capture, cause and action creation do not invent If-Match preconditions.
Investigation uses the reviewed parent revision; stale state requires renewed
review and explicit resubmission, never automatic replay. A lost write response
may mean the mutation committed: reconcile before deliberately retrying.

## Batch 4 review reports

See [report index](docs/index.md) for UX alignment, measured component reuse,
the five-component no-business-logic review, persona review, verification,
accessibility limitations and dependency-audit findings.
