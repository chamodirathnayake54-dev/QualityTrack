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
| DateFilters | D | No |
| Journey | W | No |
| LoginPage | Page presentation itself | No |
| DefectListPage | Page presentation itself | No |
| LogDefectPage | Page presentation itself | No |
| WorkflowPage | Page presentation itself | No |
| NotFoundPage | Page presentation itself | No |

**11 / 28 × 100 = 39.29%**, below the delivery target of at least 40%.

This post-polish measurement reviews commit
`89f11449d44ded85f485852fedd90303e8db4a8b`. The previous 42.31% figure omitted
the page-local `DateFilters` presentation component and predates the new
`Journey` component. Both belong in the denominator, but neither is consumed
by two distinct page components. Journey appears on S2–S4 through the single
`WorkflowPage`; three routes do not make it cross-page reuse. The numerator
remains 11. Styling improvements do not change that count, and no artificial
sharing is introduced to meet the target.

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
