# QA-07 System Validation Case Inventory

## Status and execution convention

All 20 cases are draft designs, not execution results. Read the [system strategy and gates](system-validation-batch1.md) first. Canonical steps and expected results are held in the linked Spec Builder JSON records; this inventory provides the traceability view, not a second editable case definition.

Every case requires the strategy's disposable real-stack environment, synthetic users, recorded grants, and safe evidence handling. Successful writes must be independently retrieved and associated to the correct defect; retain sanitized network and data/history evidence. A first-time cohort follows labels and prompts without saved knowledge; a repeat cohort revisits saved records and recovery paths. These are test perspectives, not claims that real users participated.

S1–S4 mean the engineer UX screens. J-SUP and J-AUD are local test grouping labels for broader backlog journeys, not new product requirements. “Cross-cutting” mappings test risks supporting the named AC, not new numbered product criteria. Auditor authority is provisional and conditional; neither role names nor test design provision grants.

## Traceability inventory

| Case / canonical record | Journey | Backlog / source AC mapping | Persona and experience | Priority / planned boundary |
| --- | --- | --- | --- | --- |
| [01 — configuration](../../../../kavia-docs/CodeWiki/Artifacts/SpecBuilder/json/test_cases/qa07-01.json) | Entry → S1 | US-01; AC-01a (cross-cutting setup) | Engineer, first-time | High; isolated configuration negative, then restore. |
| [02 — complete journey](../../../../kavia-docs/CodeWiki/Artifacts/SpecBuilder/json/test_cases/qa07-02.json) | S1 → S2 → S3 → S4 | US-01/04/06/07/08; AC-01a, AC-02a, AC-03b/f, AC-04a/c | Engineer, first-time | High; primary real-stack path. |
| [03 — lookup identity](../../../../kavia-docs/CodeWiki/Artifacts/SpecBuilder/json/test_cases/qa07-03.json) | S1 | US-01/03; AC-01a, AC-02d | Engineer, first-time | High; code/label versus submitted ID. |
| [04 — invalid capture](../../../../kavia-docs/CodeWiki/Artifacts/SpecBuilder/json/test_cases/qa07-04.json) | S1 | US-01/04; AC-01c, AC-02c; DR-19 | Engineer, first-time | High; missing-field and quantity variants. |
| [05 — capture denial](../../../../kavia-docs/CodeWiki/Artifacts/SpecBuilder/json/test_cases/qa07-05.json) | S1 | US-01; AC-01e | Engineer, repeat | High; API enforcement, not merely hidden controls. |
| [06 — retired type](../../../../kavia-docs/CodeWiki/Artifacts/SpecBuilder/json/test_cases/qa07-06.json) | S1 | US-03; AC-02d | Engineer, repeat | High; controlled lookup retirement race. |
| [07 — cause presence](../../../../kavia-docs/CodeWiki/Artifacts/SpecBuilder/json/test_cases/qa07-07.json) | S2 → S3 | US-06; AC-03a/c/d/e | Engineer, first-time | High; blank versus one preliminary cause. |
| [08 — no-cause gate](../../../../kavia-docs/CodeWiki/Artifacts/SpecBuilder/json/test_cases/qa07-08.json) | S3 | US-06/07; AC-03b/d | Engineer, repeat | High; no persisted status/history mutation. |
| [09 — history attribution](../../../../kavia-docs/CodeWiki/Artifacts/SpecBuilder/json/test_cases/qa07-09.json) | S3 | US-07; AC-03f | Engineer, repeat | High; exact old/new actor/time reconciliation. |
| [10 — stale review](../../../../kavia-docs/CodeWiki/Artifacts/SpecBuilder/json/test_cases/qa07-10.json) | S3 | US-07; AC-03b/f; DR-03 | Engineer, repeat | High; concurrent update and missing-grant variants. |
| [11 — multiple actions](../../../../kavia-docs/CodeWiki/Artifacts/SpecBuilder/json/test_cases/qa07-11.json) | S4 | US-08; AC-04a/b/c | Engineer, repeat | High; append and reconcile fields. |
| [12 — reload recovery](../../../../kavia-docs/CodeWiki/Artifacts/SpecBuilder/json/test_cases/qa07-12.json) | S1–S4 revisit | US-01/06/08; AC-01a, AC-03b, AC-04a (cross-cutting session) | Engineer, repeat | High; saved data survives ephemeral session loss. |
| [13 — logout isolation](../../../../kavia-docs/CodeWiki/Artifacts/SpecBuilder/json/test_cases/qa07-13.json) | S1–S4 session boundary | US-01/17; AC-01e, AC-03f; DR-03 | Engineer then conditional auditor, repeat | High; delayed responses and cache isolation. |
| [14 — optional photo gap](../../../../kavia-docs/CodeWiki/Artifacts/SpecBuilder/json/test_cases/qa07-14.json) | S1 | US-02; AC-01b/d | Engineer, first-time | High; known requirement gap, not expected full-AC pass. |
| [15 — supervisor overdue](../../../../kavia-docs/CodeWiki/Artifacts/SpecBuilder/json/test_cases/qa07-15.json) | J-SUP: overdue review | US-11; AC-05a/b/c/d | Supervisor, first-time | High; browser path unavailable; supporting API checks separate. |
| [16 — action and closure](../../../../kavia-docs/CodeWiki/Artifacts/SpecBuilder/json/test_cases/qa07-16.json) | J-SUP: complete → close → reopen | US-07/09/10; AC-03f, AC-04d/e/f | Supervisor, repeat | High; broader browser workflow unavailable. |
| [17 — supervisor denial](../../../../kavia-docs/CodeWiki/Artifacts/SpecBuilder/json/test_cases/qa07-17.json) | J-SUP: restricted workflow | US-07/20; AC-03f, AC-08d; DR-03 | Supervisor, repeat | High; direct API denial supports but does not replace missing UI. |
| [18 — auditor evidence](../../../../kavia-docs/CodeWiki/Artifacts/SpecBuilder/json/test_cases/qa07-18.json) | J-AUD: review → export | US-17/18/16/19; AC-03f, AC-08a/b/c | Conditional auditor, first-time | High; missing export UI, photo limitation, and persona approval. |
| [19 — auditor isolation](../../../../kavia-docs/CodeWiki/Artifacts/SpecBuilder/json/test_cases/qa07-19.json) | J-AUD: restricted evidence | US-17/18/20; AC-08d; DR-03 | Conditional auditor, repeat | High; read/export scope and no write authority. |
| [20 — intentionally break response delivery](../../../../kavia-docs/CodeWiki/Artifacts/SpecBuilder/json/test_cases/qa07-20.json) | S4 failure/recovery | US-08; AC-04a/b; UX uncertain-write recovery (cross-cutting) | Engineer, repeat | High; controlled real-stack fault experiment, never production. |

## Coverage limits and review

The design covers the requested three persona perspectives and first-time/repeat use, not validated persona acceptance. Cases 15–19 must carry explicit blocked browser dispositions while their routes or permissions are unavailable. Case 14 must preserve the photo requirement failure/gap rather than treating the implemented 422 response as AC-01b acceptance. These are draft statuses now, not newly observed execution failures.

The inventory is risk-selected, not exhaustive coverage of all 40 backlog ACs. Rule-mode AC-02b remains conditional on approval; analytics AC-06 and AC-07 are outside the current implemented/demo scope. Complete photo/PDF, accessibility, performance, and production-policy qualification remain open. Review exclusions against the intended release before approving execution.

## Canonical relationships and sources

The backlog stores embedded US IDs in authored Markdown, not standalone JSON story artifacts. Each case's `parent_story` is a qualified repository-document reference to the corresponding section. No nonexistent JSON story, roadmap identity, symmetric story link, or new requirement is invented; the source backlog remains unchanged. Canonical case records contain their own journey, AC, and cohort tags.

Sources are the [Stage 2 backlog](../../../../kavia-docs/CodeWiki/Specs/FeatureSpecs/qualitytrack-stage-2-backlog.md), [Stage 2 UX](../../../../kavia-docs/CodeWiki/Specs/FeatureSpecs/qualitytrack-stage-2-ux.md), implementation sources cited in the strategy, and [backend sign-off](api-readiness-signoff.md).
