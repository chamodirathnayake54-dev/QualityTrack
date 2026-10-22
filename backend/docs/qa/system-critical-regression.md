# QA-07 Critical-Path Regression Set

## Scope

Use this set for the bounded photo-free engineer release. It is not full-product
acceptance and does not close [open scope defects](system-defect-log.md).
The [Batch 2 report](system-validation-batch2.md) holds actual results.

| Set | Cases / risk | Required assertions |
| --- | --- | --- |
| CP-01 setup | 01 | Missing API base fails clearly; public example supplies `/api/v1`; valid setup reaches real login/identity/lookups. |
| CP-02 engineer journey, twice | 02 + consolidated 03 + 07 + 09 + valid 11 + 12 | Real multipart capture; correct stable lookup IDs/snapshots; one saved cause; explicit reviewed transition; attributable history; two appended actions; reauthentication recovery; independent API/database reconciliation. |
| CP-03 rejection and races | 04–06, 08, 10, invalid 11 | Required fields and quantity boundaries reject without writes; denied capture/transition; selected type retirement race; no-cause gate; exact stale ETag and renewed review without replay. |
| CP-04 session isolation | 13 | Hold a real read response across logout and denied-reader login; no stale identity/data restoration; real read/write denial. |
| CP-05 uncertain write | 20 | Commit actual action then lose only its response; unconfirmed warning; one POST; refreshed action visible; independent API/database count one; no blind replay. |
| CP-06 bounded capability checks | 14; supporting 15–19 APIs | Preserve safe photo rejection as a known requirement failure. Check overdue calendar exclusions, valid lifecycle/retained cycles, PDF signature and grant denials without counting absent browser journeys as passes. |

Case 03's separate execution adds no value once CP-02 compares all three
lookup IDs and snapshots. It is removed from the independent set but retains
its original traceability ID and coverage in both critical journeys.

## Reproduce the real-stack run

Prerequisites: repository-pinned frontend and backend dependencies installed;
Python 3.11, Node 22, PostgreSQL 16 tools at the existing documented
`/usr/lib/postgresql/16/bin`, and the Chromium binary matching pinned Playwright.
Use a non-root account so `initdb` can run. Loopback ports 8000, 4173, and 4174
must be free; do not attach this isolated runner to production services.
The runner does not invoke the destructive existing demo-cluster helper.

From `backend/`, with the supported Python environment active and Node 22 on
PATH:

```sh
QA07_DISPOSABLE=true python scripts/qa07_real_stack.py
python -m pytest -q tests/test_frontend_configuration.py
ruff check scripts/qa07_real_stack.py tests/test_frontend_configuration.py
black --check scripts/qa07_real_stack.py tests/test_frontend_configuration.py
```

If a custom browser cache is used, supply the same `PLAYWRIGHT_BROWSERS_PATH`
used at installation. The observed validation used a temporary matching-browser
cache. Do not save passwords or bearer tokens to reproduce the run: the runner
generates per-user passwords and signing material in memory.

The runner migrates/seeds a new private temporary PostgreSQL cluster, creates
explicit denial fixtures, launches real FastAPI and frontend processes, invokes
`playwright.real.config.ts`, saves sanitized evidence, and stops/removes its
resources in `finally`. A test-only supervisor retirement grant never modifies
the shipped seed policy. The isolated database administrator connection means
deployment-role privilege enforcement requires separate qualification.

The runner overwrites `batch2-evidence/` for each complete run. Archive a reviewed
evidence set before rerunning it if retention is required. Do not run two
instances concurrently.

From `frontend/`:

```sh
CI=true npm test
npm run build
```

Existing `npm run test:e2e` remains the mocked desktop/mobile suite; it explicitly
excludes `real-stack.spec.ts`. Do not use its result as real-backend evidence.
The opt-in real suite disables traces/videos/screenshots to avoid retaining
login bodies or credentials. It stores IDs, statuses, ETags and synthetic domain
data, not raw authentication traffic.

## Review gate

Require all executable bounded checks to pass and both critical runs to remain
stable. Review known photo/missing-screen exclusions explicitly; API-only
diagnostics do not replace the five unavailable persona browser journeys.
A lost-response pass establishes one observed attempt, not idempotent writes.
Do not commit/push this proposal until the requester approves.
