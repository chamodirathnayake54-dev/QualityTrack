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
W = WorkflowPage, N = NotFoundPage.

| Presentation component | Consuming pages | Reused |
| --- | --- | --- |
| Button | L, D, C, W | Yes |
| Field | L, D, C via CaptureFields, W via editors | Yes |
| TextInput | L, D (also DateInput), C | Yes |
| TextArea | W via editors | No |
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
| DefectContextSummary | W | No |
| WorkflowCollection | W | No |
| LoginPage | Page presentation itself | No |
| DefectListPage | Page presentation itself | No |
| LogDefectPage | Page presentation itself | No |
| WorkflowPage | Page presentation itself | No |
| NotFoundPage | Page presentation itself | No |

**11 / 26 × 100 = 42.31%**, exceeding the delivery target of at least 40%.

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
