# Batch A validation

## Scope

Batch A only: backend scaffold, full ERD, one initial migration, private local
PostgreSQL helper, exact demo fixtures, authentication/current caller, active
lookups, photo-free capture and permitted detail/collection reads.

Batches B and C are not implemented. The full ERD and explicit future-operation
grants are schema/fixture foundations, not evidence of available workflow routes.
No design documents were modified.

## Executed checks

The final proposed implementation was tested using Python **3.11.17** and local
**PostgreSQL 16**, with every declared application/test dependency installed.

| Check | Result |
| --- | --- |
| Database helper recreate with explicit confirmation and environment-injected passwords | Passed; migration and seed completed |
| Final full suite, run 1 | 150 passed in 37.21 seconds |
| Final full suite, run 2 | 150 passed in 38.22 seconds |
| Unit subset | 96 tests |
| PostgreSQL integration subset | 54 tests |
| Black check | 17 Python files unchanged |
| Ruff check | All checks passed |
| uv dependency compatibility check | All 40 installed packages compatible |

Commands, run from `backend/` in the Python 3.11 environment:

```sh
python scripts/demo_db.py test
python scripts/demo_db.py test
black --check qualitytrack migrations scripts tests
ruff check .
```

Dependency consistency was checked with `uv pip check --python` targeting that
environment. The uv-created environment does not include the optional `pip`
module; `python -m pip check` was therefore unavailable, and the equivalent uv
check succeeded.

The only suite warning is a third-party Starlette TestClient reference to
AnyIO's deprecated `BlockingPortal` alias. No tests failed or were skipped in
the final runs.

## Evidence covered

- Frozen initial migration versus live SQLAlchemy metadata, all eleven tables,
  restrictive foreign keys, checked permission vocabulary and event evidence.
- Non-superuser application role, no DELETE grants on history and no UPDATE
  grants on RCA/status/action history.
- Seed rerun preserves credential hashes and exact grants; drift, deactivation,
  collisions and partial fixtures abort without repair.
- Argon2id credential verification, generic login denials, HS256 lifetime,
  invalid/expired/incorrectly scoped tokens, current persisted grants and safe
  caller-only projection.
- Five focused contracts for each lookup endpoint: denied access, empty result,
  safe projection, active predicate and code ordering.
- Five focused current-caller and five detail-service contracts, in addition to
  end-to-end identity and detail checks.
- Manual severity, strict numeric and string bounds, unknown/trusted input
  rejection, unsupported photo and malformed/duplicate multipart rejection.
- Snapshot preservation after lookup changes, authorization before disclosure,
  failed transaction rollback and database constraint rollback.
- Actual PostgreSQL lock waits for concurrent type/line/shift retirement:
  retirement-first rejects capture; capture-first retains its original snapshot.
- Fresh identity resolution rejects an account deactivated after its initial
  identity object was cached in the transaction.
- AND filters, paired plant-local dates across DST, strict query bounds,
  equal-timestamp UUID keyset ordering and caller/filter/calendar-bound cursors.
- OpenAPI contains exactly eight Batch A operations on seven paths and does not
  expose workflow, analytics, PDF or retirement routes.

Each PostgreSQL test uses its own randomly named database, migration and seed.
Teardown drops committed test data with the database. Repeated full runs do not
depend on a previously populated first page or the process timezone.

## Limits and remaining work

No Batch A validation blocker remains for the exercised local demo environment.
This is not a production security or performance certification: independent
penetration testing, load/SLO measurement, deployment/TLS controls, operational
backup/restore, external identity integration and production authority policy
review were not performed. The database helper intentionally trusts only its
owner-private administrative socket and is not a production provisioner.

The full workflow/transition suites and full OpenAPI header/conditional response
declarations belong to Batches B/C. Photo upload, analytics and auditor stretch
stories remain out of scope. No claims are made about those unimplemented
features.

Return to the [backend guide](../README.md) for setup, API scope and repeatable
verification commands.
