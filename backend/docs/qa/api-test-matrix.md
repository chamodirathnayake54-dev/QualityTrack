# QualityTrack Backend API Test Matrix

## Baseline, scope, and evidence status

This Stage 5 Batch 2 document was prepared at starting commit `c5d6f084f29c6aae7445bd96cccef8b205041230` on `kavia/cmada08852`. Before proceeding, `git merge-base --is-ancestor e0a24dc HEAD` returned exit code 0, and the working tree was clean. This is documentation for approval, not an executed QA report. No tests were run for this batch, and no numerical coverage or release acceptance is claimed.

The matrix covers the [endpoint inventory](endpoint-inventory.md): 20 operations on 17 paths, comprising 13 GET and 7 POST operations. All paths below have prefix `/api/v1`. The [failure-mode matrix](failure-mode-matrix.md) expands cross-cutting risks. The [Batch 1 strategy](backend-test-strategy.md) remains unchanged as a historical approval-stage artifact.

Expected behavior is reconciled against current routes, schemas, services, tests, and the [settled Batch C scope](../batch-c-contract-drift.md), rather than treating every proposal in the LLD as delivered. Photos, analytics routes/stubs, rule evaluation, production policy approval, auditor acceptance, and effectiveness verification are outside this batch. Reserved photo storage does not make photo upload/export supported.

### How to read evidence and acceptance references

Every case has an expected outcome and acceptance reference. `AC-xx` refers to Stage 1 acceptance criteria, not an invented endpoint criterion. `Support DR-03` means authorization supports that domain rule but has no direct endpoint-specific AC. `Support LLD-8` means a technical API/protocol expectation from LLD Section 8, qualified by the settled scope. These support references deliberately do not claim direct AC coverage.

`Existing` identifies source-inspected pytest assertions at their actual layer; it does not mean the test passed in this invocation. `Partial` means existing coverage exercises the behavior but does not establish every listed status, schema, header, error code, or boundary. `Gap Gxx` identifies only the missing assertion or scenario in the gap register. A row may combine existing proof and a narrow gap; it is not a request to rebuild the existing test.

The following aliases expand to exact pytest node prefixes relative to `backend/`. References retain exact function names; parametrized variants are described in prose rather than inventing collection suffixes.

| Alias | Exact pytest file prefix | Evidence layer |
| --- | --- | --- |
| U | `tests/test_unit.py::` | Schema, authentication, capture/read service unit tests. |
| S | `tests/test_services.py::` | Direct handler/service contracts; not HTTP transport. |
| P | `tests/test_postgres.py::` | Real PostgreSQL and HTTP coverage, with some direct service fault injection. |
| WU | `tests/test_workflow_unit.py::` | Workflow schemas, gates, revision parsing, and child service contracts. |
| WP | `tests/test_workflow_postgres.py::` | Workflow HTTP, persistence, rollback, and locking. |
| RU | `tests/test_reporting_unit.py::` | Calendar/cursor, retirement, renderer, and OpenAPI declarations. |
| RP | `tests/test_reporting_postgres.py::` | Reporting HTTP and real-database snapshot/retirement coverage; some service injections. |

For example, `WP:test_defect_preconditions_no_mutation` means exactly `tests/test_workflow_postgres.py::test_defect_preconditions_no_mutation`. “No existing test” means no matching assertion was found in these inspected modules, not that the code necessarily fails.

## Shared schema, status, and header oracle

Every success is `application/json` with the named response model below, except E19, which is `application/pdf`. All responses must have `Cache-Control: private, no-store`. Errors use `application/problem+json` and the `Problem` schema: required `type`, `title`, integer `status` matching HTTP status, and `code`; `field_errors` is safe and omitted when absent. Errors must not echo passwords, bearer tokens, submitted evidence, SQL, or exception details. The status/code pairs below are expected assertions, not a claim that every referenced test currently checks the code.

Successful E06, E08, E09, E11, E12, and E15 return a strong quoted positive parent-defect revision as `ETag`; the JSON revision agrees with it. E20 returns the type revision. Login and other GET operations do not promise an ETag. Errors do not promise an ETag or current revision; assertions must not manufacture such a contract.

Only E11, E15, and E20 require `If-Match`. For an authorized, structurally valid request to an existing resource, absent header gives 428 `precondition_required`, malformed/duplicate/weak/wildcard/comma-list/nonpositive header gives 400 `invalid_precondition`, and a valid but stale revision gives 412 `precondition_failed`. E15 uses the parent defect revision, not a separate action token. E20 uses the type revision. E06/E09/E12 neither require nor evaluate `If-Match`; they never reject an additive write merely for a stale or malformed header.

Protected requests reload active identity and current persisted grants. Missing/invalid bearer authentication gives 401 `invalid_token`; inactive or unmapped persisted identity gives 403 `inactive_user`; missing operation grant or owner/supervisor authority gives 403 `forbidden`. Service authorization precedes existence and revision disclosure for structurally valid requests. Framework rejection of malformed UUID/body input may occur before the service: do not require universal 403 precedence over malformed requests.

Default page size is 50 and allowed limits are 1 through 100 for E07/E10/E13/E16/E17/E18. Collections return required `items` and nullable `next_cursor`. Lookup and owner lists are complete collections with null continuation, not cursor APIs. Invalid framework UUIDs, query limits, and request DTOs give 422 `validation_failed` unless a route explicitly maps validation differently, such as capture.

OpenAPI evidence is declarative: `RU:test_openapi_security_and_error_media`, `RU:test_openapi_transition_headers`, `RU:test_openapi_required_outputs_and_capture`, `RU:test_openapi_pdf_and_no_stretch_routes`, `RU:test_openapi_references_resolve`, and `P:test_openapi_batch_boundary`. These do not validate every actual response against OpenAPI. The broad documented Problem vocabulary is not evidence that every status is reachable on every route. G01 tracks the remaining live-response assertion work.

## Operation cases

### E01 — POST /auth/login

Success model is `TokenResponse` (200), with nonempty access token, bearer type, and positive `expires_in` of 3600 for the demo. No bearer token or If-Match is required; no ETag is promised.

| Case | Input and expected outcome | Acceptance reference | Exact existing evidence and remaining gap |
| --- | --- | --- | --- |
| E01-P | Valid active local credentials produce 200, a signed expiring token, and no password/hash/permission claims. | Support DR-03; LLD-8 local login. | Existing U:test_valid_login_token_contract; P:test_login_me_and_revocation. Full response/header validation is G01. |
| E01-N1 | Unknown username, wrong password, inactive account, or invalid stored hash produces generic 401 `invalid_credentials`, not user enumeration. | Support DR-03; LLD-8. | Existing U:test_login_generic_denial; P:test_inactive_login_and_existing_token_denied. P:test_unknown_wrong_password_and_validation_never_echo checks safe mixed failure responses, not every exact code. |
| E01-N2 | Missing/malformed fields or blank username produce 422 `validation_failed`, with no echo or issued token. | Support LLD-8. | Existing U:test_login_username_nonblank; partial P:test_unknown_wrong_password_and_validation_never_echo; G01 exact wire assertions. |
| E01-B | Token lifetime/required claims are enforced; expired, tampered, wrong issuer/audience/algorithm tokens cannot subsequently authenticate. | Support DR-03; LLD-8. | Existing U:test_valid_login_token_contract; U:test_token_validation; U:test_missing_claims_rejected. Unit token proof is not per-route HTTP authentication coverage; G02. |

### E02 — GET /me

Success model is `MeView` (200). It returns the caller only, sorted current operation names, plant scope, and resolved plant zone; no additional operation grant or ETag is required.

| Case | Input and expected outcome | Acceptance reference | Exact existing evidence and remaining gap |
| --- | --- | --- | --- |
| E02-P | Active caller receives current identity/grants without credentials or other users' data. | Support DR-03; LLD-8. | Existing S:test_me_route_contract; P:test_login_me_and_revocation. G01 for complete wire schema/header assertions. |
| E02-N1 | Missing bearer gives 401 `invalid_token`. | Support DR-03. | Partial P:test_missing_authentication_denied includes `/me` and asserts status; G01 code/media/schema. |
| E02-N2 | A previously issued token for a now inactive user gives 403 `inactive_user`. | Support DR-03. | Existing P:test_inactive_login_and_existing_token_denied; U:test_inactive_or_unmapped_caller_denied. |
| E02-B | Zero effective grants still permit caller-only 200; revoked grants disappear immediately, and protected reads then deny. | Support DR-03; LLD-8. | Existing S:test_me_route_contract empty/sorted-grant variants; P:test_login_me_and_revocation; U:test_principal_reloads_grants. |

### E03 — GET /production-lines

Success model is `LookupPage` (200), requiring `defect.capture`. No If-Match or ETag applies.

| Case | Input and expected outcome | Acceptance reference | Exact existing evidence and remaining gap |
| --- | --- | --- | --- |
| E03-P | Capture-authorized caller receives only active `{id,code,label}` choices ordered by code. | AC-01a (capture-context support). | Existing S:test_lookup_route_contract production-line variants; P:test_active_lookup_choices_require_capture. G01 wire schema. |
| E03-N1 | Missing bearer gives 401 `invalid_token`. | Support DR-03; AC-01e. | Partial P:test_missing_authentication_denied production-lines variant; G01 exact Problem assertions. |
| E03-N2 | Authenticated caller without capture grant gives 403 `forbidden`, not an empty success. | AC-01e; Support DR-03. | Existing S:test_lookup_route_contract denied variant; P:test_active_lookup_choices_require_capture. |
| E03-B | Empty active set gives 200 empty items/null cursor; retired choices remain excluded. | AC-01a (context support); Support LLD-8. | Existing S:test_lookup_route_contract empty/active/order variants; P:test_active_lookup_choices_require_capture. |

### E04 — GET /shifts

Success model is `LookupPage` (200), requiring `defect.capture`. No If-Match or ETag applies.

| Case | Input and expected outcome | Acceptance reference | Exact existing evidence and remaining gap |
| --- | --- | --- | --- |
| E04-P | Capture-authorized caller receives active shifts and safe ID/code/label projection in code order. | AC-01a (capture-context support). | Existing S:test_lookup_route_contract shift variants; P:test_active_lookup_choices_require_capture. G01 wire schema. |
| E04-N1 | Missing bearer gives 401 `invalid_token`. | Support DR-03; AC-01e. | Partial P:test_missing_authentication_denied shifts variant; G01 exact Problem assertions. |
| E04-N2 | Missing capture grant gives 403 `forbidden`. | AC-01e; Support DR-03. | Existing S:test_lookup_route_contract denied variant; P:test_active_lookup_choices_require_capture. |
| E04-B | No active shifts returns 200 empty items/null cursor; retired rows never become selectable. | AC-01a (context support); Support LLD-8. | Existing S:test_lookup_route_contract empty/active/order variants; P:test_active_lookup_choices_require_capture. |

### E05 — GET /defect-types

Success model is `TypePage` (200), requiring `defect.capture`; each item also has retirement and revision fields. No If-Match or response ETag is promised.

| Case | Input and expected outcome | Acceptance reference | Exact existing evidence and remaining gap |
| --- | --- | --- | --- |
| E05-P | Capture-authorized caller sees active types in code order with required revision/retired fields. | AC-01a; AC-02d. | Existing S:test_lookup_route_contract type projection/order variants; P:test_active_lookup_choices_require_capture. G01 full wire assertion. |
| E05-N1 | Missing bearer gives 401 `invalid_token`. | AC-01e; Support DR-03. | Partial P:test_missing_authentication_denied defect-types variant; G01 exact Problem assertions. |
| E05-N2 | Missing capture grant gives 403 `forbidden`. | AC-01e; Support DR-03. | Existing S:test_lookup_route_contract denied variant; P:test_active_lookup_choices_require_capture. |
| E05-B | All types retired gives empty 200/null continuation; retirement never removes old captured meaning. | AC-02d. | Existing S:test_lookup_route_contract empty/active variants; RP:test_retirement_preserves_capture provides retirement/capture evidence. |

### E06 — POST /defects

Success model is `DefectView` (201), initially Open, revision 1, `has_photo=false`, with `ETag: "1"`. Request is multipart with exactly one `capture` JSON part and no photo. Any If-Match is ignored.

| Case | Input and expected outcome | Acceptance reference | Exact existing evidence and remaining gap |
| --- | --- | --- | --- |
| E06-P | Valid six-field capture preserves selected Critical/Major/Minor, trusted actor/time, and captured lookup labels. Detail agrees with creation. | AC-01a; AC-02a; AC-02d. | Existing P:test_capture_and_read_preserve_snapshots; U:test_manual_severity_preserved. Includes ignored If-Match and ETag. G01 full response schema. |
| E06-N1 | Missing/invalid fields, quantity 0/fraction/bool/string, invalid severity, or caller-supplied trusted properties give 422 `capture_validation_failed` and no defect. | AC-01c (backend portion); AC-02c. | Existing U:test_capture_quantity_is_strict; U:test_capture_rejects_invalid_or_trusted_input; P:test_invalid_capture_no_write. G01 exact per-variant code assertions. |
| E06-N2 | Missing/retired type, line, or shift gives 409 `lookup_unavailable` with safe field feedback and no write. Denied capture gives 403 `forbidden` before state processing. | AC-02d; AC-01e. | Existing U:test_capture_missing_or_retired_lookup_has_no_write covers retired variants, not every missing lookup; P:test_retirement_wins_lock_capture_rechecks; P:test_denied_capture_precedes_state_and_input. Missing-lookup HTTP variants are G03. |
| E06-B | Trimmed part length 1..50 and strict quantity 1..1,000,000 are accepted; 51/1,000,001 are rejected. Photo gives 422 `photo_not_supported`; duplicate/extra/missing parts give 422 `invalid_parts`; bad JSON gives 422 `capture_validation_failed`; wrong media gives 400 `invalid_multipart`. | AC-01a; AC-01c; AC-02a; AC-02c; photo rejection is settled-scope support, not AC-01b/01d acceptance. | Existing U:test_capture_trims_and_accepts_boundaries proves trim/max quantity, not a 50-character positive; U:test_capture_quantity_is_strict; P:test_invalid_capture_no_write; P:test_capture_photo_duplicate_and_malformed_parts_rollback. G04 for missing accepted HTTP text/quantity boundaries; G01 for exact multipart code assertions. |

### E07 — GET /defects

Success model is `DefectPage` (200), requiring `defect.read`. Filters use AND, exact part matching, paired inclusive local dates, and descending `(created_at,id)`. No ETag applies.

| Case | Input and expected outcome | Acceptance reference | Exact existing evidence and remaining gap |
| --- | --- | --- | --- |
| E07-P | Authorized filtered live pages reconcile all matching records without duplicate equal-time IDs. | AC-01a; AC-02a; AC-02d (read support); Support LLD-8. | Existing P:test_keyset_equal_times_filters_and_caller_binding; P:test_all_collection_filters_and_dst_boundaries. G01 full page schema. |
| E07-N1 | Missing/revoked read authority gives 401 `invalid_token` or 403 `forbidden`, never empty success. | Support DR-03. | Partial P:test_missing_authentication_denied; existing P:test_login_me_and_revocation. G01 exact error envelope. |
| E07-N2 | Bad filter enum/date pair/inverted range gives 422 `invalid_filters`; invalid framework UUID/limit gives 422 `validation_failed`; tampered or changed caller/filter cursor gives 400 `invalid_cursor`. | Support LLD-8. | Existing U:test_filter_validation; U:test_cursor_bound_context; partial P:test_invalid_collection_queries; P:test_keyset_equal_times_filters_and_caller_binding. G01 exact status/code discrimination where tests accept broad outcomes. |
| E07-B | Default 50, limits 1/100 valid and 0/101 invalid; independent local midnight boundaries include the final local day over DST, not a fixed 24-hour interval. | Support LLD-8; DR-11 calendar convention. | Existing P:test_all_collection_filters_and_dst_boundaries; P:test_keyset_equal_times_filters_and_caller_binding; P:test_invalid_collection_queries. G05 for explicit accepted/default HTTP page-size assertions. |

### E08 — GET /defects/{defect_id}

Success model is `DefectView` (200), requiring `defect.read` only; ETag matches current parent revision.

| Case | Input and expected outcome | Acceptance reference | Exact existing evidence and remaining gap |
| --- | --- | --- | --- |
| E08-P | Authorized detail returns exactly the requested record and immutable captured labels, even after lookup changes. | AC-01a; AC-02a; AC-02d. | Existing S:test_detail_service_contract found/id-bound/no-capture-required variants; P:test_capture_and_read_preserve_snapshots. G01 full schema/ETag consistency. |
| E08-N1 | Caller lacking read receives 403 `forbidden` for known and unknown valid IDs. | Support DR-03. | Existing P:test_denied_read_precedes_record_existence; U:test_record_denies_before_existence_lookup. |
| E08-N2 | Authorized absent UUID gives 404 `not_found`, without protected detail. | Support LLD-8; DR-03. | Existing P:test_missing_record_safe_404; U:test_record_missing_is_safe; S:test_detail_service_contract missing variant. |
| E08-B | Malformed UUID gives 422 `validation_failed`; historical labels remain stable after rename/retirement. | AC-02d; Support LLD-8. | Existing U:test_projection_uses_captured_labels; RP:test_retirement_preserves_capture. G03 for explicit malformed-detail-UUID HTTP assertion. |

### E09 — POST /defects/{defect_id}/causes

Success model is `CauseView` (201), requiring `cause.create`. It returns trusted actor/time and the incremented parent revision/ETag; If-Match is ignored.

| Case | Input and expected outcome | Acceptance reference | Exact existing evidence and remaining gap |
| --- | --- | --- | --- |
| E09-P | Saved trimmed preliminary text creates a separate cause and advances parent revision; stale/malformed additive headers do not block it. | AC-03b; AC-03d. | Existing WU:test_add_cause_contract; WP:test_cause_reads_and_additive_headers. |
| E09-N1 | Blank/oversized/null/non-string text gives 422 `validation_failed` and no cause/revision change. | AC-03a; AC-03d. | Existing WU:test_cause_input_rejections; G04 for full HTTP boundary/no-mutation bridge; G01 exact Problem/schema. |
| E09-N2 | Missing grant gives 403 `forbidden` before parent lookup; authorized absent parent gives 404 `not_found`. | Support DR-03; AC-03f (denied unchanged). | Existing WP:test_denials_precede_existence_and_preconditions for denial; G03 authorized missing-parent HTTP assertion. |
| E09-B | Trimmed length 1 and 2,000 accepted, 2,001 rejected; four concurrent additions preserve all rows and revisions rather than last-writer-wins. | AC-03b; AC-03d; Support LLD-8. | Existing WU:test_add_cause_contract; WU:test_cause_input_rejections; WP:test_concurrent_cause_writes_keep_all_revisions. G04 only missing HTTP text-boundary assertions. |

### E10 — GET /defects/{defect_id}/causes

Success model is `CausePage` (200), requiring read, ordered by `(recorded_at,id)`. No ETag applies.

| Case | Input and expected outcome | Acceptance reference | Exact existing evidence and remaining gap |
| --- | --- | --- | --- |
| E10-P | Authorized empty/full cause pages retain saved text and attribution in stable order. | AC-03b; AC-03d; AC-03f (evidence support). | Existing WP:test_cause_reads_and_additive_headers; WU:test_child_reads_contract causes variants. |
| E10-N1 | Denied/revoked read gives 403 `forbidden` on first and continuation pages, for known/unknown parents. | Support DR-03. | Existing WP:test_denials_precede_existence_and_preconditions; WP:test_live_child_keysets causes variants. G02 missing bearer HTTP coverage. |
| E10-N2 | Cursor tampering or caller/parent/kind replay gives 400 `invalid_cursor`; authorized absent parent gives 404 `not_found`. | Support LLD-8; DR-03. | Existing WU:test_child_cursor_context; WP:test_live_child_keysets. G03 absent-parent HTTP proof; G10 malformed signed payload shape. |
| E10-B | Default 50, 1/100 accepted, 0/101 rejected with 422 `validation_failed`; page size 1 reconciles all causes. | AC-03b; Support LLD-8. | Existing WP:test_live_child_keysets; WU:test_child_reads_contract uses a service limit, not HTTP boundary validation. G05 remaining limits/UUID assertions. |

### E11 — POST /defects/{defect_id}/transitions

Success model is `DefectView` (200), with updated parent ETag. Target-specific explicit grant and current strong parent If-Match are required; reopening additionally needs demo supervisor authority.

| Case | Input and expected outcome | Acceptance reference | Exact existing evidence and remaining gap |
| --- | --- | --- | --- |
| E11-P | Open enters Under Investigation only with saved nonblank cause; eligible Under Investigation closes with zero actions or all Complete; supervisor can reopen Closed. Each successful edge records old/new/actor/time/revision. | AC-03a; AC-03b; AC-03d; AC-03f; zero-action closure is settled working scope. | Existing WU:test_defect_transition_gates; WP:test_defect_lifecycle_zero_action_close_reopen; WP:test_action_cycles_closure_and_closed_reopen_policy. |
| E11-N1 | No saved cause gives 409 `cause_required`; incomplete actions give 409 `actions_incomplete`; illegal/same-state edge gives 409 `invalid_transition`, without mutation. | AC-03a; AC-03f; Support DR-08. | Existing WU:test_defect_transition_gates; WP:test_defect_preconditions_no_mutation; WP:test_action_cycles_closure_and_closed_reopen_policy. |
| E11-N2 | Authorized missing/malformed/stale If-Match gives 428/400/412 and the shared precondition codes. Missing grant/authority gives 403 `forbidden` before revision disclosure. | AC-03f; Support DR-03; LLD-8. | Existing WP:test_defect_preconditions_no_mutation; WP:test_action_preconditions_and_duplicate_headers; WU:test_defect_reopen_authority_precedes_preconditions; WP:test_denials_precede_existence_and_preconditions. |
| E11-B | Strong current token accepts; weak, wildcard, list, zero, leading zero, whitespace, negative, or duplicate tokens reject. Additive writes invalidate reviewed revision; refreshed closure rechecks current actions. | AC-03f; Support LLD-8. | Existing WU:test_revision_contract; WP:test_parent_lock_serializes_competing_commands; WP:test_closure_races_existing_action_reopen. G03 authorized absent UUID and G02 bearer bridge only; existing concurrency proof is not a gap. |

### E12 — POST /defects/{defect_id}/actions

Success model is `ActionView` (201), with parent ETag. Assignment needs `action.assign`; initial In Progress/Complete additionally needs the relevant operation grant and owner/supervisor authority. If-Match is ignored.

| Case | Input and expected outcome | Acceptance reference | Exact existing evidence and remaining gap |
| --- | --- | --- | --- |
| E12-P | Explicit Open/In Progress/Complete entry associates work with the parent and creates attribution/event; direct Complete requires notes and completion authority, not effectiveness verification. | AC-04a; AC-04b; AC-04c; AC-04d; AC-04f. | Existing WU:test_action_entry_contract; WP:test_action_cycles_closure_and_closed_reopen_policy includes direct Complete and ignored header. G01 full wire schema. |
| E12-N1 | Closed parent returns 409 `defect_closed` for all three entry states before owner/completion business gates; no action/event/revision or implicit reopening. | Support DR-08; settled Closed-entry policy; AC-03f (unchanged parent). | Existing WP:test_closed_action_creation_precedes_business_gates; WU:test_action_entry_contract. |
| E12-N2 | Ineligible/inactive owner gives 422 `invalid_owner`; missing/inappropriate Complete notes gives 422 `completion_notes_required`; missing assignment/entry authority gives 403 `forbidden`. | AC-04a; AC-04d; Support DR-03. | Existing WU:test_action_entry_contract; WP:test_assignable_and_action_validation; WP:test_denials_precede_existence_and_preconditions. G01 exact error envelope; G03 authorized missing parent. |
| E12-B | Description/notes trim to 1..2,000 characters; 2,001/blank reject; due date is a date without a future-only rule. Multiple actions persist; no default initial state is inferred. | AC-04a; AC-04b; AC-04c; AC-04d. | Existing WP:test_assignable_and_action_validation covers several rejection/date variants; WU:test_action_entry_contract covers initial states; WP:test_live_child_keysets covers multiple actions. G04 only unasserted accepted/conditional text boundaries. |

### E13 — GET /defects/{defect_id}/actions

Success model is `ActionPage` (200), requiring read, ordered by stable action ID. No ETag applies.

| Case | Input and expected outcome | Acceptance reference | Exact existing evidence and remaining gap |
| --- | --- | --- | --- |
| E13-P | Authorized pages return all associated actions with explicit status/owner/date; empty result is 200, not denied-as-empty. | AC-04a; AC-04b; AC-04c; AC-04f. | Existing WU:test_child_reads_contract actions variants; WP:test_live_child_keysets. |
| E13-N1 | Missing/revoked read gives 403 `forbidden`, including continuation and unknown valid parent IDs. | Support DR-03. | Existing WP:test_denials_precede_existence_and_preconditions; WP:test_live_child_keysets. G02 bearer bridge. |
| E13-N2 | Wrong parent/kind/caller or tampered cursor gives 400 `invalid_cursor`; authorized missing parent gives 404 `not_found`. | Support LLD-8; DR-03. | Existing WU:test_child_cursor_context; WP:test_live_child_keysets; G03 authorized missing parent; G10 signed cursor payload validation. |
| E13-B | Size 1 reconciles IDs without duplication; default 50 and 1/100 accepted, 0/101 rejected with 422 `validation_failed`. | AC-04b; Support LLD-8. | Existing WP:test_live_child_keysets; WU:test_child_reads_contract. G05 remaining accepted/default/invalid HTTP limits and UUID assertions. |

### E14 — GET /assignable-users?defect_id={uuid}

Success model is `OwnerPage` (200), requiring `action.assign`, valid parent context, and demo eligibility policy. Items are active eligible engineer/supervisor references/names in reference order, with null continuation. No ETag applies.

| Case | Input and expected outcome | Acceptance reference | Exact existing evidence and remaining gap |
| --- | --- | --- | --- |
| E14-P | Assignment-authorized caller sees eligible active owners only, not arbitrary active accounts. | AC-04a; Support DR-03. | Existing WU:test_assignable_contract; WP:test_assignable_and_action_validation. |
| E14-N1 | Missing assignment grant gives 403 `forbidden` before parent existence disclosure. | Support DR-03. | Existing WP:test_denials_precede_existence_and_preconditions; WU:test_assignable_contract denied variant. G02 bearer bridge. |
| E14-N2 | Missing/malformed required defect_id gives 422 `validation_failed`; authorized absent parent gives 404 `not_found`. | AC-04a (context support); Support LLD-8. | No matching HTTP assertion found: G03/G05. Existing denial tests with unknown parents do not prove authorized 404. |
| E14-B | No eligible users gives empty 200/null cursor; deactivated owner disappears; absent non-demo eligibility policy gives 503 `policy_unavailable`, not guessed eligibility. | AC-04a; Support DR-03; LLD-8. | Existing WU:test_assignable_contract empty/active/fixture variants; WP:test_assignable_and_action_validation deactivation; G09 non-demo HTTP bridge. |

### E15 — POST /actions/{action_id}/transitions

Success model is `ActionView` (200), with updated parent-defect ETag. Operation grant and owner/supervisor policy apply; a current strong parent If-Match is required.

| Case | Input and expected outcome | Acceptance reference | Exact existing evidence and remaining gap |
| --- | --- | --- | --- |
| E15-P | Open→In Progress, Open/In Progress→Complete, and supervisor Complete→In Progress retain every cycle's notes/reason/actor/time. Complete never means effectiveness verified. | AC-04c; AC-04d; AC-04e (history portion); AC-04f. | Existing WU:test_action_transition_contract; WP:test_action_cycles_closure_and_closed_reopen_policy. G06 only reopened overdue recalculation bridge. |
| E15-N1 | Missing/inappropriate notes gives 422 `completion_notes_required`; missing reopening reason gives 422 `reopening_reason_required`; illegal edge gives 409 `invalid_transition`. No partial event/state/revision. | AC-04c; AC-04d; AC-04e. | Existing WU:test_action_transition_contract; WP:test_action_cycles_closure_and_closed_reopen_policy. G04 missing HTTP reason/notes boundary variants. |
| E15-N2 | Missing/malformed/duplicate/stale If-Match gives 428/400/412 shared codes; owner without explicit grant or non-supervisor reopen gives 403 `forbidden`. | AC-04d; AC-04e; Support DR-03; LLD-8. | Existing WP:test_action_preconditions_and_duplicate_headers; WP:test_owner_needs_explicit_grant; WU:test_action_transition_contract; WP:test_denials_precede_existence_and_preconditions. |
| E15-B | Closed-parent existing-action reopen gives 503 `policy_unavailable`, unchanged; closure/reopen race serializes. Notes/reason boundaries are trimmed 1..2,000, rejecting 2,001/blank. | AC-04e (safe history preservation); Support settled policy; LLD-8. | Existing WP:test_closure_races_existing_action_reopen; WP:test_action_cycles_closure_and_closed_reopen_policy. G04 missing text boundaries; G03 authorized absent action; G02 bearer bridge. |

### E16 — GET /defects/{defect_id}/history

Success model is `DefectEventPage` (200), requiring read, ascending aggregate revision with old/new/actor/time. No ETag applies.

| Case | Input and expected outcome | Acceptance reference | Exact existing evidence and remaining gap |
| --- | --- | --- | --- |
| E16-P | Successful transitions appear in causal revision order, retaining closure/reopen history and attribution; no initial invented transition is needed. | AC-03f. | Existing WP:test_defect_lifecycle_zero_action_close_reopen; WU:test_child_reads_contract history variants; WP:test_live_child_keysets. |
| E16-N1 | Missing/revoked read gives 403 `forbidden`, not history leakage or empty success. | AC-03f (protected history); Support DR-03. | Existing WP:test_denials_precede_existence_and_preconditions; WP:test_live_child_keysets. G02 bearer bridge. |
| E16-N2 | Tampered/wrong context cursor gives 400 `invalid_cursor`; authorized absent parent gives 404 `not_found`. | Support LLD-8; DR-03. | Existing WU:test_child_cursor_context; WP:test_live_child_keysets. G03 absent-parent HTTP; G10 signed malformed shape. |
| E16-B | Revision gaps are valid because additive writes also advance parent; size-1 paging reconciles events. Default 50 and 1..100 limits apply, outside range 422 `validation_failed`. | AC-03f; Support LLD-8. | Existing WP:test_defect_lifecycle_zero_action_close_reopen; WP:test_live_child_keysets. G05 remaining default/edge/UUID HTTP assertions. |

### E17 — GET /actions/{action_id}/history

Success model is `ActionEventPage` (200), requiring parent read through the action FK. No ETag applies.

| Case | Input and expected outcome | Acceptance reference | Exact existing evidence and remaining gap |
| --- | --- | --- | --- |
| E17-P | Creation has null old status; completion/reopen cycles preserve notes, reasons, actor/time, parent identity, and aggregate ordering. | AC-04d; AC-04e (retention); AC-04f. | Existing WU:test_child_reads_contract action-history variants; WP:test_action_cycles_closure_and_closed_reopen_policy; WP:test_live_child_keysets. |
| E17-N1 | Missing/revoked read gives 403 `forbidden` for known/unknown valid action IDs and continuations. | Support DR-03. | Existing WP:test_denials_precede_existence_and_preconditions; WP:test_live_child_keysets. G02 bearer bridge. |
| E17-N2 | Caller/action/kind replay or tampering gives 400 `invalid_cursor`; authorized absent action gives 404 `not_found`. | Support LLD-8; DR-03. | Existing WU:test_child_cursor_context; WP:test_live_child_keysets. G03 authorized missing action; G10 malformed signed shape. |
| E17-B | Multiple cycles remain distinct even where timestamps tie; causal revision, not clock/UUID, orders them. Size-1 continuation reconciles; default50/1..100 and 422 invalid limit apply. | AC-04d; AC-04e; Support LLD-8. | Existing WP:test_action_cycles_closure_and_closed_reopen_policy; WP:test_live_child_keysets establishes revision retention/paging, not every tied-clock fixture. G05 limit/UUID assertions; no standalone timestamp-order rebuild proposed. |

### E18 — GET /overdue-actions

Success model is `OverduePage` (200), requiring read, with `evaluated_on`, `plant_zone`, items, and nullable cursor. Incomplete actions satisfy `due_date < evaluated_on`; days overdue uses calendar-date subtraction. No ETag applies.

| Case | Input and expected outcome | Acceptance reference | Exact existing evidence and remaining gap |
| --- | --- | --- | --- |
| E18-P | Past-due incomplete work includes current owner name, correct days, and fixed evaluation date/zone; empty authorized result is 200. | AC-05a; AC-05d. | Existing RP:test_overdue_pinned_date_and_owner (service with real DB); RP:test_overdue_revocation_and_empty (HTTP); RU:test_calendar_dst_boundaries. |
| E18-N1 | Read revocation denies continuation with 403 `forbidden`; missing bearer gives 401 `invalid_token`. | Support DR-03. | Existing RP:test_overdue_revocation_and_empty; G02 missing bearer HTTP. G01 exact code/schema/header assertions. |
| E18-N2 | Tampered/wrong-caller/zone/kind/shape cursor gives 400 `invalid_cursor`; invalid framework limit gives 422 `validation_failed`; unavailable runtime calendar gives 503 `calendar_unavailable`. | AC-05d; Support LLD-8. | Existing RU:test_overdue_cursor_rejects_context; RU:test_calendar_invalid_and_naive. G05 HTTP limits; G09 HTTP calendar failure. A naive injected clock is a unit misuse check, not a public request expected to return 503. |
| E18-B | Due today and Complete excluded, yesterday one day late; cursor pins date across midnight/DST while status/name remain live. Future-due excluded; reopened overdue work reappears. | AC-05b; AC-05c; AC-05d; AC-04e (recalculation). | Existing RP:test_overdue_pinned_date_and_owner; RP:test_overdue_status_is_live; RU:test_calendar_dst_boundaries. G06 explicit future-due and reopen-to-overdue HTTP bridge; do not duplicate pinned-date tests. |

### E19 — GET /defects/{defect_id}/audit.pdf

Success is 200 `application/pdf`, with `Content-Disposition: attachment; filename="defect-{uuid}.pdf"` and private/no-store. The output is a complete buffered PDF, not a JSON view or UI page. Both current `defect.read` and `defect.export` are required initially and after rendering; no ETag or If-Match applies.

| Case | Input and expected outcome | Acceptance reference | Exact existing evidence and remaining gap |
| --- | --- | --- | --- |
| E19-P | One read-only repeatable-read snapshot includes full record, all causes/actions/action events/status history and export context, detached before rendering. Output has PDF signature/EOF, every required section/count, and no invented effectiveness claim. | AC-08a (photo-free subset); AC-03f; AC-04d; AC-04e (history); AC-04f. | Existing RP:test_pdf_complete_evidence (55 causes, 2 actions, 2 action events, 3 status events); RP:test_render_off_transaction; RU:test_pdf_required_sections_and_counts; RU:test_pdf_immutable_snapshot. |
| E19-N1 | Either read or export missing gives 403 `forbidden` for known/unknown IDs; post-render revoked/inactive caller discards bytes. Authorized absent record gives 404 `not_found`. | AC-08d; Support DR-03. | Existing RP:test_export_requires_both_grants; RP:test_export_final_revocation; RP:test_export_final_inactive; RU:test_export_failure_discards_bytes. Final-check tests are service-level; G08 HTTP bridge, G03 authorized 404, G02 bearer. |
| E19-N2 | Render exception, incomplete bytes, or unsupported text fails with 500 `export_failed`, a safe Problem and no PDF prefix/attachment success. Reserved photo snapshot fails 500 `unsupported_evidence`. | AC-08a; AC-08c (no partial output); AC-08d; settled photo-free scope. | Existing RP:test_pdf_render_failure_safe_http; RU:test_export_failure_discards_bytes; RU:test_pdf_latin_text_and_unsupported_glyph (renderer raises). G07 reserved-photo HTTP path; G08 partial-output HTTP bridge. |
| E19-B | Long/oversized rows, repeated headers, escaped markup, A4 and Latin/WinAnsi text remain complete; concurrent writes do not mix snapshot sections. Exporting one of two records must never include the other's evidence. | AC-08a; AC-08b; AC-08c (photo-free subset); AC-03f. | Existing RU:test_pdf_empty_sections_a4_and_complete; RU:test_pdf_long_text_repeated_headers_and_escape; RU:test_pdf_single_oversized_row; RP:test_snapshot_concurrent_write. G07 explicit two-record isolation. These structural tests do not establish visual/accessibility or arbitrary-Unicode acceptance. |

### E20 — POST /defect-types/{type_id}/retire

Success model is `TypeView` (200), requiring explicit `type.retire`, empty JSON `{}`, and strong current type If-Match. ETag and JSON revision reflect the incremented type revision; seeded personas do not gain this grant implicitly.

| Case | Input and expected outcome | Acceptance reference | Exact existing evidence and remaining gap |
| --- | --- | --- | --- |
| E20-P | Authorized active type retires atomically, revision increments, ETag agrees, and historical capture remains unchanged while new capture is blocked. | AC-02d. | Existing RP:test_retirement_http; RP:test_retirement_preserves_capture; RU:test_retirement_preconditions. |
| E20-N1 | Missing grant gives 403 `forbidden` before type lookup; authorized absent type gives 404 `not_found`. | Support DR-03; AC-02d (governance support). | Existing RU:test_retirement_denial_before_query; RP:test_retirement_http denial. G03 authorized 404; G02 bearer bridge. |
| E20-N2 | Absent/malformed/duplicate/stale header gives 428/400/412 shared codes. Current revision of already-retired type gives 409 `invalid_transition`. Nonempty body gives 422 `validation_failed`. | AC-02d; Support LLD-8. | Existing RP:test_retirement_http; RP:test_retirement_preserves_capture; RU:test_retirement_preconditions. G01 complete per-variant wire validation. |
| E20-B | Capture and retirement share type lock and refresh authority; retirement winner blocks capture, capture winner preserves snapshot, waiting revoked caller denies. Post-flush failure rolls back flag/revision. | AC-02d; Support DR-03; LLD-8. | Existing RP:test_retirement_capture_lock; RP:test_retirement_rollback; P:test_capture_wins_lock_retirement_waits_and_snapshot_survives. G09 HTTP dependency-error bridge only; do not rebuild locking/rollback coverage. |

## Genuine gap register

These are proposed additions or assertion extensions only, not new implemented tests. Reuse the named existing fixtures/tests wherever possible. An assertion gap must not be reported as absence of the underlying behavior.

| Gap | Planned scope and expected evidence | Acceptance reference |
| --- | --- | --- |
| G01 | Extend live HTTP assertions across E01–E20 for exact success/Problem schemas, exact status/code pairs, private/no-store, media, no sensitive echo, expected ETag/body-revision agreement, and no success PDF headers/body on export errors. Reuse existing happy/error tests; OpenAPI declaration/reference tests already exist. | All applicable ACs in operation rows; technical remainder Support LLD-8/DR-03. |
| G02 | Add missing-bearer HTTP checks on E08–E20 and token-invalid variants representative of shared protection. Existing missing-auth parametrization covers E02–E05/E07; JWT unit tests already cover signature/claim failures. | AC-01e; AC-03f; AC-08d where relevant; remainder Support DR-03. |
| G03 | Add authorized missing-resource HTTP checks for workflow parent/action operations, owner lookup, PDF, and retirement; explicit malformed detail UUID and missing capture lookup variants. Preserve existing denied-before-existence assertions rather than replacing them. | AC-02d; AC-03f; AC-04a; AC-08d where relevant; remainder Support LLD-8/DR-03. |
| G04 | Extend boundary assertions only where absent: accepted 50-character capture part and quantity 1 at HTTP; HTTP cause length 1/2,000/2,001; action description/conditional notes/reason accepted limits and missing blank/oversized variants. Existing quantity strictness, maximum quantity, cause unit limits, and several action rejection tests remain evidence. | AC-01a/01c; AC-03b/03d; AC-04a/04d/04e; technical bounds Support settled scope. |
| G05 | Assert default50, accepted1/100, rejected0/101 and invalid UUID at HTTP where not already asserted, especially child/history/overdue pages; owner query requires valid defect_id. Existing size-1 keysets and service pagination/order tests are not gaps. | AC-03f; AC-04b; AC-05a (read support); remainder Support LLD-8. |
| G06 | Add explicit future-due exclusion and complete→supervisor-reopen→overdue HTTP reconciliation with deterministic date/owner/days. Do not rebuild existing due-today, Complete exclusion, DST/midnight pinning, live completion, or cycle-history tests. | AC-05c; AC-04e; AC-05a/05b/05d. |
| G07 | Add two-record PDF isolation reconciliation and fail-safe export of a fixture containing reserved photo evidence (500 unsupported_evidence, no PDF). Photo handling itself remains excluded. | AC-08b; AC-08a/08c/08d photo-free scope qualification. |
| G08 | Bridge existing service proof for post-render revocation/inactive principal and partial/incomplete renderer bytes through HTTP, asserting safe Problem/no success output. The renderer-exception HTTP case already exists. | AC-08d; AC-08a/08c. |
| G09 | Inject persistence failures at principal load, command transaction, snapshot load, and final authorization through HTTP: 503 persistence_unavailable with safe Problem and no partial mutation/output. Bridge runtime calendar503 and non-demo policy503 where only service/schema evidence exists. Generic non-SQLAlchemy unexpected failures expect 500 internal_failure, not an invented 503. | AC-01c; AC-03f; AC-04d/04e; AC-05d; AC-08a/08d; remainder Support LLD-8. |
| G10 | Extend child cursor tests with correctly signed malformed payload/key shapes and invalid typed positions; require controlled 400 invalid_cursor without data leakage. Existing signature/caller/parent/kind replay coverage must not be duplicated. | Support DR-03; LLD-8. |

## Acceptance and approval limits

Stage 1 AC-01c includes UI retained-input behavior, which backend rejection/rollback tests cannot establish. AC-03c/03e concern prompts and are outside backend API acceptance. AC-01b/01d photos and AC-02b conditional automatic rules are not delivered by this scope; AC-06/07 analytics are excluded. AC-08a/08c are only evidenced for the settled photo-free Latin-text subset. AC-04e history retention already has coverage, but its overdue recalculation bridge remains G06. No API-only claim establishes a complete frontend journey, production authority policy, visual readability, accessibility, performance budget, or rollout approval.

Review should approve or adjust the documented expectations and genuine gaps before any later test work. This batch stops at documentation; committing and pushing require subsequent approval.

## Source references

The implementation references are [main routes](../../qualitytrack/main.py), [workflow routes](../../qualitytrack/workflow_routes.py), [reporting routes](../../qualitytrack/reporting_routes.py), [base schemas](../../qualitytrack/schemas.py), [workflow schemas](../../qualitytrack/workflow_schemas.py), [security](../../qualitytrack/security.py), [capture/read services](../../qualitytrack/defects.py), [workflow services](../../qualitytrack/workflow.py), [reporting](../../qualitytrack/reporting.py), [evidence export](../../qualitytrack/evidence.py), [Problems](../../qualitytrack/errors.py), [OpenAPI](../../qualitytrack/openapi.py), [models](../../qualitytrack/models.py), and [configuration](../../qualitytrack/config.py).

Evidence modules are [unit](../../tests/test_unit.py), [service](../../tests/test_services.py), [PostgreSQL](../../tests/test_postgres.py), [workflow unit](../../tests/test_workflow_unit.py), [workflow PostgreSQL](../../tests/test_workflow_postgres.py), [reporting unit](../../tests/test_reporting_unit.py), and [reporting PostgreSQL](../../tests/test_reporting_postgres.py).

Acceptance references come from the workspace [Stage 1 requirements](../../../../kavia-docs/CodeWiki/Specs/FeatureSpecs/qualitytrack-stage-1-requirements.md), [Stage 2 backlog](../../../../kavia-docs/CodeWiki/Specs/FeatureSpecs/qualitytrack-stage-2-backlog.md), and [LLD Section 8](../../../../kavia-docs/CodeWiki/Specs/DetailedDesigns/qualitytrack-topic-06-lld.md), qualified by the repository Batch C drift report. The workspace CodeWiki links resolve alongside the QualityTrack checkout; that external documentation directory is not part of this Git repository.
