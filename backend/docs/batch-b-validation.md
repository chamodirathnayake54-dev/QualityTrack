# Batch B validation

## Scope and status

Batch B is implemented and validated, pending user acceptance. This proposal
adds nine operations to accepted Batch A: cause POST/GET, defect history GET,
defect transitions, action POST/GET, assignable-user GET, action transitions and
action-history GET. The API now has 17 operations on 14 paths.

No new commit or push was made. Batch C has not started. The schema, initial
migration, dependencies, seed grants and design documents are unchanged.

## Executed checks

Validation used Python **3.11.17**, local **PostgreSQL 16**, the existing
owner-private database helper and all declared application/test dependencies.

| Check | Result |
| --- | --- |
| Final full suite, run 1 | 267 passed in 68.81 seconds |
| Final full suite, run 2 | 267 passed in 68.68 seconds |
| Unit subset | 179 tests, including 83 new Batch B cases |
| PostgreSQL integration subset | 88 tests, including 34 new Batch B cases |
| Black check | 22 Python files unchanged |
| Ruff check | All checks passed |
| Dependency compatibility | All 40 installed packages compatible |
| Git whitespace check | Passed |

Commands from `backend/`, using the Python 3.11 environment:

```sh
python scripts/demo_db.py test
python scripts/demo_db.py test
black --check qualitytrack migrations scripts tests
ruff check .
git diff --check
```

Dependency compatibility was verified with `uv pip check --python` targeting
that environment. Both final full runs completed without failed or skipped
tests. The sole warning is the existing third-party Starlette TestClient
reference to AnyIO's deprecated `BlockingPortal` alias.

The first focused PostgreSQL attempt encountered a stopped private database
cluster. Restarting the existing cluster resolved the environment issue without
recreating the database, changing credentials or reading `.env`. Focused tests
then passed before the final full runs.

## Evidence covered

- Causes are trimmed nonblank text of at most 2,000 characters, attributed to
  the verified caller, saved under the parent lock and revisioned atomically.
- Cause/action creation ignores `If-Match`; status transitions evaluate one
  strong quoted positive parent revision under lock.
- Missing, malformed, weak, wildcard, multiple and stale revision tokens
  produce the specified 428/400/412 responses. Current-token state/gate
  failures return 409. Duplicate header lines are rejected.
- Investigation requires a persisted nonblank cause. Legal transitions retain
  successful actor/time/revision evidence. Same-state and unsupported edges
  do not mutate the aggregate.
- Closure rejects incomplete associated work; zero-action closure is explicitly
  permitted. Supervisor-authorized reopening preserves the same cause gate.
- Action creation supports explicit Open, In Progress and Complete entry.
  Eligibility, progress/completion grants, ownership or explicitly bound
  supervisor authority and conditional completion evidence are enforced.
- All action additions on Closed return 409 `defect_closed` before owner or
  completion business gates, with no action/event/revision mutation.
- Existing-action reopening on Closed returns 503 without mutation. Completion
  notes and reopening reasons are preserved across cycles in append-only
  ActionEvents, ordered by parent aggregate revision rather than clock time.
- Assignable users require assignment authority and existing parent context.
  Only active explicitly eligible demo engineer/supervisor references appear;
  active status, display names and persona labels never grant eligibility.
- Ownership without an explicit progress/completion grant is denied. A reopen
  grant without agreed supervisor authority cannot reveal precondition results.
- Child/history reads require current parent read authority on every page.
  Ordered keyset continuations bind caller, plant, collection and resource.
  Empty reads, bounded limits, safe projections, tampering, changed collection,
  changed caller and revocation are covered.
- Post-flush fault injection verifies rollback of causes, defect transitions,
  action creation and action transitions, including state/revision/evidence.
- Real PostgreSQL lock waits verify closure-first action addition rejection,
  action-first stale closure, cause-first stale closure and grant revocation
  while an assignment waits for the parent lock.
- Both lock orderings of closure racing existing-action reopening are tested:
  closure-first rejects reopening with 503; reopening-first invalidates the
  reviewed closure token and leaves the parent Under Investigation.
- Concurrent cause additions preserve all saved rows and unique successive
  parent revisions without lost increments.
- Original Batch A regression coverage remains passing, including immutable
  history table privileges, migration drift, seed integrity, authentication,
  capture, lookup locking and defect collection cursors.

Every PostgreSQL case creates, migrates and seeds its own uniquely named
database, then drops it in teardown, including committed test rows. Tests use
their own record identifiers and do not depend on global first-page positions,
the process timezone or persistent test data.

## Boundaries and limits

Demo supervisor authority and owner eligibility are explicitly bound to LLD
16.3 stable references only in demo mode. Unsupported authority/eligibility
policy fails closed; this is not a production entitlement implementation.

Photo upload/serving, analytics stubs and auditor acceptance stories remain
outside scope. Overdue queries, PDF export, type retirement, the complete
OpenAPI header/response declaration pass and contract drift report remain
Batch C work. No routes for those features were added.

This is functional/security-contract and concurrency evidence for the local
demo, not production security certification, performance/SLO measurement,
deployment approval or a privileged-SQL tamper-proof audit guarantee.

Return to the [backend guide](../README.md) for route scope and operator setup.
