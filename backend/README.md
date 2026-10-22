# QualityTrack backend — Batch A

Disposable, single-plant demo built with Python 3.11, FastAPI, Pydantic 2,
SQLAlchemy 2, Alembic and PostgreSQL 16. The saved QualityTrack LLD is the design
contract; this implementation deliberately stops at Batch A.

## Setup

Run from `backend/` using Python 3.11. Install the pinned dependencies from
[pyproject.toml](pyproject.toml), including the test and formatting tools:

```sh
python3.11 -m venv /tmp/qualitytrack-venv
/tmp/qualitytrack-venv/bin/python -m pip install -e .
```

The helper expects PostgreSQL 16 executables in `/usr/lib/postgresql/16/bin`.
Use the same interpreter/environment for all commands below. If using uv,
`uv venv --python 3.11 /tmp/qualitytrack-venv` and
`uv pip install --python /tmp/qualitytrack-venv/bin/python -e .` are equivalent.

## Configuration and disposable database

[.env.example](.env.example) lists names with empty values only. Neither the
application nor the helper reads `.env`. Request configuration from the operator
and inject values through the environment; do not paste secrets into terminal
commands, documentation, Git or chat.

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL SQLAlchemy URL using the psycopg driver |
| `JWT_SECRET_KEY` | Signing secret, at least 32 UTF-8 bytes |
| `QT_DEMO_MODE` | Exactly `true` permits demo seeding and the default calendar |
| `SEED_PASSWORD_ENGINEER` | Secure password for `sample-engineer` |
| `SEED_PASSWORD_SUPERVISOR` | Secure password for `sample-supervisor` |
| `SEED_PASSWORD_AUDITOR` | Secure password for `sample-auditor` |
| `PLANT_TIMEZONE` | IANA zone; defaults to `Etc/UTC` only in demo mode |

With demo mode and all three seed passwords securely injected:

```sh
python scripts/demo_db.py recreate --confirm-disposable
python scripts/demo_db.py api
```

**Recreate destroys this helper's entire disposable cluster**, including test
databases. It refuses to run without both demo mode and explicit confirmation,
and checks seed password availability before destroying existing data.

Storage is `/tmp/qualitytrack-demo-<uid>`, outside the workspace and Git. The
helper requires an owner-only directory (0700), private socket, and credential
metadata (0600). It rejects unsafe ownership, permissions and symlinks at the
checked storage boundaries. TCP listening is disabled. The local administrative
role uses trust authentication only inside that private socket; the application
role uses SCRAM and is not a superuser. No table grants include DELETE, and
RCA/status/action history cannot be updated by the application role. The helper
must not be used as a production database provisioner.

The helper creates database/signing credentials privately and passes them to
the API/test child process without printing them. The API binds loopback port
8000 with access logs disabled. Stop it with the process supervisor or Ctrl-C,
then stop the helper database:

```sh
python scripts/demo_db.py stop
```

The seed inserts the complete LLD 16.3 fixture atomically: three users, six
lookups, and exact plant-scoped grants. Subsequent runs verify the fixture and
preserve password hashes. Missing/changed fixtures, disabled users, changed
lookups or revoked/extra grants cause refusal, never silent repair. There is no
automatic startup seed. With configuration already injected, the explicit seed
entrypoint is `python -m qualitytrack.seed`.

## Implemented API

Swagger UI is `/docs`; the generated schema is `/openapi.json`. Eight operations
share seven paths:

| Method | Path | Required authority |
| --- | --- | --- |
| POST | `/api/v1/auth/login` | Active local username/password |
| GET | `/api/v1/me` | Active authenticated caller |
| GET | `/api/v1/production-lines` | `defect.capture` |
| GET | `/api/v1/shifts` | `defect.capture` |
| GET | `/api/v1/defect-types` | `defect.capture` |
| POST | `/api/v1/defects` | `defect.capture` |
| GET | `/api/v1/defects/{defect_id}` | `defect.read` |
| GET | `/api/v1/defects` | `defect.read` |

Login verifies Argon2id hashes and issues HS256 bearer tokens for 3600 seconds.
Current identity and persisted permissions are reloaded on requests; persona,
ownership and display names do not confer authority. The supervisor fixture
does not have capture authority, and no fixture has type-retirement authority.
Demo grants for later batches exist in the ERD/fixtures but expose no routes.

Capture accepts **multipart/form-data** with one `capture` part containing JSON:

```json
{
  "part_number": "SAMPLE-P100",
  "defect_type_id": "<UUID from permitted type lookup>",
  "quantity_affected": 3,
  "production_line_id": "<UUID from permitted line lookup>",
  "shift_id": "<UUID from permitted shift lookup>",
  "severity": "Major"
}
```

The UUID strings above are explanatory placeholders, not executable identifiers.
Severity is required and is exactly `Critical`, `Major` or `Minor`. Part numbers
are trimmed, nonblank and at most 50 characters. Quantity is a strict integer
from 1 to 1,000,000. Unknown/trusted metadata fields are rejected. A photo part
is rejected with no writes. Capture locks type, line and shift in that order,
checks availability, rechecks current authority after lock waits, then copies
codes/labels into immutable captured context. No duplicate suppression exists.
Capture ignores `If-Match`; successful capture/detail reads return an ETag.

Collection filters are AND-combined: `status`, `severity`, `production_line_id`,
`shift_id`, `defect_type_id`, exact `part_number`, and paired inclusive
`start_date`/`end_date`. Date boundaries use the configured plant calendar,
including DST, independently of the process timezone. Results order by
`created_at DESC, id DESC`; `limit` defaults to 50 and accepts 1–100.
`next_cursor` is signed and bound to caller, plant scope, filters, calendar and
ordering. A changed caller/filter/calendar or tampered token is rejected.
Pagination is a live view, not an export snapshot.

Errors use safe Problem envelopes and do not echo passwords or raw database
exceptions. Responses disable caching. There is no photo serving, inline
child history, cause/action workflow, transitions, overdue endpoint, PDF,
type-retirement operation or analytics implementation in Batch A.

## Schema and migrations

[models.py](qualitytrack/models.py) defines the full eleven-table ERD, including
future-batch tables. The single initial Alembic revision uses the frozen
[migration schema](migrations/initial_schema.py), not live application metadata.
It creates constraints, restricted foreign keys and indexes. Do not edit the
frozen schema to implement subsequent changes; add a new migration instead.

The helper applies `alembic upgrade head` using its administrative connection.
For externally provisioned disposable databases, inject `DATABASE_URL` for a
migration-capable role before running `alembic upgrade head`, then run the API
with a separately provisioned least-privileged application role.

## Verification

With the helper cluster initialized:

```sh
python scripts/demo_db.py test
python -m pytest -q tests/test_unit.py tests/test_services.py
black --check qualitytrack migrations scripts tests
ruff check .
```

The integration fixture creates a uniquely named database for every test,
applies the migration and grants, seeds random test passwords, then drops that
database in teardown. PostgreSQL tests do not silently skip if the helper is
missing. Do not run `recreate` while tests or the API are using the cluster.

Tests cover exact seed grants and discrepancy refusal, migration/model drift,
login/token handling, current identity and grant revocation, safe projections,
strict multipart capture, rollback, captured snapshots, lookup retirement lock
races, cached identity refresh, filters, DST boundaries and caller-bound keyset
pagination with equal timestamps.

See [Batch A validation](docs/batch-a-validation.md) for recorded results and
remaining validation limits.
