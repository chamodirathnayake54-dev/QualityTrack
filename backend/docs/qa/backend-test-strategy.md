# QualityTrack Backend Test Strategy

## Document status and baseline

This strategy is the Stage 5, Batch 1 deliverable for session QA-06-QualityTrack-Backend-v5. It is proposed for user approval alongside the [endpoint inventory](endpoint-inventory.md). It is not an execution report, implementation plan, test-case collection, or Go / No-Go recommendation.

The verified starting commit is `b9396df057fd98e30631c952338fa815e06768df`. Required Batch C commit `e0a24dc` appears in `git log --oneline -5`, and `git merge-base --is-ancestor e0a24dc HEAD` returned 0. The four required files existed. HEAD and ancestry remained unchanged at the pre-generation recheck.

Only documentation is authorized in this batch. No application or test changes, commits, pushes, or Batch 2 matrices are included. The initial untracked `.kavia/` and `logs/` directories remain outside scope.

## Product and change context

QualityTrack is a bounded, single-plant demo backend using Python 3.11, FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, and PostgreSQL 16. Its implemented API supports local identity, capture lookups, photo-free defect capture, investigation and closure, corrective work, retained history, overdue work, protected PDF evidence, and defect-type retirement.

The strongest quality risks concern incorrect authority, lost or contradictory workflow evidence, concurrent command ordering, stale revisions, calendar boundaries, and incomplete exports. Current grants are persisted and reloaded; production identity federation and general organizational authority policies are not implemented.

The [Batch C contract-drift report](../batch-c-contract-drift.md) records settled demo boundaries. Runtime code is the source of truth for what is implemented; approved requirements and settled decisions remain the behavioral oracle. A conflict must be recorded and reviewed rather than silently redefining acceptance to match code.

## Quality objectives

Stage 5 should establish observable confidence that all 20 implemented operations preserve their wire contracts and business rules, that denied or failed commands do not alter persisted state or evidence, and that authorized critical workflows remain consistent under concurrency.

Later qualification must produce an explicit operation-level coverage denominator, safe and reproducible execution evidence, at least 95% live-response schema-validation coverage under the definition below, and two full Python 3.11 suite runs in Batch 4. These are future gates, not Batch 1 achievements. Passing counts alone do not establish release readiness.

## Scope and exclusions

All operations in the endpoint inventory are in scope. Direct validation should cover authentication, explicit grants, request/response contracts, multipart capture, filters and signed pagination, lifecycle gates, parent/type revision handling, transaction rollback, retained history, overdue calendars, complete PDF evidence, and retirement/capture coordination.

The highest-priority backend journey is login, permitted lookup, capture, record/read a cause, investigate, assign and complete work, close, review history, and export evidence. Supervisor-authorized reopening and subsequent completion cycles require retained evidence. Retirement is a separate configuration journey using an explicitly granted disposable fixture, not an invented seed permission.

Photos, analytics or stubs, auditor-story acceptance, frontend/browser behavior, notification systems, production identity provisioning, general multi-plant entitlements, and duplicate suppression are excluded by settled scope. A backend test using the existing auditor fixture does not claim acceptance of excluded auditor stories.

This strategy does not authorize production load testing, destructive testing against shared data, schema changes, dependency upgrades, or new capabilities. Performance budgets, production SLOs, regulatory applicability, and deployment acceptance requirements are not supplied and must not be invented.

## Risk assessment and priorities

Likelihood ratings below are planning judgments based on implementation complexity, not measured incident rates. P0 denotes highest-risk validation and release-blocking failures; P1 denotes important validation whose unresolved findings require explicit disposition.

| Risk | Impact | Likelihood | Priority | Planned validation | Residual risk |
| --- | --- | --- | --- | --- | --- |
| Revoked, inactive, or incorrectly privileged callers access data or mutate state. | High | Medium | P0 | Exercise persisted grants, deactivation, owner/supervisor boundaries, disclosure ordering, post-lock refresh, and final export authorization. | Revocation after the final delivery check is not eliminated. |
| Concurrent commands lose revisions, permit invalid closure, or create contradictory evidence. | High | High | P0 | Use real PostgreSQL lock waits and competing transactions; reconcile state, revision, and child/event counts. | Untested production topology and workload remain unknown. |
| Rejected or failed commands partially persist. | High | Medium | P0 | Inject post-flush faults and verify committed state is unchanged across command families. | Infrastructure crash recovery is not established by transaction tests alone. |
| PDF omits rows, mixes revisions, leaks evidence, or returns partial output. | High | High | P0 | Reconcile full snapshot and rendered identifiers, exceed page sizes, inject concurrent writes/render faults, and revoke authority during render. | Large-record memory and visual readability remain unqualified. |
| Cursor replay or live-page behavior leaks data or produces incorrect membership. | High | Medium | P0 | Reject altered caller, context, resource, filter, zone, and signature; verify equal sort keys and fresh authorization. | Live pages are not snapshot-consistent exports. |
| Capture and retirement race corrupts historical context. | High | Medium | P0 | Verify both lock winners, grant refresh, active lookup rejection, atomic type revision, and preserved labels. | Direct privileged SQL remains an operator trust boundary. |
| DST, local midnight, or evaluation-date changes misclassify work. | Medium | High | P1 | Use aware fixed instants, short/repeated DST hours, inclusive date filters, due-today exclusion, and pinned continuations. | Only an approved representative zone set can be claimed. |
| Schema declarations differ from actual response bodies or media. | Medium | Medium | P1 | Reconcile all operations, resolve schema references, and validate actual success/error responses plus headers and PDF semantics. | Structural validation does not prove business correctness. |
| Seed/migration/privilege drift invalidates test assumptions. | High | Medium | P0 | Verify migrated schema, exact grants, discrepancy refusal, restricted application role, and immutable-history privileges. | This is not a production provisioning or tamper-proof-ledger assessment. |

## Test levels and techniques

### Existing lower-level assets

The repository already has database-free tests in [test_unit.py](../../tests/test_unit.py), [test_services.py](../../tests/test_services.py), [test_workflow_unit.py](../../tests/test_workflow_unit.py), and [test_reporting_unit.py](../../tests/test_reporting_unit.py). They inspect input boundaries, credentials/tokens, permissions, projections, cursors, revisions, workflow gates, calendars, PDF rendering, and generated OpenAPI contracts.

These tests are the preferred fast feedback layer. They should execute in the pinned Python 3.11 environment without a running database when selecting only database-free files. Their mocked dependencies do not prove PostgreSQL transaction, lock, or privilege behavior.

### API and real-database integration

[test_postgres.py](../../tests/test_postgres.py), [test_workflow_postgres.py](../../tests/test_workflow_postgres.py), and [test_reporting_postgres.py](../../tests/test_reporting_postgres.py) use real PostgreSQL-backed fixtures and FastAPI TestClient. They cover migration/seed assumptions, authenticated HTTP behavior, rollback, keysets, competing locks, export snapshots, and retirement.

Real PostgreSQL is required for lock, isolation, constraint, and role evidence; an SQLite substitute is not adequate. Concurrency checks should observe actual lock waits, not infer locking merely from a scheduling delay. Rejections must be checked against database state, aggregate revisions, and evidence counts, not just HTTP status.

TestClient exercises the backend stack but is not proof of a separately deployed network service. Any later deployed-service smoke validation must identify its environment and must not be conflated with in-process API evidence.

### Critical workflow, exploratory, and acceptance validation

A concise backend workflow regression should connect capture, causes, investigation, work assignment/completion, closure, reopening, history, and export using persisted records and fresh ETags. Lower-level suites should handle exhaustive boundary combinations rather than multiplying long end-to-end journeys.

Exploratory review should target ambiguous request-validation precedence, conditional completion/reopening evidence, unusually long PDF content, live continuation changes, and failure confidentiality. Manual PDF readability review is useful but must be reported separately from automated text/geometry checks.

The requester is the approval authority for batch progression and residual-risk acceptance. Business/user acceptance beyond the settled demo scope is not demonstrated by the existing backend suites. Detailed AC mappings and API/failure-mode matrices are deferred to Batch 2; no AC identifiers are invented here.

## Non-functional validation

Security validation should prioritize bearer verification, current persisted grants, inactive callers, authorization before valid-record disclosure, owner/supervisor restrictions, secret-safe Problems, no-store headers, cursor integrity, and least-privileged database access. Any credentials, token values, connection strings, protected evidence, or raw database exceptions must be removed from retained reports.

Reliability validation should establish atomic rollback, lock serialization, coherent repeatable-read export snapshots, no partial PDF delivery, and fail-closed calendar/authority behavior. Repeated additive requests may create distinct records; duplicate suppression and safe automatic retry are not guarantees.

Compatibility validation should use the declared Python range `>=3.11,<3.12`, pinned dependencies, PostgreSQL 16 environment, generated OpenAPI, and migrated schema. No broader version matrix is claimed.

Performance and resource observations may be recorded during approved execution, especially for complete in-memory PDF snapshots and long rows. There is no approved latency, concurrency, memory, or capacity threshold. Resource budgets require owner agreement before becoming release gates; the strategy does not permit evidence truncation to meet an arbitrary limit.

Frontend accessibility is outside this backend-only scope. PDF accessibility certification, general Unicode support, and production privacy/compliance certification are not established. Applicable legal obligations are unknown; no GDPR-specific compliance claim is made.

## Environments and test data

The repository [backend guide](../../README.md) describes setup and the disposable PostgreSQL helper. The pinned environment is defined in [pyproject.toml](../../pyproject.toml). The integration [fixtures](../../tests/conftest.py) create uniquely named per-test databases, apply migrations and application-role grants, seed random test passwords, and drop databases in teardown.

The private host-local helper cluster must exist before integration execution. Tests intentionally fail rather than silently skip when required private metadata is unavailable. Do not recreate or reset a cluster while an API or test run uses it. Destructive helper setup requires the operator's explicit disposable-environment confirmation.

Use synthetic part numbers, causes, owner fixtures, dates, and evidence. Cover minimum/maximum quantities and lengths, malformed/extra fields, unknown UUIDs, active/retired choices, all lifecycle states, missing/revoked grants, equal ordering keys, empty/multiple pages, and DST/local-midnight boundaries. Inject times where services support them rather than relying on wall-clock timing.

Configuration and seed passwords must be injected securely. Neither the application nor helper loads `.env` automatically. Never include secret values or private helper metadata in logs, shell transcripts, screenshots, documents, or Git. Test databases must not share production or user data.

Environment readiness has not been exercised in Batch 1. No database setup, service launch, dependency installation, or test run was needed for source-based documentation.

## Automation and delivery integration

The existing pytest suite is the automation base. After approval, missing tests should be added only where Batch 2 establishes a genuine gap against the verified baseline. Every confirmed defect fix must include a regression test. This batch authorizes neither fixes nor new tests.

The proposed cadence is fast database-free feedback during development, full real-database validation for backend changes, and sequential qualification runs before final release recommendation. CI wiring and job durations have not been verified; this is a proposed execution policy rather than a claim that such gates are installed.

Future non-interactive execution should use the same Python 3.11 environment for the existing commands below, from `backend/`, after approved environment preparation:

```sh
python -m pytest -q tests/test_unit.py tests/test_services.py tests/test_workflow_unit.py tests/test_reporting_unit.py
python scripts/demo_db.py test
black --check qualitytrack migrations scripts tests
ruff check .
```

The full-suite command should be run twice sequentially in Batch 4 against the same final candidate. Each run must retain its own result and baseline identifier. Failures must be triaged; rerunning to hide intermittent failures is not acceptable.

The authoritative sequence remains Batch 1 inventory/strategy approval, Batch 2 API and failure-mode matrices with AC/test mappings, Batch 3 missing tests and live-response schema evidence, and Batch 4 defect disposition, Go / No-Go, and two full-suite runs. No later deliverable is created in this batch.

## Defect management

A confirmed defect requires a reproducible baseline, sanitized request/setup, expected behavior with its approved oracle, observed behavior, impact, and persisted-state evidence where relevant. Distinguish an environment failure, test error, intentional scope decision, and product defect before changing application behavior.

Critical severity includes unauthorized disclosure/mutation, lost evidence, or severe data-integrity failure. High severity includes failure of a critical lifecycle or complete export. Medium severity covers bounded contract or calendar defects with limited impact; low severity covers minor issues that do not compromise protected workflows. Delivery priority is assigned separately according to release risk.

For a confirmed defect, reproduce it, add a regression test, apply only the necessary approved fix, and rerun focused and affected regression suites. Security/data-integrity findings require immediate escalation to the requester and backend owner. A passing retest is required before closure. The formal defect log belongs to Batch 4.

## Metrics and reporting

Report operation coverage using the 20-operation inventory, critical-path pass/fail, executed versus blocked/skipped checks, high-risk failure-mode coverage, unresolved defects by severity, and repeat-run stability. A test-function count is not an operation-coverage percentage, and static OpenAPI assertions are not live-response schema-validation evidence.

For Batch 3, use this explicit proposed measurement: live-response schema-validation coverage is `100 × operations with a captured actual successful response validated against the matching generated OpenAPI success contract ÷ 20`. At least 95% means at least 19 of 20 operations. Target all 20; any omission must be named with its reason and residual risk, never hidden by changing the denominator.

Validate JSON responses using the matching operation/status/media schema, resolved references, required properties, types, enums, formats, and nullability. PDF success requires binary media, complete PDF framing, attachment and cache headers, and content/evidence checks rather than pretending the bytes are JSON. Record PDF validation explicitly in the numerator rationale.

Separately report actual error-response schema checks, status/media/header agreement, the number of captured responses validated, and validation failures. Keep coverage and conformance distinct: the coverage threshold does not authorize known schema violations or exclude unsuccessful validation attempts from the report. A declaration inspection alone must not count as a validated live response.

The schema-validation mechanism has not yet been implemented or selected. JSON Schema/OpenAPI tooling compatibility and the measurement interpretation require confirmation during Batch 1 approval or Batch 2 design, before Batch 3 execution.

Historical [Batch C validation](../batch-c-validation.md) records two runs with 319 passes each, comprising 210 unit/service cases and 109 PostgreSQL cases. These are prior reported results, not fresh Stage 5 results. Its historical pending-commit narrative is superseded for this session by the observed Git baseline; it is not evidence that Batch C is currently uncommitted.

## Entry, exit, and release criteria

| Gate | Required evidence and decision |
| --- | --- |
| Batch 1 entry | Required recent Batch C log entry, successful ancestry check, required files, stated HEAD, and documentation-only scope. This passed. |
| Every subsequent step | State the current HEAD and verify required ancestry before work; stop on failure. If the baseline changes, identify and review the change rather than silently reusing prior evidence. |
| Batch 1 exit | Source-reconciled inventory and strategy returned to the requester; no code/test changes, commits, pushes, or Batch 2 work. Approval remains pending. |
| Formal execution entry | Approved scope and matrices, known AC sources, Python 3.11 and pinned dependencies, disposable PostgreSQL readiness, isolated data, and safe evidence capture. |
| Batch 3 exit | Agreed missing tests completed, approved defect handling with regression tests where applicable, actual response evidence, and at least 95% schema-validation coverage with all gaps/violations disclosed. |
| Batch 4 exit | Full Python 3.11 suite passes twice on the same final candidate, critical/high risks resolved or explicitly dispositioned, and defect log plus reasoned Go / No-Go submitted. Blocked/skipped required checks cannot masquerade as passes. |
| Commit/push | Explicit requester approval is required. Any later approved push must show `git ls-remote` evidence safely. No such action is authorized or performed in Batch 1. |
| Release decision | Requester accepts or rejects the evidence and remaining risks. No Go recommendation is made in Batch 1. |

## Roles and responsibilities

The requester owns batch approval, scope decisions, permission to commit/push, and final residual-risk acceptance. The backend developer owns approved fixes and regression coverage. The QA executor owns matrices, reproducibility, execution evidence, schema-validation reporting, and defect verification.

The environment operator owns safe disposable PostgreSQL provisioning, injected configuration, and cleanup coordination. A security/operations owner should review production authority, revocation, resource, and monitoring questions if production readiness is later requested.

These are proposed role assignments, not named staffing commitments. Owners and availability must be confirmed before formal execution; unassigned production concerns remain visible risks rather than implicit QA ownership.

## Assumptions, dependencies, and residual risks

No incident history, deployed-service access, production workload, operational SLO, CI configuration evidence, regulatory determination, or named acceptance owner beyond the requester was established in this batch. No fresh code-coverage or live-response conformance percentage is available.

The settled demo binds eligible owners and supervisor authority to explicit fixtures. Broader non-demo authority/eligibility behavior fails closed where policy is unavailable. Existing reserved persistence tables do not imply delivered photo features, and privileged SQL is not prevented from changing evidence by an application-level audit claim.

Complete export uses memory proportional to the complete record and rendered output. Automated reconciliation does not establish manual visual acceptance, PDF accessibility, general font coverage, or production capacity. A residual revocation race remains after final authorization and before/during delivery.

The detailed AC source reconciliation is deferred to Batch 2. Missing or conflicting AC definitions must be raised for decision; no unsupported AC IDs or acceptance claims should be fabricated.

## Review cadence and approval record

Review this strategy when the baseline changes, after a confirmed defect, when the endpoint surface or settled policy changes, and at each batch boundary. Refresh affected evidence rather than treating this snapshot as permanently current.

Batch 1 source inspection and AST-based counting confirmed 20 operations, 17 paths, 13 GET, and 7 POST. Git baseline and ancestry checks passed, and the pre-generation `git diff --check` reported no errors. No pytest, live HTTP, PostgreSQL, load, or manual PDF validation was performed.

The requested artifacts are complete for review. Approval status is **pending**. Work stops here; Batch 2 may begin only after user approval.

## Evidence references

The runtime evidence is in [main](../../qualitytrack/main.py), [security](../../qualitytrack/security.py), [capture/read services](../../qualitytrack/defects.py), [workflow services](../../qualitytrack/workflow.py), [reporting](../../qualitytrack/reporting.py), [evidence export](../../qualitytrack/evidence.py), [OpenAPI](../../qualitytrack/openapi.py), and [safe errors](../../qualitytrack/errors.py).

Existing automated assets are linked in the test-level sections. Environment and historical evidence are provided by the [backend guide](../../README.md), [dependency configuration](../../pyproject.toml), [integration fixtures](../../tests/conftest.py), [Batch C drift report](../batch-c-contract-drift.md), and [Batch C validation](../batch-c-validation.md). The companion [endpoint inventory](endpoint-inventory.md) provides the operation denominator and current wire-contract summary.
