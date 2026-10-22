# QualityTrack Backend Endpoint Inventory

## Status and verified baseline

This is the Stage 5, Batch 1 inventory for session QA-06-QualityTrack-Backend-v5. It is submitted for user approval, not a release acceptance report. The companion [Backend Test Strategy](backend-test-strategy.md) defines the proposed validation approach.

Work began at commit `b9396df057fd98e30631c952338fa815e06768df` on `develop`, tracking `origin/develop`. Before backend analysis, `git log --oneline -5` showed required Batch C commit `e0a24dc`, and `git merge-base --is-ancestor e0a24dc HEAD` returned exit code 0. The required workflow routes, reporting routes, evidence service, and Batch C contract-drift report all existed. The same HEAD and ancestry were rechecked before document generation.

The initial worktree reported only untracked `.kavia/` and `logs/` directories. These were not changed. No application code or tests were modified, and no commit or push was performed.

## Scope and counting convention

The registered business API contains **20 method/path operations on 17 distinct paths: 13 GET operations and 7 POST operations**. An independent Python AST scan of the three route-registration files verified these totals without starting the application or accessing a database.

All paths in the register are relative to `/api/v1`. Query parameters are not part of a path identity. The three shared paths are `/defects`, `/defects/{defect_id}/causes`, and `/defects/{defect_id}/actions`; each supports GET and POST.

FastAPI's `/docs`, `/docs/oauth2-redirect`, `/redoc`, and `/openapi.json` are framework documentation surfaces, not additional business operations in this count. No health endpoint, analytics endpoint, photo endpoint, generic update/delete endpoint, grant-administration endpoint, or asynchronous export endpoint is registered.

## Endpoint register

All successful responses are JSON unless explicitly identified as PDF. All operations except login require a bearer token resolving to an active persisted caller. “Read” below means the explicit plant-scoped `defect.read` grant, not ownership-derived access.

The inventory identifiers are local documentation references, not acceptance-criterion IDs or a Batch 2 test matrix.

| ID | Method | Path after `/api/v1` | Request contract | Required authority | Success contract |
| --- | --- | --- | --- | --- | --- |
| E01 | POST | `/auth/login` | JSON `LoginRequest`: username and password. | Valid active local credentials; no bearer token required. | 200 `TokenResponse`: access token, bearer type, 3600-second lifetime. |
| E02 | GET | `/me` | No body or business query parameters. | Active authenticated caller; no additional operation grant. | 200 `MeView`: caller reference, display name, plant scope, sorted current permissions, plant zone. |
| E03 | GET | `/production-lines` | No body or business query parameters. | `defect.capture`. | 200 `LookupPage`; active choices ordered by code; null continuation. |
| E04 | GET | `/shifts` | No body or business query parameters. | `defect.capture`. | 200 `LookupPage`; active choices ordered by code; null continuation. |
| E05 | GET | `/defect-types` | No body or business query parameters. | `defect.capture`. | 200 `TypePage`; active choices with retirement flag and type revision; null continuation. |
| E06 | POST | `/defects` | Multipart with exactly one `capture` part containing Capture JSON; no photo part. | `defect.capture`, rechecked after lookup locks. | 201 `DefectView`; initial Open state and aggregate revision; parent ETag. |
| E07 | GET | `/defects` | Optional AND filters, signed cursor, and limit. | Read. | 200 `DefectPage`; live descending keyset collection. |
| E08 | GET | `/defects/{defect_id}` | UUID path identifier. | Read, checked before record lookup. | 200 `DefectView`; current parent ETag. |
| E09 | POST | `/defects/{defect_id}/causes` | UUID parent; JSON `CauseCreate` with text. | `cause.create`, refreshed under parent lock. | 201 `CauseView`; verified actor/time and updated parent revision/ETag. |
| E10 | GET | `/defects/{defect_id}/causes` | UUID parent; cursor and limit. | Read. | 200 `CausePage`; ascending recording time and ID. |
| E11 | POST | `/defects/{defect_id}/transitions` | UUID parent; JSON `DefectTransition`; strong parent `If-Match`. | State-dependent `defect.investigate`, `defect.close`, or `defect.reopen`; reopen also requires demo supervisor authority. | 200 `DefectView`; updated parent revision/ETag and retained status event. |
| E12 | POST | `/defects/{defect_id}/actions` | UUID parent; JSON `ActionCreate`: description, owner reference, due date, explicit status, conditional completion notes. | `action.assign`; initial In Progress/Complete additionally requires the corresponding grant and owner/supervisor authority. | 201 `ActionView`; updated parent revision/ETag and creation event. |
| E13 | GET | `/defects/{defect_id}/actions` | UUID parent; cursor and limit. | Read. | 200 `ActionPage`; ascending stable action ID. |
| E14 | GET | `/assignable-users` | Required UUID query parameter `defect_id`. | `action.assign` and valid parent context; demo eligibility policy. | 200 `OwnerPage`; active eligible demo owners, ordered by reference; null continuation. |
| E15 | POST | `/actions/{action_id}/transitions` | UUID action; JSON `ActionTransition`; strong parent-defect `If-Match`. | State-dependent `action.progress`, `action.complete`, or `action.reopen`; owner/supervisor restrictions also apply. | 200 `ActionView`; updated parent revision/ETag and retained action event. |
| E16 | GET | `/defects/{defect_id}/history` | UUID parent; cursor and limit. | Read. | 200 `DefectEventPage`; ascending aggregate revision. |
| E17 | GET | `/actions/{action_id}/history` | UUID action; cursor and limit. | Read on the parent resolved through the action foreign key. | 200 `ActionEventPage`; ascending aggregate revision, including retained completion/reopen evidence. |
| E18 | GET | `/overdue-actions` | Cursor and limit. | Read, freshly checked on each page. | 200 `OverduePage`: evaluation date, plant zone, items, nullable continuation. |
| E19 | GET | `/defects/{defect_id}/audit.pdf` | UUID parent; no pagination. | Both Read and `defect.export`, checked in the snapshot and again after rendering. | 200 `application/pdf`; complete buffered attachment named using the defect UUID. |
| E20 | POST | `/defect-types/{type_id}/retire` | UUID type; explicitly empty JSON object; strong type `If-Match`. | `type.retire`, refreshed after obtaining the type lock. | 200 `TypeView`; retired state, incremented type revision and type ETag. |

## Shared contracts and validation boundaries

### Authentication and response protection

Login verifies Argon2 credentials and issues an HS256 token with required subject, issuer, audience, issued-at, and expiry claims. Tokens do not contain permission grants. Protected requests reload active identity and persisted plant-scoped grants. A familiar display name, persona, or owner reference does not independently confer an operation grant.

The application middleware sets `Cache-Control: private, no-store` on responses. Safe failures use `application/problem+json` with `type`, `title`, `status`, `code`, and optional `field_errors`; absent field errors are omitted. Passwords and raw database exceptions are not intentionally echoed.

### Capture and lookup snapshots

Capture requires the six fields `part_number`, `defect_type_id`, `quantity_affected`, `production_line_id`, `shift_id`, and `severity`. Part numbers are trimmed, nonblank, and at most 50 characters. Quantity is a strict integer between 1 and 1,000,000. Severity is exactly Critical, Major, or Minor. Unknown input properties, including caller-supplied trusted metadata, are forbidden.

The service locks type, line, and shift in that order and copies their codes and labels into captured context. Missing or retired lookups reject capture. Later lookup changes do not rewrite historical captured labels. Duplicate submissions are not suppressed.

### Pagination and date filters

Paged collections default to 50 items and accept limits from 1 through 100. Lookup and assignable-user pages are complete bounded collections with null continuations, rather than cursor-driven collections.

Defect collection filters are `status`, `severity`, `production_line_id`, `shift_id`, `defect_type_id`, exact `part_number`, and paired `start_date`/`end_date`. They are AND-combined. Dates are inclusive plant-local calendar dates; the implementation uses independent local-midnight boundaries rather than adding 24 UTC hours across DST. Reversed, incomplete, and unsupported maximum-date ranges are rejected.

Defect cursors bind caller, plant scope, filters, calendar, and descending `created_at,id` order. Child cursors bind caller, plant scope, and the exact parent/action collection context. Child ordering is ascending as shown in the register. Every continuation request is authorized again; possession of a cursor never grants access.

Overdue cursors additionally pin the evaluation date and zone. Incomplete actions with due dates strictly before that date are overdue; due today and Complete actions are excluded. Status membership and owner display names remain live across continuation requests. These live collections are not export snapshots.

### Revisions, writes, and lifecycle gates

Defect/action transitions and type retirement require one strong quoted positive revision, such as `"7"`. Action transitions use the parent defect revision, not an independent action revision. Retirement uses the type revision. For authorized, otherwise valid commands, missing headers produce 428, malformed headers produce 400, and well-formed stale revisions produce 412. Duplicate, weak, wildcard, zero, and comma-list revisions are not accepted.

Capture, cause creation, and action creation do not evaluate `If-Match`. Successful mutations return an ETag representing the applicable updated aggregate or type revision. Defect detail reads also return the parent ETag.

Workflow writes serialize on the parent defect lock, refresh authority after waiting, and commit state, revision increments, and events together. Defect transitions allow Open to Under Investigation, Under Investigation to Closed, and Closed to Under Investigation. Entering investigation requires a saved nonblank cause. Closure requires all existing actions Complete, but zero-action closure is allowed.

Actions enter with an explicit Open, In Progress, or Complete status. Completion requires notes; reopening Complete to In Progress requires a reason and supervisor authority. Action creation on Closed returns 409 `defect_closed`. Existing-action reopening on Closed returns 503 `policy_unavailable` without implicitly reopening the defect. Workflow text is trimmed, nonblank, and bounded to 2,000 characters.

Authorization-before-existence and authorization-before-revision are service guarantees for structurally valid requests. Framework parsing can reject malformed UUIDs or request bodies before the service is called; this inventory does not promise universal 403 precedence over every malformed request.

### PDF and retirement boundaries

PDF export reads all causes, actions, action events, and status events in a dedicated read-only repeatable-read transaction. It detaches the complete snapshot, closes the transaction, renders locally, and rechecks active identity plus Read/export grants before returning bytes. It does not reuse paginated child responses or truncate evidence to a UI page.

The renderer supports A4 Latin/WinAnsi text, escapes markup, wraps and splits long rows, and repeats table headers. Unsupported glyphs, unexpected reserved photo evidence, rendering failures, and incomplete output fail safely rather than yielding partial evidence. This is not a claim of general Unicode, visual readability, or PDF accessibility acceptance.

Retirement requires an explicit grant that no seeded persona receives automatically. It shares capture's type-row lock, permits only active-to-retired change, increments revision atomically, and preserves historical capture context.

## Error interpretation

| Status | Meaning in the implemented API |
| --- | --- |
| 400 | Malformed multipart request, cursor, or revision token, depending on the operation. |
| 401 | Missing/invalid bearer authentication or invalid login credentials. |
| 403 | Inactive caller, missing explicit grant, or insufficient owner/supervisor authority. |
| 404 | Authorized lookup of a missing record. |
| 409 | Unavailable lookup, invalid lifecycle edge, failed business gate, Closed action addition, or already-retired type. |
| 412 | Well-formed but stale revision. |
| 422 | Framework/schema validation or conditional business-input rejection. |
| 428 | Required revision absent after service authorization. |
| 500 | Safe internal/export failure without partial protected output. |
| 503 | Persistence, calendar, or authority-policy unavailable. |

The shared OpenAPI Problem vocabulary is deliberately broad. Its presence on an operation does not establish that every listed error is reachable for that operation. Detailed reachability and AC-to-test mappings belong to the approval-gated Batch 2 matrices.

## Evidence and review limits

The inventory was reconciled against [main routes](../../qualitytrack/main.py), [workflow routes](../../qualitytrack/workflow_routes.py), [reporting routes](../../qualitytrack/reporting_routes.py), and [OpenAPI declarations](../../qualitytrack/openapi.py). Input/output details come from [base schemas](../../qualitytrack/schemas.py), [workflow schemas](../../qualitytrack/workflow_schemas.py), and [Problem handling](../../qualitytrack/errors.py).

Behavioral details were checked against [security](../../qualitytrack/security.py), [capture and reads](../../qualitytrack/defects.py), [workflow services](../../qualitytrack/workflow.py), [reporting services](../../qualitytrack/reporting.py), [evidence export](../../qualitytrack/evidence.py), and the [Batch C contract-drift report](../batch-c-contract-drift.md).

Batch 1 performed source inspection and static route-count verification only. It did not execute HTTP requests, PostgreSQL tests, live-response schema validation, performance tests, or release qualification. Approval is pending before Batch 2.
