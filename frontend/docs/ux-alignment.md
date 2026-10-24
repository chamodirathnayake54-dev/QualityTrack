# S1–S4 UX alignment review

## Basis and method

Reviewed the [Stage 2 text mockups](../../../kavia-docs/CodeWiki/Specs/FeatureSpecs/qualitytrack-stage-2-ux.md)
against `CaptureFields.tsx`, `LogDefectPage.tsx`, `WorkflowPage.tsx`,
`WorkflowViews.tsx` and the feature controllers in `src/features/defects/`.

This is an analyst checklist of hierarchy, copy intent, fields and outcome
presentation, not pixel comparison, user testing, or full story acceptance.
Each screen has ten equally weighted checks below (1 matched, 0 different).
No weighting was specified in the proposal; this transparent rubric is local to
this review. Approved photo-free scope still incurs a visible deduction against
the original mockup rather than silently removing it from the denominator.

**Audit-trail correction: 36/40 = 90% alignment**, meeting the requested 90%
target under the unchanged rubric. WorkflowPage renders
`Changed by {entry.actor_ref}` and AssociatedActionList renders
`Owner: {action.owner_ref}`. These restore the two checks deducted in the
previous 34/40 = 85% review. No other score or denominator changed.

## Checklist

| Screen | Checks matched | Differences | Score |
| --- | --- | --- | --- |
| S1 | Heading/required guidance; part input; configured type; positive integer quantity feedback; production line; shift; explicit manual severity; confirmed success/onward link; retained-input/error/loading outcomes | Optional photo control absent (approved photo-free deviation) | 9/10 |
| S2 | Record/context heading; current status; initial 5-Why framing; labelled prompt; preliminary-cause helper; blank/length feedback; saved-cause list; save/outcome feedback; investigation link | Recorded list precedes editor, whereas mockup places editor before list | 9/10 |
| S3 | Heading; current status; requested status; recorded causes; preliminary-not-validated explanation; empty-cause guidance/return link; explicit transition control; pending/error outcomes; action onward link; attributable history with old/new status, timestamp and actor | None under this rubric | 10/10 |
| S4 | Heading/context/status; description; assignable owner; due date; explicit status; Complete notes/authority caveat; save/error/pending outcomes; retained associated description, owner, date and status | Associated list precedes form rather than follows it; no separate “Add another action” control (cleared form remains available) | 8/10 |

The unchanged ten-check denominators give S1 90%, S2 90%, S3 100% and S4 80%.
The restored fields use existing API data; no API contract changed. Decorative
icons, badges and progress navigation earn no additional points.

## Other visible adaptations and qualifications

- S1 quantity appears before the lookup selectors rather than after defect type;
  all are in one logical capture group. This minor ordering difference is
  recorded, but not separately scored beyond the ten checks above.
- S2 navigation is always available rather than presented as a post-save gate.
  Entering S3 never mutates; the API remains the cause-presence authority.
- S3 adds an explicit reviewed-context checkbox and refresh control for ETag
  safety. Its history appears above the request form. These are recorded
  hierarchy additions, not fabricated backend requirements.
- S4's owner selector uses server display names. The associated list shows the
  saved owner username even if that user is no longer in the assignable list.
- Memory-only authentication is approved and explained on login.
- Photo-free messaging is explicit and there is no misleading upload control.
  Optional-photo US-02 acceptance is not claimed.

## Responsive and accessibility polish

Shared tokens bound control widths, allow grid children/fieldsets to shrink,
wrap long text and style panels consistently. Layout remains single-column
below the existing 48rem breakpoint; list filters use three columns above it.
DOM order is unchanged by responsive CSS. Native labelled controls, severity
fieldset/legend, textual statuses, skip navigation, focusable error summaries
and heading focus are retained. S2/S4 required-input guidance was clarified;
the review checkbox label has a 44px minimum height.

The browser scenario checks route-heading focus and document overflow on login,
list and S1–S4 at 360×800 and 1280×800, plus a long action draft. It does not
establish all saved-content extremes, device suitability, keyboard-only task
completion, 200/400% zoom, contrast in all states, or screen-reader conformance.
No WCAG 2.2 AA certification is claimed. See [verification](verification-and-audit.md).

## DEV-09 note

The supervisor summary page is outside the S1–S4 mockup set, so the 36/40 = 90%
alignment is unchanged. The shared history list keeps the S3 attributable-history
check (old/new status, timestamp, actor) satisfied.

## DEV-10 note

The audit report panel (Export audit PDF button, progress text, photo note, outcome
message) is an addition outside the S1–S4 mockups. It does not remove or replace any
mockup element, so the 36/40 = 90% alignment is unchanged. The deviation is listed
here because S2–S4 now carry one extra panel under the defect context. For read-only
users the button uses the primary style; for users who can change the record it is
secondary so the page's main action stays the next workflow step.

## UX-15, UX-16 and UX-12 review

The same ten-check-per-screen rubric remains **36/40 = 90%** (S1 9/10,
S2 9/10, S3 10/10, S4 8/10). CauseList now shows each cause's recorded_by_ref
and recorded_at through the same actor/plant-time presentation as EventList.
This enriches the already-matched saved-cause check; it does not earn an extra
point or remove the S2 ordering deduction.

Summary action forms now require both an explicit grant and the owner/supervisor
presentation hint in transitionChoices. Only the explicitly server-bound
sample-supervisor may reopen; owner or supervisor may start/complete with the
appropriate grant. Hidden forms are replaced with owner guidance. The server
remains authoritative, including the existing friendly refusal fallback.
The summary is outside the S1–S4 rubric, so this does not change its score.

Supervisor and auditor list regression tests render the list with inaccessible
lookup data and URL filter IDs. Defect type, production line and shift selectors
are omitted, with no unavailable message or visible raw ID. The production list
already behaved this way; UX-12 needs no further presentation change.
These are mocked component checks, not real-server browser or persona usability
testing.
