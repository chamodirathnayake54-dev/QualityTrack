# Batch C contract drift report

## Baseline and precedence

This compares the implemented API to QualityTrack LLD v0.3, especially sections
7–10, 12, 15 and 16.3, narrowed by the original DEV-06 rebuild instructions and
settled decisions. The latest instruction requires acceptance **before** any
commit/push. No design document, migration, seed grant or dependency pin was
changed in Batch C.

Evidence: [entry point](../qualitytrack/main.py),
[OpenAPI declarations](../qualitytrack/openapi.py),
[reporting services](../qualitytrack/reporting.py),
[evidence service](../qualitytrack/evidence.py),
[HTTP routes](../qualitytrack/reporting_routes.py),
[unit tests](../tests/test_reporting_unit.py), and
[PostgreSQL tests](../tests/test_reporting_postgres.py).
See [validation](batch-c-validation.md) for executed results.

## Route register reconciliation

The API has **20 operations on 17 paths**, including the three Batch C additions.
The implemented LLD register consists of login/me; production lines/shifts/type
choices; capture/defect collection/detail; cause create/read; defect history and
transitions; action create/read/transitions/history; assignable users; and the
three additions below.

| Batch C contract | Implementation | Drift |
| --- | --- | --- |
| GET `/api/v1/overdue-actions` | `evaluated_on`, `plant_zone`, `items`, nullable `next_cursor`; each item has action/defect IDs, owner name, due date, status, positive days overdue | None against settled scope |
| GET `/api/v1/defects/{defect_id}/audit.pdf` | Complete `application/pdf`; generated UUID filename; private/no-store | Deliberately photo-free per settled decision |
| POST `/api/v1/defect-types/{type_id}/retire` | Empty JSON object; explicit retirement grant; type-row lock; strong type revision; TypeView and new ETag | None against settled scope |

No generic update/delete, grant administration, self-registration, rule,
notification, remote asset, export job or public download endpoint was added.

## Behavioral reconciliation

| LLD requirement | Implemented evidence / result |
| --- | --- |
| Plant-calendar overdue; due today excluded; Complete excluded | Aware UTC clock converted to the configured IANA zone once; strict due-date comparison; date subtraction, never elapsed hours |
| Signed date-pinned overdue continuation | HMAC-derived HS256 key; caller, plant, route version, calendar, order, evaluation date and last `(due_date,id)` bound; integrity/context checked every page |
| Live continuation membership and authorization | Current statuses and owner display names queried; current read grants reloaded; no frozen totals or cursor-derived authority |
| Explicit read plus export authority | Both checked before record disclosure, in the consistent snapshot, and again in a new transaction after rendering; inactive caller fails closed |
| Consistent complete export | First snapshot SQL sets read-only repeatable-read; all causes/actions/events/history loaded without page limits; immutable detached tuples; transaction closes before rendering |
| Complete buffered output only | All required sections and expected row counts checked; ReportLab completes into a closed BytesIO before response; renderer exceptions/partial output yield safe Problem |
| PDF contents | A4 title/context, captured lookup labels/codes, all causes/actions/action events/status events, actor references, revisions, completion/reopening evidence, export timestamp and labelled local timestamps |
| Pagination and safe text | Repeated table headers, wrapped text and split oversized rows; text escaped before Paragraph parsing; no remote fetching or image processing |
| Retirement/capture coordination | Same type-row lock as capture, fresh grant check after waiting, active-to-retired only, atomic revision increment; historical snapshots unchanged |
| Revision outcomes | Authorized missing token 428; malformed/weak/multiple/wildcard 400; stale 412; current same-state/gate failure 409; no failed mutation |
| Transition-only If-Match | Required for defect/action transitions and retirement only; action tokens are parent revisions; additive capture/cause/action commands continue ignoring it |
| OpenAPI surface | Bearer security, required response fields including serialized defaults, typed UUID/date/enum filters, Capture JSON schema linkage, binary PDF, ETag/Cache-Control and Problem media declarations |

The OpenAPI If-Match parameter is required in the wire contract. Its Python
binding remains optional intentionally: authorization happens before the service
returns 428 for a missing token, rather than framework validation returning 422.
Conditional action notes/reopening requirements remain described in field/route
documentation and enforced against persisted state; they are not unconditional
schema requirements.

Shared Problem responses are a documented safe error vocabulary, not a claim
that every operation can exercise every state/gate failure. Runtime Problems use
`application/problem+json`, not the framework's default validation-error envelope.

## Intentional differences from the un-narrowed LLD

| Difference | Authority / treatment |
| --- | --- |
| No photo upload/serving or PDF photo embedding | Explicit settled exclusion. Capture rejects photo parts with no writes; reserved storage remains in the unchanged ERD |
| No Pareto/trend stubs or future success DTOs | Explicit stretch exclusion; no 200 analytics, fabricated no-data output or 501 stub routes |
| No auditor acceptance stories | Explicit stretch exclusion; original three seeded users/exact grants remain unchanged, without claiming auditor-story acceptance |
| Bounded capture and workflow text | Settled demo limits: part 50; quantity 1–1,000,000 strict whole units; trimmed nonblank workflow text 2,000 |
| No duplicate suppression | Explicit settled decision, not an idempotency guarantee |
| Zero-action closure, Closed addition rejection and Closed existing-action reopen | Settled decisions preserve Batch B behavior: permitted closure, 409 addition rejection, 503 existing-action reopening respectively |
| PDF font repertoire | Settled Latin-text scope implemented with Helvetica/WinAnsi (Windows-1252). Unsupported glyphs fail rather than silently substituting evidence |
| Unexpected reserved photo row | Export fails safely with no PDF rather than silently omitting unsupported evidence; no photo feature is enabled |

No unapproved endpoint, lifecycle, grant, persistence-schema or precondition
drift was identified against the **settled Batch A–C scope**. This is not a claim
that the complete un-narrowed LLD, Next analytics or stretch stories are delivered.

## Limits and residual risks

- Final authorization narrows but cannot eliminate the race after the final
  check and delivery; cancellation/revocation after delivery begins remains a
  production identity/session policy question.
- Complete in-memory snapshots/PDFs are not truncated to satisfy arbitrary
  budgets. Large-record resource bounds, cancellation policy and performance
  measurement remain operational review items; no SLO is claimed.
- PDF checks reconcile rendered text streams, sections, pagination, repeated
  headers and A4 geometry. No visual/manual readability acceptance or PDF
  accessibility certification was performed.
- Latin/WinAnsi output is not a general Unicode/font-coverage commitment.
- Single-plant explicit grants and demo owner/supervisor fixture bindings are
  unchanged; no production identity, narrower record entitlement, grant-change
  auditing or production provisioning policy is invented.
- Existing immutable-history privileges are unchanged; privileged SQL is not
  a tamper-proof ledger.
- No demo persona receives `type.retire` automatically. Tests grant it explicitly
  in disposable fixtures; real configuration authority remains operator-owned.

Return to the [backend guide](../README.md).
