# QA-07 System Defect Log

## Classification and evidence convention

Candidate: uncommitted Batch 2 worktree based on
`8e3abfaca941f1ddfea2f6f866144ae22faada31`; execution date 2026-10-22.
See [Batch 2 results](system-validation-batch2.md) and its linked evidence.
Severity: P0 critical exposure/corruption/outage; P1 major required journey
blocked; P2 bounded setup/usability/test reliability defect; P3 minor.
Severity does not imply delivery priority or release approval.

“Open scope gap” means unmet full-product acceptance, not an instruction to
expand this bounded release in a bug-fix batch. Origin phase is selected from
requirements, design, implementation, documentation. No requirements defect
or persona-policy approval is inferred merely from absent implementation.

## Product and documentation defects

| ID / cases | Severity | Boundary and confirmed root cause | Origin phase | Status / remedy / owner |
| --- | --- | --- | --- | --- |
| QT-SYS-01 / 01 | P2 | Repository setup documentation/configuration: required `VITE_API_BASE_URL` was blank in the shipped example; normal documented startup did not supply it. Correct application validation then displayed Configuration required. This is not a fetch or authentication code defect. | Documentation | **Fixed and retested, pending review.** Example supplies `/api/v1`; README explains explicit configuration. Python documentation regression and real case 01 pass. Frontend/documentation owner. |
| QT-SYS-02 / 14, 18 | P1 | Full-product optional-photo acceptance conflicts with deliberately narrowed photo-free delivery: S1 has no file control and backend capture rejects every `photo` part with 422 `photo_not_supported`. Reserved storage does not implement upload acceptance. | Design — delivered scope explicitly narrowed in backend/frontend docs; no evidence that the original photo requirement was withdrawn | **Open scope gap.** Real case 14 confirms absence and safe rejection without a write. Do not label it passed or remove backend rejection without a separately designed upload feature. Product and frontend/backend owners must approve a photo-free limitation or schedule implementation. |
| QT-SYS-03 / 15–17 | P1 | Required broader supervisor UI has no overdue, progression, closure, or reopen routes/controls in current App routes. APIs exist but cannot provide browser acceptance. | Implementation — incomplete full-product screen delivery | **Open scope gap; not executable in this release.** API diagnostics pass for the tested authority/calendar/lifecycle variants; no UI fix attempted because adding these workflows is feature scope, not a minimal defect fix. Product/frontend owners. |
| QT-SYS-04 / 18–19 | P1 | No browser PDF/export journey; provisional auditor persona and production grants are unvalidated. Photo-inclusive export also depends on QT-SYS-02. | Implementation for missing UI; persona-policy approval remains a separate requirements clarification | **Open scope gap; not executable in this release.** API read/export denial and PDF signature checks are supporting diagnostics only. Product/frontend owners; persona authority requires product approval. |

No P0 application defect was observed. QT-SYS-01 is the only product-facing
fix in this proposal; the three P1 records remain open for full-product scope.
No acceptance waiver has been granted.

## Source evidence for classification

- Configuration: `frontend/src/main.tsx` constructs
  `new ApiClient(import.meta.env.VITE_API_BASE_URL ?? '')`.
  `frontend/src/api/client.ts`, constructor, rejects missing configuration with
  `if (!baseUrl || ... || !baseUrl.endsWith('/api/v1'))`.
  Before this proposal `.env.example` contained `VITE_API_BASE_URL=`.
  Correcting the example is the narrow repository-owned remedy; changing the
  constructor would weaken an intentional validation boundary.
- Photos: `backend/qualitytrack/main.py`, `capture`, contains
  `if "photo" in form: raise Failure(422, "photo_not_supported", ...)`.
  Real browser case 14 observes no `input[type=file]`. The existing backend
  README explicitly describes photo rejection, and frontend README describes
  photo-free capture. Thus an unimplemented requirement is not an environment
  prerequisite and cannot be repaired by installing a package.
- Missing screens: `frontend/src/app/App.tsx`, `App`, registers `/defects`,
  `/defects/new`, and `/defects/:defectId/{causes,investigation,actions}`, then
  the wildcard `NotFoundPage`. No overdue/export/closure screen is registered
  in that inspected entrypoint. Case inventory already identifies these
  broader browser paths as unavailable.
- Closed-parent reopening is **not** an additional runtime defect:
  `backend/qualitytrack/workflow.py`, `transition_action`, deliberately raises
  `Failure(503, "policy_unavailable", ...)` for reopening on a Closed parent.
  `transition_defect` permits `("Closed", "Under Investigation")`, not Closed
  → Open. Real API tests first confirm 503, explicitly reopen the parent, then
  reopen its action successfully and reconcile retained completion evidence.

The first three points are verified by source inspection and real execution.
The origin of the photo scope decision is evidenced by delivered documentation;
who authorized it historically is unknown. Missing persona approval is not
resolved by inventing or expanding grants.

## Resolved validation-harness defects

These belong to new QA automation, not the product pass/fail count.

| ID | Severity / origin | Cause and boundary | Resolution and regression |
| --- | --- | --- | --- |
| QT-QA-01 | P2 / Implementation | Full-page `page.goto` after login erased the intended memory-only session; repeated capture attempted to reuse a confirmation view. | Resolved: SPA navigation plus explicit S1 reset. Final journeys and capture variants pass; explicit reload still requires sign-in. |
| QT-QA-02 | P2 / Implementation | Retirement request omitted the required `EmptyCommand` JSON body and returned 422. | Resolved: send `{}` and strong type ETag. Final real retirement/stale-capture case passes. |
| QT-QA-03 | P2 / Implementation | In-memory evidence arrays were lost on Playwright worker restart and overwrote earlier cases. | Resolved: append per-test evidence to the ledger; initialize once per run. Final artifact contains all 13 group dispositions. |
| QT-QA-04 | P2 / Implementation | Additional lifecycle test assumed unsupported Closed → Open rather than Closed → Under Investigation. | Resolved against the inspected state machine; final complete/close/reopen diagnostics pass. |

Initial filesystem-test attempts were replaced, not shipped: jsdom URL handling
and Vite's deliberate `.env` import denial were test-setup incompatibilities.
The final Python documentation regression passes without new dependencies or
relaxing Vite's safeguards.

## External prerequisites, not repository defects

The process initially lacked installed declared dependencies, supported Python
3.11 and Node 22, and the Chromium binary matching the pinned Playwright
version. Repository dependency declarations and runtime documentation already
specified these capabilities; provisioned them outside Git rather than alter
product behavior. The exact first browser boundary was
`browserType.launch: Executable doesn't exist ... chromium_headless_shell-1248`.
The final matching-browser run passed.

Production database-role enforcement, validated persona/grant policy, PDF
visual/content completeness, DST cases, security findings, performance, and
accessibility acceptance remain qualification work, not silently closed defects.
