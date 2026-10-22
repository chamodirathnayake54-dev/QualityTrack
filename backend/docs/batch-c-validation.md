# Batch C validation

## Scope and acceptance state

Batch C implements plant-calendar overdue results, photo-free complete PDF
export, type retirement, and full OpenAPI declarations. The baseline is LLD
v0.3 narrowed by the authoritative settled demo decisions.
The implementation remains in the worktree on `kavia/cmfa6fe2fc`, based on
Batch B HEAD `f8e8f4fcc66c3da9c7d16aae7c7d700385557185`.
No Batch C commit or push was made; acceptance is pending.

See the [contract drift report](batch-c-contract-drift.md) for route/schema
reconciliation, intentional exclusions and residual risks, and the
[backend guide](../README.md) for setup and API usage.

## Final full-suite results

Both sequential final runs used Python **3.11.17** and the unchanged final
implementation with PostgreSQL 16 through the private host-local helper:

```sh
python scripts/demo_db.py test
```

| Final run | Passed | Failed / skipped | Warnings | Duration |
| --- | ---: | --- | ---: | --- |
| 1 | 319 | 0 / 0 | 1 | 87.62 s |
| 2 | 319 | 0 / 0 | 1 | 87.82 s |

The suite comprises **210 unit/service cases and 109 PostgreSQL integration
cases**. Batch C adds 52 cases (31 unit and 21 PostgreSQL); the previous
267 cases remain included. Integration fixtures create, migrate, seed and
drop uniquely named per-test databases. No disposable-cluster recreation or
credential reset was needed.

The sole warning in each run is Starlette TestClient's deprecated
`anyio.abc.BlockingPortal` alias. It is not an application failure; no dependency
upgrade was introduced to silence it.

An earlier exploratory full run had 318 passes and one obsolete Batch B
OpenAPI boundary assertion failure (14 paths/17 operations). That assertion
was updated to require Batch C's 17 paths/20 operations while retaining the
photo/analytics exclusion. Both final successful runs above occurred after
that correction.

## Verification coverage

| Feature | Focused evidence |
| --- | --- |
| Overdue | Due today/Complete exclusions, calendar subtraction, DST short and repeated hours, invalid zone/naive clock, midnight-pinned continuations, cursor tampering/caller/calendar/kind/shape rejection, live completion and grant revocation |
| PDF | Immutable complete snapshot, more causes than a UI page, every source identifier in rendered output, all five sections, completion/reopening evidence, A4 geometry, empty/long/oversized rows, repeated headers, escaped markup, Latin accents and unsupported glyph rejection |
| Export security and consistency | Read/export denial before existence, current grants and final deactivation/revocation, concurrent writes do not mix snapshot sections, HTTP rendering holds no idle read transaction, renderer faults/partial output produce safe failure without PDF bytes |
| Type retirement | Missing/malformed/stale/current revision behavior, authorization before lookup/preconditions, duplicate headers/body rejection, historical snapshots retained, retired capture rejection, injected rollback, real PostgreSQL capture/retirement/grant-revocation lock races |
| OpenAPI | Bearer security, required/defaulted response properties, typed filters, JSON multipart schema, resolvable references, binary PDF media, ETag/cache headers, safe Problem vocabulary, bounded route surface |

Tests are in [reporting unit tests](../tests/test_reporting_unit.py),
[reporting PostgreSQL tests](../tests/test_reporting_postgres.py), and the
updated [route-boundary regression](../tests/test_postgres.py).
The [application factory](../qualitytrack/main.py) registers reporting routes
and installs the generated OpenAPI declarations.

## Quality and change boundaries

- Black check: **28 files unchanged**.
- Ruff: **all checks passed**.
- Dependency compatibility: **40 installed packages compatible**, using the
  Python 3.11 environment.
- `git diff --check`: passed.
- No migration, dependency pin, seed-grant or saved design change.
- No `.env` reads/edits, published credentials, remote URL disclosure, or changes
  to `.kavia/` or `logs/`.
- Existing private PostgreSQL storage was reused; test shells are cleaned up
  separately without destroying the cluster.

## Limits

Automated PDF text/pagination/geometry checks do not establish manual visual
readability, accessibility certification, general Unicode support or production
resource/performance readiness. Photo handling, analytics/stubs and auditor
stories remain excluded. Large-record memory budgets, production provisioning,
identity/session policy and the residual race after final authorization remain
explicitly outside acceptance claims; see the contract report.
