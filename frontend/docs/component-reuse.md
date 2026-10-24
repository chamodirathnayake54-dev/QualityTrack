# Component reuse measurement

## Approved method

The [Batch 0 proposal](../../../kavia-docs/CodeWiki/Specs/ArchitectureSpecs/qualitytrack-qt06-frontend-batch-0.md)
defines reuse as distinct production presentation components consumed by at least
two page components divided by all distinct production presentation components.
Tests, hooks, providers and router infrastructure are excluded. Repeated uses
on one page do not count. Transitive presentation composition counts as
consumption and is shown explicitly below.

Treat `WorkflowPage` as **one** consuming page component even though it renders
three routes. No three-page inflation of S2–S4 reuse is used. Include page
presentation components themselves in the denominator, conservatively.

## Inventory

Page abbreviations: L = LoginPage, D = DefectListPage, C = LogDefectPage,
W = WorkflowPage, S = DefectSummaryPage, N = NotFoundPage.

| Presentation component | Consuming pages | Reused |
| --- | --- | --- |
| Button | L, D, C, W | Yes |
| Field | L, D, C via CaptureFields, W via editors | Yes |
| TextInput | L, D (also DateInput), C | Yes |
| TextArea | W via editors, S via transition notes | Yes |
| Select | D, C via CaptureFields, W via action fields | Yes |
| DateInput | D, W via action fields | Yes |
| RadioGroup | C via CaptureFields | No |
| ErrorSummary | L, D, C, W | Yes |
| Alert | L, D, C/W also via ReadFeedback | Yes |
| StatusBadge | D, W via DefectContextSummary | Yes |
| Skeleton | D, C/W via ReadFeedback | Yes |
| EmptyState | D, C/W via ReadFeedback/WorkflowCollection | Yes |
| DataTable | D | No |
| ReadFeedback | C, W | Yes |
| CaptureFields | C | No |
| CauseEditor | W | No |
| CorrectiveActionFields | W | No |
| InvestigationSummary | W | No |
| AssociatedActionList | W | No |
| DefectContextSummary | W, S | Yes |
| WorkflowCollection | W, S | Yes |
| EventList | W (status history), S (defect and action history) | Yes |
| RecordAttribution | W, S via CauseList and EventList | Yes |
| CauseList | W (cause and investigation routes), S | Yes |
| TransitionControl | S | No |
| ActionCard | S | No |
| AuditExport | W (cause, investigation and action routes), S | Yes |
| LoginPage | Page presentation itself | No |
| DefectListPage | Page presentation itself | No |
| LogDefectPage | Page presentation itself | No |
| WorkflowPage | Page presentation itself | No |
| DefectSummaryPage | Page presentation itself | No |
| NotFoundPage | Page presentation itself | No |

**18 / 33 × 100 = 54.55%**, meeting the delivery target of at least 40%.

The audit-trail correction folds the single-use DateFilters controls into
DefectListPage and the journey markup into WorkflowPage. The standalone
Journey module is removed. Evidence is `<Field label="Start date">` in
DefectListPage and `<nav aria-label="Defect journey">` in WorkflowPage.
Against the reported 11/28 = 39.29% inventory, these remove two denominator
entries only; the numerator remains 11. WorkflowPage still counts as one
consuming page, not three routes. No counting rule changed.

Excluded: App, AppShell (shell infrastructure), AuthProvider/AuthBoundary,
RouteFocus, RecordEntry, WorkflowRoute, all hooks, API types/classes, tests,
React fragments and native HTML elements. `src/ui/index.tsx` is a barrel, not
another component. Named components are counted once, regardless of use count.

## Evidence and limitations

Inventory comes from production TSX declarations and JSX composition in
`src/ui/`, `src/features/` and `src/app/App.tsx`. This is a manual static
measurement, not runtime telemetry. Components rendered only for error/empty
states still count as page consumption. A direct-import-only metric would be a
different method and is not substituted here.

The two inline workflow views were named for the requested boundary review,
not shared artificially across unrelated pages to inflate reuse.

## Supervisor workflows update

DEV-09 adds the DefectSummaryPage (S, one consuming page) and three
presentation components: EventList, TransitionControl and ActionCard. EventList is
shared by WorkflowPage and DefectSummaryPage, replacing duplicated history markup.
TextArea, DefectContextSummary and WorkflowCollection are now also consumed by S.
Counting rules are unchanged: the denominator grows from 26 to 30 and the numerator
from 11 to 15. TransitionControl and ActionCard are single-use and are not counted
as reused. Saving, validation and review rules live in `useTransition.ts`
(hooks, excluded from this inventory), so the components only present.

## Audit PDF export update (DEV-10)

DEV-10 adds one presentation component, AuditExport, consumed by WorkflowPage
(one consuming page, three routes) and DefectSummaryPage, so it counts as reused.
The denominator grows from 30 to 31 and the numerator from 15 to 16. Button gained
a `variant` option rather than a new component. The download rules live in
`useAuditExport.ts` (a hook, excluded from this inventory); AuditExport only presents.
Counting rules are unchanged.

## UX-15, UX-16 and UX-12 update

CauseList replaces duplicated cause markup in W and S. RecordAttribution is
consumed transitively by both pages through CauseList and EventList and owns
the shared actor/plant-time text. These add two reused presentation components:
16/31 becomes 18/33 = 54.55%. W still counts once, not once per route.
Action authority hints remain in useTransition.ts (excluded), with no new
presentation component. UX-12 retains the existing omission of inaccessible
lookup filters; no component count changes arise from that check.
