# Stage 5 backend QA — Batch 3 validation

## Revision and scope

Base commit: `b26c9888bd210da72c9767cf7f7d46cdd98bfd99`.
Required ancestor: `e0a24dc`; the Git ancestry gate passed before investigation,
focused regression, full-suite launch, and HTTP validation.

Evidence describes the proposed working tree, not a new commit. No commit or
push was made. Photos and analytics remain excluded. The approved gap tests
were preserved and extended only for the confirmed cursor defect.

Related documents:

- [Defect log](defect-log.md)
- [API test matrix](api-test-matrix.md)
- [Failure-mode matrix](failure-mode-matrix.md)
- [Endpoint inventory](endpoint-inventory.md)

## Confirmed fix

QA-B3-001 is a repository-owned cursor conversion defect. Only narrow string
guards were added to UUID conversion boundaries in `workflow.py`, `security.py`,
and `reporting.py`. History revision cursors already validate types correctly.
See the defect log for source excerpts and safe request/response evidence.

## Real HTTP and live schema validation

Execution used Python 3.11.17, the repository disposable PostgreSQL 16 helper,
and `scripts/demo_db.py api`, serving Uvicorn on loopback. A generated throwaway
login password was held in process memory and only its Argon2 hash was stored
in the disposable demo database. Authentication tokens and signed continuations
were held in memory. No `.env` file was read or changed.

The helper retains its existing owner-only local database metadata; this is
distinct from the ephemeral login password. Only the helper-owned demo database
was modified. An explicit `type.retire` grant was added to the disposable
engineer fixture to exercise retirement success, without changing product
authorization or seed policy.

The reproducible harness is [scripts/qa_batch3.py](../../scripts/qa_batch3.py).
It requires an already recreated, fresh demo database and uses the QA
environment's preinstalled `jsonschema` 4.26.0 as validation tooling, not as an
application runtime dependency. Run from `backend` with the QA interpreter:

```text
PYTHONPATH=. python scripts/qa_batch3.py
```

The harness starts and terminates its own API process and suppresses access
logs. Recreate the disposable database before repeating it, because retirement
intentionally changes fixture state.

### Method and accuracy

- Fetched `/openapi.json` from the running API; no static schema substitute.
- Used `Draft202012Validator` with `FormatChecker`, resolving local
  `#/components/schemas/...` references through the live components object.
- Matched actual status and response Content-Type to the live declaration.
- Validated every executed API response body, including login, all successes,
  all authentication Problems, and all malformed-cursor Problems.
- Checked `Cache-Control: private, no-store` on every API response.
- PDF: validated the declared binary-string schema using a lossless Latin-1
  representation, plus `%PDF-` and terminal `%%EOF` checks. A binary schema
  does not establish full PDF semantic correctness.
- Live schema acquisition is setup, not an API-operation response in the metric.

**Result: 46 / 46 executed API responses schema-valid = 100.0%**, above the
95% target. All **20 / 20 operations** were exercised successfully and with an
authentication rejection. This is a measured response-sample accuracy, not a
claim that all possible responses or error paths were exercised over HTTP.

### Sanitized operation evidence

All paths below have prefix `/api/v1`. Each row represents one success and one
401 response. Every listed response validated. Success media is
`application/json`, except the PDF; every 401 is `application/problem+json`.

| Method | Route template | Success | Authentication Problem | Validation |
| --- | --- | --- | --- | --- |
| POST | `/auth/login` | 200 | 401 (invalid credentials) | Both pass |
| GET | `/me` | 200 | 401 | Both pass |
| GET | `/production-lines` | 200 | 401 | Both pass |
| GET | `/shifts` | 200 | 401 | Both pass |
| GET | `/defect-types` | 200 | 401 | Both pass |
| GET | `/defects` | 200 | 401 | Both pass |
| POST | `/defects` | 201 | 401 | Both pass |
| GET | `/defects/{defect_id}` | 200 | 401 | Both pass |
| POST | `/defects/{defect_id}/causes` | 201 | 401 | Both pass |
| GET | `/defects/{defect_id}/causes` | 200 | 401 | Both pass |
| POST | `/defects/{defect_id}/transitions` | 200 | 401 | Both pass |
| POST | `/defects/{defect_id}/actions` | 201 | 401 | Both pass |
| GET | `/defects/{defect_id}/actions` | 200 | 401 | Both pass |
| GET | `/assignable-users` | 200 | 401 | Both pass |
| POST | `/actions/{action_id}/transitions` | 200 | 401 | Both pass |
| GET | `/defects/{defect_id}/history` | 200 | 401 | Both pass |
| GET | `/actions/{action_id}/history` | 200 | 401 | Both pass |
| GET | `/overdue-actions` | 200 | 401 | Both pass |
| GET | `/defects/{defect_id}/audit.pdf` | 200 (`application/pdf`) | 401 | Both pass |
| POST | `/defect-types/{type_id}/retire` | 200 | 401 | Both pass |

Additional six responses, all schema-valid `400 application/problem+json` with
code `invalid_cursor`:

| Method | Route template | Scenario |
| --- | --- | --- |
| GET | `/defects/{defect_id}/actions` | Non-string UUID position |
| GET | `/defects/{defect_id}/causes` | Aware timestamp, non-string UUID position |
| GET | `/defects/{defect_id}/history` | Boolean revision |
| GET | `/actions/{action_id}/history` | Boolean revision |
| GET | `/overdue-actions` | Valid date positions, non-string UUID position |
| GET | `/defects` | Aware timestamp, non-string UUID identifier |

### Problem and 500 declarations

The live schema declared `500` with `application/problem+json` for all 20
operations. All executed Problems selected that media type and validated.
No live 500 was deliberately induced; fault injection remains automated-test
coverage, not part of the 46-response live sample.

## Automated checks

Python: **3.11.17**.

```text
python -m black --check qualitytrack tests scripts
27 files would be left unchanged.
python -m ruff check qualitytrack tests scripts
All checks passed!
```

Focused active regression:

```text
python -m pytest -q tests/test_batch3_gaps.py -k 'g10 or signed_malformed_list'
16 passed, 41 deselected, 1 warning in 18.48s
```

Two captured full-suite runs on the same proposed code and base commit:

```text
python -m pytest -q
376 passed, 1 warning in 167.51s (0:02:47)
python -m pytest -q
376 passed, 1 warning in 164.53s (0:02:44)
```

Both runs completed without failures, skips, or expected failures. The warning
is Starlette's deprecated AnyIO `BlockingPortal` alias. An earlier command's
tool wait timed out while pytest continued; its output could not be retrieved,
so no counts from that command are claimed. The captured replacement runs above
are the full-suite evidence.

## Evidence handling

Only route templates, statuses, media types, validation outcomes, safe Problem
content, tool versions, and test summaries are retained here. No tokens,
passwords, database connection values, signed cursor values, or raw access logs
are included.
