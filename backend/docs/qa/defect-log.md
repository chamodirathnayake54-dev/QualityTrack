# Backend QA defect log

## Baseline and scope

- Base commit for investigation, fix, focused regression, and HTTP validation:
  `b26c9888bd210da72c9767cf7f7d46cdd98bfd99`.
- `git merge-base --is-ancestor e0a24dc HEAD` passed before work and validation.
- Changes are uncommitted; no push was performed.
- Photos and analytics are excluded.
- Supporting execution evidence: [Batch 3 validation](batch3-validation.md).

## QA-B3-001 — malformed signed UUID cursor position escapes as HTTP 500

**Classification:** repository implementation defect, at cursor payload conversion.
**Status:** fixed in the working tree; active focused regressions passed.

### Failure boundary and evidence

The accepted pre-fix Batch 3 run reported 44 passing tests and one failing
regression in `test_g10_signed_malformed_child_payloads` (actions).
A correctly signed cursor with an integer UUID position reached
`qualitytrack/workflow.py:list_children`:

```python
values = (UUID(key[0]),)
```

The UUID constructor attempted string operations on the integer and raised
`AttributeError`, outside the existing `ValueError`, `TypeError`, and
`IndexError` boundary. This occurs on pagination invocation, not application
initialization. Signing validates integrity and caller/context binding; it
does not establish the types of decoded JSON values.

`qualitytrack/main.py:create_app` maps unexpected exceptions to:

```python
Problem(status=500, code="internal_failure", title="Request could not complete")
```

This explains the previously observed HTTP 500 rather than the intended
controlled HTTP 400. No environment installation or policy change is justified.

### Same-pattern inspection

| Endpoint | Conversion owner | Finding / remedy |
| --- | --- | --- |
| GET `/api/v1/defects/{defect_id}/actions` | `workflow.list_children` | Check UUID position is a string before `UUID()` |
| GET `/api/v1/defects/{defect_id}/causes` | `workflow.list_children` | Same guard on second position |
| GET `/api/v1/defects` | `security.decode_cursor`, called by `defects.list_defects` | Same guard on payload identifier |
| GET `/api/v1/overdue-actions` | `reporting.overdue_actions` | Same guard on third position |
| GET `/api/v1/defects/{defect_id}/history` | `workflow.list_children` | Already rejects non-integer, boolean, nonpositive, or wrong-length positions; no source change |
| GET `/api/v1/actions/{action_id}/history` | `workflow.list_children` | Same existing strict revision check; no source change |

All conversion guards remain inside the existing controlled `invalid_cursor`
boundary. Well-formed UUID strings still use `UUID()` for format validation;
malformed strings raise the already-caught `ValueError`. No broad exception
suppression, authentication changes, or fallback behavior was introduced.

For example, the actions branch now reads:

```python
if not isinstance(key[0], str):
    raise ValueError
values = (UUID(key[0]),)
```

The analogous guards are in the existing conversion blocks of
`security.decode_cursor` and `reporting.overdue_actions`.

### Sanitized request/response evidence

Request: authenticated GET of each of the six cursor-bearing endpoint templates
above, with an integrity-valid, caller/context-bound continuation containing a
malformed position. Submitted cursor values and authentication headers are
intentionally not retained.

UUID-based cases use a non-string position. History cases use a boolean
revision, demonstrating the existing strict integer boundary.

Post-fix real HTTP result for all six:

- Status: `400`
- Content-Type: `application/problem+json`
- Cache-Control: `private, no-store`
- Exact safe response body:

```json
{"type":"about:blank","title":"Page continuation is invalid","status":400,"code":"invalid_cursor"}
```

Each body validated against its response schema from live `/openapi.json`.
The harness also asserted the submitted continuation was absent from the body.

### Regression protection

`backend/tests/test_batch3_gaps.py` retains the accepted tests with no skip,
xfail, or relaxed expected status:

- `test_g10_signed_malformed_child_payloads`: actions, causes, defect history,
  and action history; extended causes cases reach UUID conversion with a valid
  aware timestamp and malformed UUID positions.
- `test_signed_malformed_list_uuid_positions`: defects and overdue lists,
  parameterized over integer, null, boolean, object, array, and malformed
  string positions.

Focused Python 3.11.17 command:

```text
python -m pytest -q tests/test_batch3_gaps.py -k 'g10 or signed_malformed_list'
16 passed, 41 deselected, 1 warning in 18.48s
```

The warning is a Starlette/AnyIO deprecation warning, not a test failure.
Full-suite and live HTTP methodology/results are recorded in the linked
validation report. No additional defect was confirmed by this invocation.
