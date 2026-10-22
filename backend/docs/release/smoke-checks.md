# Release smoke checks — REL-2026.10.22-prep

## Scope and evidence

These are proposed manual checks for the bounded engineer journey, not new canonical test-case artifacts or newly executed results. Run only against an approved isolated environment with synthetic data. QA should record artifact identity, schema revision, environment, plant timezone, operator, timestamp, safe record IDs, actual outcome and any failure. Do not record passwords, tokens, connection strings, login bodies, or raw traces.

Prior execution is in [QA Batch 2](../qa/system-validation-batch2.md). The full executable regression and its commands are in the [critical regression procedure](../qa/system-critical-regression.md). Its opt-in runner creates its own private cluster and uses ports 8000, 4173 and 4174; do not point it at deployment services. It overwrites `batch2-evidence/`, so archive reviewed evidence before a separately authorized rerun.

## Manual release smoke

| Step | Operator action | Required observation |
| --- | --- | --- |
| Setup | Open the configured frontend and sign in as the permitted synthetic engineer. | Login completes against the real API; current identity and intended plant zone appear. No configuration-required message or proxy HTML masquerading as API success. |
| Lookup readiness | Open new defect capture and inspect type, line and shift options. | Real active choices show code and label. Use actual IDs from this environment, not copied QA UUIDs. |
| S1 capture | Enter a unique synthetic part number, quantity 1, severity Major and valid lookup choices; submit once, without photo. | Confirmed defect and stable identifier appear with the selected captured context. Do not retry if outcome is unconfirmed. |
| S2 cause | Open the record's cause page, enter a nonblank preliminary cause and save once. | Confirmation and saved cause with actor appear after the real read refresh. Unsaved text is not evidence of a persisted cause. |
| S3 investigation | Follow the investigation link, inspect saved context, check the explicit review confirmation and submit. | Under Investigation is confirmed; history shows Open to Under Investigation, actor and plant-zone time. A stale revision must require refresh and renewed review, never silent replay. |
| S4 action | Add a synthetic corrective action with description, returned eligible owner, future plant-calendar date and explicit Open status. | Action is confirmed and associated with the same defect with matching fields. Completion/effectiveness is not claimed. |
| Persistence | Revisit cause, investigation and actions via SPA links; then reload and sign in again. | Saved context/history/action remain. Reload requiring sign-in is expected; unsaved drafts need not persist. |
| Session boundary | Sign out and attempt a protected application route. | Protected content requires authentication; no prior protected view is restored as an authenticated session. This brief smoke does not replace the delayed-response isolation regression. |
| Routing | Navigate an existing record deep link after reload and authenticate if prompted. | SPA route resolves; `/api` still reaches API responses, not SPA fallback. |

## Acceptance and failure handling

All steps must pass on the intended artifact before the bounded release gate is green. A smoke pass cannot close unresolved dependency findings, photo acceptance, missing supervisor/auditor screens, production role enforcement, or full-product No-Go.

For unconfirmed writes, reconcile before deliberately submitting again. For authorization failures, check identity and grants without weakening policy. For integrity mismatch, cross-session data exposure or sustained persistence errors, stop and follow the [rollback runbook](operations-and-rollback.md).

The recorded 14/1/5 canonical dispositions must remain visible. Do not count a photo-rejection demonstration or API-only diagnostics as acceptance of absent browser journeys. Security scans, broad backend requalification and a restore rehearsal are separate gates, not consequences of this smoke passing.
