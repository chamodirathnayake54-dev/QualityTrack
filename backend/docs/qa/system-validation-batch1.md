# QA-07 QualityTrack System Validation — Batch 1

## Status and prerequisite evidence

This is a docs-only proposal for approval in session QA-07-QualityTrack-System. It does not authorize execution, fixes, release, commit, or push. Both mandatory prerequisites passed in the QualityTrack repository: `git merge-base --is-ancestor e0a24dc HEAD` exited 0, and `git ls-files frontend/package.json backend/qualitytrack/main.py` listed both required files. The inspected HEAD was `4be660f6c4ad7d1be3f1c642cfe20e18946bd40f`. Existing untracked `.kavia/` and `logs/` directories were observed and left untouched.

The requester reports that S1–S4 passed against the real backend. That is supplied historical evidence, not a new run or evidence that the 20 proposed cases passed. The run's build, browser, data identifiers, timestamps, and raw results were not supplied; QA must obtain them before relying on the run as formal execution evidence.

## Product context and quality objectives

QualityTrack combines a React frontend, FastAPI API, and PostgreSQL data. The bounded engineer journey logs a photo-free defect, records a preliminary cause, starts investigation, and adds an action. System qualification must demonstrate that visible confirmations correspond to persisted records, permissions remain enforced across boundaries, and state/history survive reauthentication and independent retrieval.

The [Stage 2 backlog](../../../../kavia-docs/CodeWiki/Specs/FeatureSpecs/qualitytrack-stage-2-backlog.md) and [Stage 2 UX](../../../../kavia-docs/CodeWiki/Specs/FeatureSpecs/qualitytrack-stage-2-ux.md) supply story, AC, and screen mappings. Personas do not grant permissions. The engineer's downstream journey requires explicit grants; the Quality Manager / Auditor remains an assumed, unvalidated persona with conditional read/export authority.

## Scope and exclusions

Direct browser-to-real-API-to-data coverage targets login, lookups, list/detail retrieval, S1–S4 success and rejection, retained input, cause presence, reviewed revisions, history, multiple actions, session boundaries, and uncertain writes. The [case inventory](system-validation-cases.md) identifies 20 canonical case records and their execution limits.

Supervisor closure, action progression/reopening, overdue work, and auditor PDF review are broader product journeys. Their API behavior has historical backend evidence, but the inspected frontend routes only provide list, capture, cause, investigation, and action-entry pages. Browser acceptance of missing workflows must be recorded as blocked, not replaced by API-only passes. PDF and overdue reconciliation may receive separately labeled supporting integration evidence after approval.

Photo support, analytics, approved rule mode, production identity policy, arbitrary Unicode PDF support, performance qualification, and complete accessibility conformance are not established. Exclusion from the bounded demo does not remove backlog requirements or authorize full-product release. No code, test implementation, environment provisioning, or later-batch execution belongs to this batch.

## Risk model and integration risks

Priority is proposed by QA: high impact with likely or unknown exposure receives high priority. Likelihood describes planning judgment, not measured incident frequency.

| Risk | Impact / likelihood / priority | Proposed coverage | Residual risk and owner |
| --- | --- | --- | --- |
| R1: Missing or invalid API-base configuration prevents startup/login. | High / observed / high | Case 01; verify same-origin API routing before testing. | Deployment configuration remains environment-specific; environment owner. |
| R2: Lookup labels are mistaken for submitted identifiers or stale types remain usable. | High / medium / high | Cases 03, 06; compare selected UUID and captured code/label snapshot. | Taxonomy governance is not validated; product/configuration owner. |
| R3: UI confirmation differs from committed data or history. | High / medium / high | Cases 02, 07, 09, 11, 16, 18; independent retrieval and authorized read-only data checks. | Direct privileged data changes remain outside app guarantees; backend owner. |
| R4: Persona assumptions bypass grants or disclose protected records. | High / unknown / high | Cases 05, 10, 13, 17–19. | Demo grants are not production policy; product/security owners. |
| R5: Stale ETags overwrite concurrent work. | High / medium / high | Case 10; two sessions and renewed explicit review. | Coverage is bounded to inspected transition behavior; backend/frontend owners. |
| R6: Lost write responses lead to blind retry and duplicate data. | High / medium / high | Case 20; isolate response loss and reconcile persisted state. | Additive writes are not idempotent; QA and frontend owners. |
| R7: Reload/logout loses memory-only session or shows a previous user's data. | High / observed / high | Cases 12–13; reauthenticate and inspect protected data boundaries. | Cross-session drafts are not promised; frontend owner. |
| R8: Product photo acceptance conflicts with implemented photo-free scope. | High / observed / high | Case 14 and product disposition. | AC-01b and AC-08c remain unsatisfied for full scope; product owner. |
| R9: Supervisor/auditor journeys cannot be completed in the current UI. | High / source-confirmed / high | Cases 15–19; distinguish missing UI from API evidence. | Full system acceptance remains blocked; product/frontend owners. |
| R10: Calendar and PDF semantics diverge from business expectations. | High / unknown / high | Cases 15–18; fixed plant dates and complete snapshot reconciliation. | Production calendar, layout, and persona policies need approval; product owner. |
| R11: Known dependency findings or unassessed production exposure remain. | High / unknown / high | Review historical dependency report and obtain security disposition. | Functional passing results do not constitute security clearance; security owner. |

## Layered validation approach

Developer-owned unit and component tests support validation of fields, transport, session guards, and workflow state. Existing automated assets are evidence inputs, not new execution results. The existing Playwright critical path intercepts API traffic; it validates browser integration with mocks, not the real API or database.

After approval, QA should execute the proposed high-priority cases on the real stack without success-response stubs. Capture browser outcomes, sanitized HTTP status/body metadata, exact reviewed ETags, and stable record IDs. An independent authenticated GET verifies persisted application state; an authorized read-only database check should reconcile record relationships, revision, actor, and history where available. An unavailable data check is recorded as missing evidence, not silently substituted.

Product-led acceptance should review first-time comprehension and repeat-use recovery for engineer and supervisor participants. Auditor acceptance remains conditional on validating the assumed persona and grants. Exploratory work focuses on lookup races, session transitions, delayed responses, and long evidence. Later regression should combine fast existing tests with real integration checks and a small critical browser suite; no new automation is implemented here.

## Non-functional evaluation

Keyboard access, route focus, field/error association, textual status, small-screen layout, and long content should be observed during real journey execution. Prior Chromium checks are not WCAG conformance, assistive-technology certification, or factory-device acceptance. Supported browser/device coverage still needs an owner decision.

Security evaluation must include denial at API boundaries, protected data isolation after logout, safe error display, and explicit disposition of historical dependency findings. Do not expose development/test services publicly. No GDPR-specific applicability or compliance certification is inferred.

Measure observed timing during execution, but do not invent a latency SLA. Backlog p95 chart/PDF times, capacity, availability, recovery, and WCAG targets are evaluation candidates, not approved thresholds. Load, restore, penetration, and full accessibility qualification need separately approved scope.

## Environment and data

Execution requires a disposable non-production real backend/database, matching deployed frontend/API revisions, migrated schema, synthetic permitted users, active lookups, and documented plant timezone. `VITE_API_BASE_URL` must be a same-origin path ending in `/api/v1`; source inspection rejects an absent or incompatible value. Verify routing reaches the intended backend rather than a mock handler. Node 22 is documented in prior frontend verification; actual runtime versions must be recorded for the later run.

Prepare a fully granted engineer fixture and separate capture-, read-, cause-, transition-, and assignment-denied fixtures. Prepare scoped supervisor and conditional auditor fixtures only after grants are approved. Include valid and retired type IDs, two defects with distinguishable evidence, blank and preliminary causes, multiple actions, and due-yesterday/today/tomorrow examples against a fixed plant-local reference date. Use unique synthetic part markers per run.

Only an environment owner may reset or seed the disposable database. Record created IDs and restore failure-injection configuration after each experiment. Cleanup must not destroy evidence before QA captures results. Never include passwords, tokens, secret settings, or real personal data in reports, screenshots, or HTTP traces.

## Defect management and known observations

Every later defect record should include case ID, build/environment, expected AC-backed behavior, observed result, safe reproduction steps, evidence IDs, impact/severity, delivery priority, owner, root-cause hypothesis versus confirmed cause, origin phase, fix reference, regression coverage, and retest disposition. Critical means security exposure, material corruption, or broad outage; major means a critical journey is blocked; minor means a bounded usability or noncritical discrepancy. Severity is not priority.

| Observation ID | Evidence and classification | Origin phase / proposed disposition |
| --- | --- | --- |
| OBS-01 — non-code configuration defect | The requester reports that login does not render without `VITE_API_BASE_URL`; `ApiClient` explicitly rejects missing configuration. This is an environment/setup defect, not evidence of incorrect application code. Severity is major for the affected deployment; priority is high before execution. | Deployment/setup origin, not a confirmed coding fault. Environment owner supplies valid routing/configuration and QA reruns case 01 after approval. Do not silently add an application default. |
| OBS-02 — lookup presentation | Requester shorthand is “code - label”; source renders code, an em dash, and label. This preserves both values and is not inherently a defect. | UX review only unless an approved presentation criterion is violated; verify identifiers separately. |
| OBS-03 — reload logs out | Requester observation agrees with memory-only session ownership in `AuthProvider`. It is current behavior, not automatically a code bug. | Product/UX expectation decision. Reauthentication must recover saved data; draft persistence is not promised. |
| OBS-04 — photo mismatch | UX/backlog require an optional supported photo, while capture rejects any photo part with 422 `photo_not_supported`; the browser fixture expects no upload control. | Scope/requirements-to-delivery mismatch; precise origin phase requires product/change-history review. Product owner must retain a full-scope blocker or explicitly approve a photo-free demo limitation. |

## Metrics and evidence reporting

Report planned, executed, passed, failed, blocked, and not-run cases separately, by priority, journey, AC, and persona/experience cohort. A blocked case is not a pass, and a mock pass is not a real-stack pass. Record critical journey pass rate, data/history reconciliation failures, permission failures, repeated-run instability, unresolved severity, and accepted residual risks. Case counts alone do not prove quality.

Each execution record needs case and variant IDs, build SHA, actual date/time, environment and browser, fixture grants, sanitized steps/results, record IDs, evidence references, defect links, and reviewer. This batch has 20 designed cases and zero newly executed cases. Historical backend sign-off records two 376-pass runs and 46/46 schema-valid sampled responses; this package neither reruns nor independently requalifies those results.

## Entry, exit, and go/no-go criteria

These are proposed system gates awaiting requester approval, not retrospective approved requirements.

| Gate | Required evidence / decision |
| --- | --- |
| Batch 1 approval | Requester approves strategy, cases, scope limitations, and proposed gates before any execution or publication. |
| Execution entry | Record matching build/environment; establish valid API-base routing, real PostgreSQL connectivity, approved synthetic grants, fixed calendar fixtures, and safe reset/injection permissions. Resolve or explicitly isolate setup blockers. |
| Bounded journey exit | Every applicable high-priority S1–S4 case and denial/recovery variant passes on the real stack with independently retrieved persisted state. Two consecutive critical-journey runs must be stable on the same candidate; any environmental rerun is reported. |
| Data/security gate | No unresolved critical data-integrity, authorization, cross-user disclosure, or false-success defect. Any such finding is no-go and requires remediation and regression evidence. |
| Coverage gate | All 20 cases have explicit dispositions; missing supervisor/auditor UI and photo behavior remain visible as blocked or unmet full-scope acceptance. API-only evidence cannot satisfy a browser case. |
| Residual-risk gate | Product, QA, environment, and security owners explicitly disposition known dependency findings, session UX, missing product scope, backend sign-off deferrals, and unavailable qualification evidence. Named approvals must replace currently unassigned individual owners. |
| Full-product go | Applicable Must ACs, including photo and complete PDF criteria, and accepted persona journeys are demonstrated end to end. Discovery affecting observable outcomes is resolved; release authority separately approves. |
| No-go | Any critical failure, unaccepted major defect, unresolved permission policy, missing critical evidence, or rejection of a required scope waiver prevents the corresponding approval. No approval is inferred from silence. |

The current recommendation is **no-go for full product/system release and pending for bounded-demo qualification**. Historical S1–S4 success supports planning but does not satisfy the proposed exit gate. A bounded photo-free demo may be recommended only after approved execution and explicit acceptance of exclusions; this is not full backlog acceptance.

## Ownership, review, and approval record

QA Lead owns case design, execution evidence, risk reporting, and recommendation. Frontend/backend owners diagnose and fix their respective boundaries with regression tests in later authorized work. The environment owner controls configuration and safe failure injection. Product validates personas, grants, scope decisions, calendar policy, and user acceptance. Security reviews dependency/exposure risk. The requester is the Batch 1 approval authority; production release authority remains unassigned and must be named before release.

Review this package when the requester responds, when a build or grant/calendar policy changes, and after any material failure. Approval status is pending; no approver name, date, waiver, commit, push, or remote verification is claimed. Stop after this batch. Only explicit approval can authorize the requested commit/push and `git ls-remote`; later execution and remediation remain separate batches.

## Sources

The primary product sources are the Stage 2 backlog and UX linked above. Evidence and limitations come from the [backend API readiness sign-off](api-readiness-signoff.md), [frontend verification and audit](../../../frontend/docs/verification-and-audit.md), and the authoritative session attachment supplied by the requester.

Implementation checks used [API client](../../../frontend/src/api/client.ts), [authentication provider](../../../frontend/src/features/auth/AuthProvider.tsx), [capture fields](../../../frontend/src/features/defects/CaptureFields.tsx), [application routes](../../../frontend/src/app/App.tsx), [workflow page](../../../frontend/src/features/defects/WorkflowPage.tsx), [workflow controller](../../../frontend/src/features/defects/useWorkflow.ts), [API entrypoint](../../qualitytrack/main.py), and [mocked browser critical path](../../../frontend/e2e/critical-path.spec.ts).
