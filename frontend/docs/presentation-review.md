# Five-component no-business-logic review

## Scope and outcome

Static review of production implementations after Batch 4 changes.
**All five pass the bounded presentation-boundary review**, with the
qualifications below. This means no backend authorization/lifecycle policy,
network calls, cache updates or committed-state decisions in these components;
it does not mean they contain literally no conditional rendering.

| Component / source | Observed responsibilities | Outcome |
| --- | --- | --- |
| CaptureFields — `src/features/defects/CaptureFields.tsx` | Render prepared draft/errors/choices; forward value changes; enumerate severity and lookup field metadata; native quantity min/max/step hints | Pass. Does not choose severity, fetch choices, remove retired choices, accept capture or inspect grants |
| CauseEditor — `src/features/defects/WorkflowPage.tsx` | Label text area, associate helper/error, forward edited text and disabled flag | Pass. Does not require five answers, count saved causes or establish causality |
| InvestigationSummary — `src/features/defects/WorkflowViews.tsx` | Static requested-status explanation and server-authority caveat | Pass. Does not decide transition eligibility, evaluate presence or choose a revision |
| CorrectiveActionFields — `src/features/defects/WorkflowPage.tsx` | Render supplied owners/draft/errors, explicit status choices and conditional completion-notes field | Pass with qualification. `status === 'Complete'` is visibility logic mirroring the contract, not authority or acceptance. Validation and eligibility remain elsewhere |
| AssociatedActionList — `src/features/defects/WorkflowViews.tsx` | Render provided confirmed description, owner reference, calendar date and status, keyed by server ID | Pass. Does not calculate overdue, completion authority or effectiveness |

InvestigationSummary and AssociatedActionList were previously inline page JSX.
They are now named, documented exports used by WorkflowPage; their extraction
does not introduce another data owner or domain layer.

## Responsibility trace

`main.tsx` → `App` routes → `WorkflowRoute`/`WorkflowPage` → these views.
Capture is `App` → `LogDefectPage` → `CaptureFields`.

`useCapture`, `useWorkflow`, `validation.ts` and `workflowValidation.ts` own form
coordination and mirrored input feedback. `src/api/client.ts` owns transport.
The backend owns actual grants, eligible owners, cause presence, transition
legality and committed revisions. The review does not certify all code in those
other modules or claim client-side checks are security enforcement.

The associated list receives only prepared saved actions; WorkflowCollection
owns presentation of loading/empty/error/continuation. No optimistic fake action
is added by the list. CaptureFields receives choices already prepared by the
controller. Conditional completion visibility never grants completion authority.

## Verification

Existing workflow/component tests continue to exercise these components through
real pages. The mocked browser journey exercises all five through routed entry
points, including server-confirmed action association. See
[verification and audit](verification-and-audit.md) for exact outcomes and limits.
