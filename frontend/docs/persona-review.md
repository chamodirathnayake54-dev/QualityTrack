# Persona-perspective UX review

## Method

Heuristic walkthrough against the Stage 2 Quality Engineer journey and the
implemented screens; no interviews, usability study, factory pilot or persona
sign-off was conducted. The mocked browser path represents an explicitly
permitted caller, not automatic authority from a persona name.

## Quality Engineer: log and investigate

- **Find and enter work:** clear defect-list and capture entry, production
  context and severity labels, configured choices rather than invented values.
  Single-column small-screen layout keeps entry order predictable.
- **Trust the save:** “Defect logged”, recorded-cause content, server history
  and associated action fields distinguish saved evidence from draft input.
  Unconfirmed writes warn against blindly retrying.
- **Explain the cause:** initial 5-Why prompt accepts preliminary text without
  suggesting five answers or validated causality are required.
- **Start investigation deliberately:** current/requested status, saved causes,
  explicit review and exact-revision submission make the state change distinct
  from recording a cause. The extra checkbox is useful but adds a step.
- **Assign follow-up:** eligible owner choices, explicit status, calendar date,
  and preserved associated actions support follow-through. Complete is not
  effectiveness verified, and assignment permission is not completion authority.

### Friction and remaining risks

Photo evidence is unavailable (approved); this may limit shop-floor usefulness
but is not simulated. Memory-only sessions require sign-in after reload and
drafts are not persistent; login states this, but navigating away can still lose
work. Saved owner usernames now use “Owner:” and history actors “Changed by”,
preserving attribution without exposing internal record UUIDs as visible text.
The journey navigation is exposed before a cause is saved; entering the next
screen is safe, but only server rejection establishes the actual gate.

Factory lighting, gloves, shared devices, assistive technology and unreliable
network conditions have not been validated with users. The existing 44px
controls/review label are helpful, not evidence of factory-device acceptance.

## Production Supervisor perspective

Permitted transition/assignment work can be reviewed in context, with retained
history and action fields. Supervisor-authored US-07/US-08 are not silently
reassigned as blanket engineer authority. Missing grants remain a denial, not an
invented approval queue or supervisor handoff. Overdue dashboards, analytics,
action progression and closure are outside this frontend journey.

## Auditor perspective

Historical lookup labels and attributable transition history help interpret
records. Cause text remains explicitly preliminary. This is not auditor-story
acceptance: no audit export UI, full evidence package, photo support or
snapshot-completeness claim is provided. Collection continuation remains visible
when returned; a first page is not treated as the whole record.

## Conclusion

The bounded permitted journey is coherent, with transparent saved/draft
distinctions. Heuristic acceptance is conditional on the approved scope and
actual grants; production readiness, accessibility conformance and genuine
persona validation remain unproven. [UX alignment](ux-alignment.md) records the
specific mockup deviations rather than hiding them in this qualitative review.
