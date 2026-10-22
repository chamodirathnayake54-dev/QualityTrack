# Operations and rollback — REL-2026.10.22-prep

## Operating boundary and ownership

This proposed runbook applies to an isolated, synthetic-data, single-plant engineer demonstration. It does not establish a production deployment architecture. Before use, the release owner must name an operator, database owner, security contact, and product approver, identify the running artifact and last-known-good artifact, and record the observation window and stop authority. Those assignments, recovery-time objective, recovery-point objective, backup location, and approved deployment commands are not established by repository evidence.

Use the [backend setup](../../README.md) and [frontend setup](../../../frontend/README.md) for supported startup and verification. Do not turn a disposable demo helper into a production provisioner.

## Critical operational assumptions

| Area | Evidenced behavior and required assumption |
| --- | --- |
| Runtime | Backend documentation requires Python 3.11 and PostgreSQL 16. Frontend requires Node 22. Pinned dependencies and matching Playwright browser binaries are needed for the documented checks. |
| Backend configuration | `DATABASE_URL` must use the PostgreSQL psycopg SQLAlchemy scheme. `JWT_SECRET_KEY` must have at least 32 UTF-8 bytes. `PLANT_TIMEZONE` must be a valid IANA zone; `Etc/UTC` defaults only when `QT_DEMO_MODE` is exactly `true`. Backend settings do not load `.env`. |
| Seed configuration | `SEED_PASSWORD_ENGINEER`, `SEED_PASSWORD_SUPERVISOR`, and `SEED_PASSWORD_AUDITOR` are operator-injected secrets for explicit demo seeding. Do not retain values, hashes, tokens, or connection strings in documentation, shell history, logs, or evidence. There is no automatic startup seed. |
| Frontend configuration | Apply public `VITE_API_BASE_URL=/api/v1` before startup/build as applicable. The application has no implicit fallback. Restart Vite after configuration changes. `API_PROXY_TARGET` is an optional development proxy origin; the default is loopback port 8000. No frontend variable may contain secrets. |
| Routing | Production static hosting needs same-origin `/api` forwarding, unchanged API paths, and SPA fallback only for application routes. API failures must not become HTML success responses. The Vite development proxy is not a production proxy. |
| Identity and authority | Use permitted synthetic accounts and persisted explicit grants. Display names/personas confer no authority. Do not grant permissions to bypass a 403. Reload requires sign-in; sign-out clears browser state but does not revoke the issued backend token. |
| Data | Use synthetic records and active lookup IDs returned by the actual environment. Capture snapshots are historical evidence, not live labels. The seed verifies exact fixtures and refuses discrepancies instead of repairing grants. |
| Database roles | Run migrations with an appropriate administrative role and the API with a separately provisioned least-privileged role. Batch 2 real-stack QA used an administrator connection, so it did not qualify deployment-role restrictions. |
| Calendar and scope | Verify `/api/v1/me` reports the intended plant zone. QA Batch 2 used `Etc/UTC`; broader DST, persona, PDF visual, performance, and accessibility acceptance are not established. |
| Recovery | A compatible last-known-good artifact, securely managed configuration, and a tested backup/restore path must exist before retained-data use. Repository evidence does not establish a release registry or automated rollback service. |

The disposable helper stores data outside Git in a private temporary directory and binds its API to loopback. Its `recreate --confirm-disposable` command destroys its cluster, including test databases. It must never be a normal restart, rollback, or retained-data recovery step.

## Startup and pre-use checks

The operator should confirm the environment is isolated, the approved artifact and configuration are selected, and the database is migrated to the reviewed revision before starting services through the approved supervisor. For an already provisioned disposable demo, the backend README documents `python scripts/demo_db.py api` from `backend/`; recreation is not required to start the API.

Confirm frontend deep links and same-origin API routing, then run the [smoke checks](smoke-checks.md). Inspect current identity, grants, active lookups, plant timezone, and retained synthetic data. The inspected API entry point does not define a dedicated health endpoint; a served static page or OpenAPI document alone is not evidence of database readiness. Successful authorized identity and record reads are stronger bounded probes.

## What to watch

These are proposed manual observations, not claims of implemented dashboards or alerts. Observe during initial use and after a restart or rollback; record safe status codes, Problem codes, timestamps, and synthetic record identifiers without credentials or raw authentication traffic.

| Signal | Interpretation and response |
| --- | --- |
| Configuration required or startup configuration failure | Check public API base or securely injected backend configuration. Restore approved settings; do not add an implicit client fallback. |
| Repeated 401 or 403 | Confirm session, active identity and exact current grants. Reauthenticate for 401; investigate 403 rather than broadening authority. |
| 409, 412, 428 or malformed-revision 400 | Distinguish lifecycle/lookup conflict from stale, missing, or malformed review tokens. Refresh and explicitly review again; never replay a transition automatically. |
| 500, persistence-related 503, or failed reads | Pause writes and inspect database connectivity/configuration through safe operator diagnostics. A known closed-parent action-reopen policy 503 is distinct from persistence failure. |
| Unconfirmed write outcome | Stop resubmission. Read the parent and associated collection; have QA/database owner reconcile if necessary. The original request may have committed. |
| Duplicate actions or unexpected counts/revisions | Pause writes and preserve evidence. No general duplicate suppression or idempotency is promised. |
| Wrong actor, plant time, lookup snapshot, or missing history | Treat as an integrity stop condition; involve QA and the database owner before further mutation. |
| Data appearing after identity change | Stop use immediately and escalate to security; preserve sanitized evidence without exposing the prior user's data. |
| Photo, export, or supervisor journey requested | Explain scope limits. Missing screens are not transient outages; do not claim full-product readiness. |

## Rollback decision and procedure

Trigger a stop for failed engineer smoke checks, suspected data leakage, integrity mismatch, sustained persistence failure, or a failed startup/routing change that prevents the bounded journey. The incident owner decides rollback with the database owner; suspected security exposure also requires the security owner. A concurrent-edit conflict alone is normally a refresh/review event, not a rollback trigger.

First stop new user activity and stop or isolate write-serving processes through the environment's approved supervisor or routing controls. No application-level maintenance-mode switch is established here. Preserve sanitized failure evidence and record candidate identity, schema revision, configuration version references, affected synthetic IDs, and last successful operation. Do not replay uncertain requests.

Next reconcile possible committed writes and verify database health. For an application/configuration regression with a compatible unchanged schema, restore the approved last-known-good application artifact and configuration using the environment's approved mechanism while retaining the database. Do not invent a Git reset, mutable source checkout, or database downgrade as an artifact deployment mechanism. If no compatible prior artifact exists, remain stopped and prepare a reviewed forward fix.

If data integrity is damaged, the database owner must preserve the current state and restore a verified backup into an isolated recovery target. Compare schema, identities/grants, record counts, causes, actions and history before switching traffic. Explicitly approve any loss of post-backup writes and reconcile them under an auditable procedure. Do not delete or edit append-only history to conceal a partial operation.

Finally restart with approved configuration, repeat the smoke checks, and compare representative preincident records and history as well as newly created synthetic data. The incident owner must authorize reopening after QA and database-owner review. Retain incident and recovery evidence; a recovered UI alone does not close security or integrity concerns.

## Migration reversibility and failure scenarios

Revision `0001` loads the frozen `migrations/initial_schema.py`; upgrade creates the full schema and downgrade calls `drop_all`. This is structural reversibility only, with data destruction on downgrade. The docstring limits downgrade to explicitly disposable databases; the implementation does not itself enforce a disposable-target guard. Never downgrade a retained-data environment as ordinary rollback.

On a separately authorized empty/disposable target with migration credentials injected, a database owner can rehearse the following from `backend/`:

```sh
alembic upgrade head
alembic current
alembic downgrade base
alembic upgrade head
alembic current
```

This sequence destroys schema data at downgrade and is not a backup/restore test. It was not executed for this docs-only batch. Retained-data reversibility requires a separately rehearsed restore and compatible application recovery.

| Failure scenario | Safe action and return-to-service requirement |
| --- | --- |
| Upgrade fails or revision is unexpected | Stop API writes; database owner checks actual Alembic/schema state before retry or recovery. Do not assume clean rollback or use `stamp` to hide drift. |
| Frontend cannot reach API after routing/config change | Restore reviewed routing/public configuration and artifact; verify real identity/read requests and deep links, not just static loading. |
| API fails database/config startup | Restore approved injected settings and connectivity; preserve the database and verify authorized reads before writes. |
| Action response is lost | Reconcile actual action collection/database state; do not automatically retry. Resume only when the outcome is understood. |
| Seed refuses changed fixtures/grants | Investigate drift and ownership. Do not recreate retained data or silently restore permissions. |
| Previous artifact is incompatible or backup cannot be restored | Keep service stopped. Database and release owners must supply a verified recovery option or approved forward fix. |
