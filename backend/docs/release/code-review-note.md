# Release code-review note — REL-2026.10.22-prep

## Review scope

This is a source-informed proposal, not an implemented refactor or exhaustive review. No application, dependency, test, or migration files are changed in Batch 1. Existing [verification and audit evidence](../../../frontend/docs/verification-and-audit.md) informs risk but does not validate these unimplemented proposals.

## Proposed low-risk refactors

| Issue and source | Proposed change | Risk and protected behavior | Validation required in a separately approved change |
| --- | --- | --- | --- |
| `frontend/src/features/defects/useWorkflow.ts` embeds nested mutation-feedback selection in `submit`. | Extract only the pure status/uncertainty-to-message selection into a local typed helper. Leave state changes and refresh decisions in place. | Low expected risk if precedence remains uncertainty first. Preserve conflict messages, explicit renewed review, serialized writes and no automatic replay. | Add table-driven message tests; run existing workflow tests, frontend tests/build and real stale-revision/lost-response regressions. |
| `frontend/src/api/client.ts` filters Problem fields inline with transport orchestration. | Extract pure safe Problem parsing into a module-local helper with unchanged media-type and fallback behavior. | Low expected risk for an exact extraction. Preserve actual HTTP status, string-only field errors, generation checks, safe fallbacks and 401 handling. Never display proxy HTML. | Test malformed JSON, wrong media type, non-string fields and valid Problems; run client tests plus browser-login, identity-isolation and uncertain-write regressions. |
| `frontend/src/app/App.tsx` and `frontend/src/features/defects/WorkflowPage.tsx` independently construct encoded record routes. | Consider a small pure record-base route builder without changing registered routes. | Low expected risk but lower value than the two extractions above. Preserve `encodeURIComponent`, direct links, remount keys, protected routing and review reset. | Test ordinary and special-character identifiers; run route/workflow tests, build and deep-link/login/journey smoke. |

These are optional follow-up proposals, not release changes already made. Keep any accepted extraction isolated from dependency upgrades, permission changes, concurrency policy or query-cache redesign.

## Refactors deliberately not done

**React Router 7 migration is deliberately not done.** The inspected manifest pins Router DOM 6.30.6. The recorded dependency review reports unresolved production Router findings and no same-major patched path at review time. A supported-major migration may be necessary security work, but it is not low-risk docs-only cleanup. It requires explicit scope approval, fresh advisory/version review, dependency compatibility checks, protected-route/deep-link/session tests, build verification and browser regression. Deferral is not vulnerability acceptance or a claim that BrowserRouter eliminates the advisories.

A broad rewrite of the workflow controller into a new mutation/state-machine architecture is also deliberately deferred. It coordinates exact reviewed ETags, identity-scoped queries, serialized writes, refresh ordering and uncertain outcomes. Rewriting those safety boundaries would expand release risk beyond the value of cleanup without dedicated design and regression scope.

The frozen initial migration schema is deliberately not deduplicated against live application models. The inspected revision loads frozen metadata, preserving historical behavior. Importing current models instead would allow later application changes to alter revision `0001`. Future schema changes require new reviewed migrations, not edits to the frozen definition.

## Approval boundary

Approve this documentation independently of any future refactor. No source refactoring was performed, and no proposed validation is represented as executed. The [readiness checklist](readiness.md) retains the security findings and full-product gaps. Requester approval is required before any commit or push.
