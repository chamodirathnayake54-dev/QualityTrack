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

**Post-polish result: 34/40 = 85% alignment**, below the proposal's requested
90% review target under this rubric. This source review is against commit
`89f11449d44ded85f485852fedd90303e8db4a8b`. Approval of remaining verification
blockers does not turn missing presentation fields into matched checks.

## Checklist

| Screen | Checks matched | Differences | Score |
| --- | --- | --- | --- |
| S1 | Heading/required guidance; part input; configured type; positive integer quantity feedback; production line; shift; explicit manual severity; confirmed success/onward link; retained-input/error/loading outcomes | Optional photo control absent (approved photo-free deviation) | 9/10 |
| S2 | Record/context heading; current status; initial 5-Why framing; labelled prompt; preliminary-cause helper; blank/length feedback; saved-cause list; save/outcome feedback; investigation link | Recorded list precedes editor, whereas mockup places editor before list | 9/10 |
| S3 | Heading; current status; requested status; recorded causes; preliminary-not-validated explanation; empty-cause guidance/return link; explicit transition control; pending/error outcomes; action onward link | History shows old/new status and timestamp but omits actor; the combined attributable-history check is not matched | 9/10 |
| S4 | Heading/context/status; description; assignable owner; due date; explicit status; Complete notes/authority caveat; save/error/pending outcomes | Associated list precedes form rather than follows it; no separate “Add another action” control (cleared form remains available); associated list omits the saved owner, so retained-associated-fields check is not matched | 7/10 |

The unchanged ten-check denominators give S1 90%, S2 90%, S3 90% and S4 70%.
The previous 36/40 figure credited attributable history and retained action
fields that the current JSX no longer fully displays. These are presentation
deductions, not claims that the API has lost the actor or owner data. Decorative
icons, badges and the new progress navigation improve presentation but do not
replace those checks or earn additional points outside the existing rubric.

## Other visible adaptations and qualifications

- S1 quantity appears before the lookup selectors rather than after defect type;
  all are in one logical capture group. This minor ordering difference is
  recorded, but not separately scored beyond the ten checks above.
- S2 navigation is always available rather than presented as a post-save gate.
  Entering S3 never mutates; the API remains the cause-presence authority.
- S3 adds an explicit reviewed-context checkbox and refresh control for ETag
  safety. Its history appears above the request form. These are recorded
  hierarchy additions, not fabricated backend requirements.
- S4's owner selector uses server display names, but the associated list shows
  description, due date and status only. Neither owner reference nor display
  name is rendered there; this is now an explicit scored gap.
- Memory-only authentication is approved and explained on login.
- Photo-free messaging is explicit and there is no misleading upload control.
  Optional-photo US-02 acceptance is not claimed.

## Responsive and accessibility polish

Shared tokens now bound control widths, allow grid children/fieldsets to shrink,
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
