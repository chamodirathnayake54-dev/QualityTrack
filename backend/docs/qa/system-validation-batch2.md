# QA-07 QualityTrack System Validation — Batch 2

## Ancestry and candidate

First check: `git merge-base --is-ancestor e0a24dc HEAD` exited **0**.
The starting worktree was clean, at
`8e3abfaca941f1ddfea2f6f866144ae22faada31`. This report evaluates the
uncommitted Batch 2 proposal based on that commit, not a new release commit.
No commit, push, or remote verification was performed.

The authoritative Batch 2 request authorized real-stack execution and minimal
confirmed fixes. Batch 1 is retained as historical planning, not current
execution evidence.

## Environment and evidence

Final execution: **2026-10-22 09:28:46–09:29:08 UTC**. The runner returned 0;
Playwright reported **13 groups passed in 20.2 seconds**, with no test retries.
The two S1–S4 critical journeys passed consecutively on the same candidate.

| Component | Actual environment |
| --- | --- |
| Browser | Real headless Chromium, Playwright 1.64.1 matching revision 1248; downloaded Chrome 156.0.8078.4 |
| Frontend | Real Vite/React application on loopback 4173; separate unconfigured instance on 4174 |
| Backend | Real FastAPI/Uvicorn on loopback 8000; declared pinned dependencies |
| Runtime | Node 22.23.4; Python 3.11.14 |
| Database | PostgreSQL 16.15; migrated private disposable cluster and Unix socket |
| Calendar | `Etc/UTC`; calendar inclusion reference date 2026-10-22 |
| Identity | Synthetic seed users plus explicit denial fixtures; random per-user passwords held in process memory |
| Authority | Seed grants plus isolated supervisor `type.retire` grant; exact actual grants exported |

The test-only database connection used the isolated cluster administrator. API
authorization was real; deployment database-role restrictions were **not**
qualified by this run. This is not production identity, persona approval, or
deployment acceptance.

Evidence retained in this repository:

- [Runtime and database reconciliation](batch2-evidence/runtime.json).
- [Final browser runner output](batch2-evidence/browser-run.txt).
- [Case observations and sanitized HTTP metadata](batch2-evidence/browser.json).
- [Independent synthetic PostgreSQL rows and grants](batch2-evidence/database.json).
- [Defect log](system-defect-log.md).
- [Critical-path regression set](system-critical-regression.md).

No successful API responses were fabricated. The only browser intercepts
delayed an actual read or fetched the actual action response and then dropped
delivery. PostgreSQL evidence was read independently after browser execution.
The runner asserted both critical journeys' parent values, cause text/actor,
action relationships/fields, exact history timestamp/actor/revision, and the
single lost-response action ID against database rows.

No `.env` file was read or written. No plaintext passwords, password hashes,
tokens, connection settings, login bodies, traces, or videos were retained in
the evidence. Temporary database files, including synthetic password hashes,
were removed when the runner stopped its services and cluster.

## Results against the original 20 IDs

Original IDs remain the traceability denominator: **14 passed, 1 failed
requirement acceptance, 5 not executable in this release**. All 15
release-executable case IDs were exercised, including photo-gap observation.
The 13 automated groups are not 13 canonical cases: some combine related
assertions, one repeats the critical journey, and one supplies API-only
diagnostics for missing browser journeys.

| Case | Disposition | Actual observation and evidence |
| --- | --- | --- |
| 01 | Passed | Unconfigured frontend showed “Configuration required”; configured frontend authenticated and loaded real lookups. Setup example corrected; see QT-SYS-01. |
| 02 | Passed, twice consecutively | Browser capture → saved cause → reviewed investigation → Open action; second In Progress action appended. Confirmations matched independent API reads and PostgreSQL. |
| 03 | Passed within 02; standalone run removed | All three selected options showed code/em dash/label; returned and independently retrieved stable IDs and capture-time labels matched selections. |
| 04 | Passed | Each required capture field omitted independently, including severity; quantities 0, -1, 1.5 rejected without capture. Correctable input retained. Critical/Major/Minor captures with quantity 1 succeeded. |
| 05 | Passed | Capture-denied fixture saw permission feedback; direct authenticated multipart POST returned 403; authorized reader found no matching defect. |
| 06 | Passed | Selected type retired through real API with test-only custodian grant and type ETag `"1"`; stale capture returned 409 and created nothing. New choices excluded it; historical snapshot remained unchanged. |
| 07 | Passed within both journeys | Empty/whitespace causes rejected; no cause persisted. One trimmed preliminary cause persisted and satisfied the investigation presence gate without five answers. |
| 08 | Passed | Entered but unsaved cause did not satisfy gate; transition returned 409; status remained Open with no history event. |
| 09 | Passed within both journeys | Visible transition showed old/new status, actor and plant-zone time. One revision-3 event survived reload/reauthentication; API timestamp and database instant reconciled exactly. |
| 10 | Passed | Concurrent real cause advanced revision; browser sent exact stale `If-Match: "2"`, received 412, refreshed context and cleared review without replay. Separate transition-denied UI request returned 403; no event persisted. |
| 11 | Passed | Each required action field rejected independently without writes. Open and In Progress actions retained their distinct description/owner/date/status under the same parent after revisit. |
| 12 | Passed within both journeys | Reload required sign-in, as designed. Saved cause, history, and actions survived reauthentication. Unsaved draft persistence is not promised. |
| 13 | Passed | Delayed real engineer read released after logout/denied-reader login did not restore prior identity or show the prior part number. New record read and mutation were denied. |
| 14 | **Failed requirement acceptance** | Browser has no upload control and says photos are unavailable. Multipart photo returned 422 `photo_not_supported` with no write. Defensive rejection assertions passed, but optional-photo AC did not; QT-SYS-02 remains open. |
| 15 | **Not executable in this release** | No overdue dashboard route. Supporting API checks included past-due incomplete work and excluded today, tomorrow, and completed past-due work. Not a browser or DST acceptance pass. |
| 16 | **Not executable in this release** | No action progression/closure/reopening UI. API rejected incomplete closure and completion without notes; valid completion/closure persisted. Closed-parent action reopening returned documented 503; explicit parent reopening to Under Investigation then action reopening succeeded with retained notes/reason/history. |
| 17 | **Not executable in this release** | Missing supervisor workflow/export controls. A separately restricted supervisor fixture received 403 for workflow/export; this does not satisfy absent UI acceptance. |
| 18 | **Not executable in this release** | No browser PDF/export journey, no validated auditor persona, and no photo evidence. Real photo-free PDF endpoint returned 200 and a PDF signature for the synthetic record. Complete visual/content reconciliation was not performed. |
| 19 | **Not executable in this release** | No complete auditor review/export journey or persona approval. API denied record/PDF without read, PDF without export, and capture/cause/action mutations for the read/export-only fixture. |
| 20 | Passed | Actual action committed, response delivery intentionally lost, UI warned unconfirmed and refreshed the associated action; one POST and exactly one independently retrieved/database action. |

The original canonical JSON records outside this Git worktree were not edited.
They remain design artifacts, not a second execution-results store.

## Lost-response experiment

Case 20 sent one real S4 action POST. `route.fetch()` received the real 201
after backend processing; only delivery to the browser was aborted. The UI
displayed:

> The result is unconfirmed. Check the refreshed record before deliberately submitting again.

The associated action became visible after the automatic read refresh; the
entered description stayed in the draft. The browser did not automatically
retry the POST. Independent API retrieval and PostgreSQL found exactly one
action for that isolated parent, ID
`f76c946c-0cab-44e8-9fe0-a32cdb339eb6`. Delivery was restored and normal GET
succeeded. This proves the observed one-attempt recovery, **not** general
idempotency or safety of a subsequent deliberate retry.

## Case pruning

Remove case 03 as an **independent critical-path execution**, not as historical
traceability. Its entire identity/snapshot check is now asserted during both
case-02 captures, using the same real choices and independent retrieval.
Repeating a standalone capture with identical identity checks adds no distinct
risk coverage. Preserve case 03's original ID and source record; report its
coverage as consolidated, not as an extra independently executed scenario.

## Failures classified before remediation

Earlier attempts are not final passing evidence:

- Missing backend/frontend dependencies and Python 3.11/Node 22 were required
  environment prerequisites. Installed declared packages and supported
  runtimes outside the worktree; dependency declarations were not changed.
- The preinstalled Chromium revision 1234 did not match Playwright's required
  1248. The first run had 12 browser launch failures and one API-only group
  pass. Matching browser installation resolved this provisioning issue.
- A harness used full navigations after login, correctly losing the memory-only
  session. It was interrupted after diagnosis; changed only harness navigation.
- A subsequent run had 11 groups pass and two harness failures: attempting a
  new capture on the existing confirmation view and omitting retirement's
  required empty JSON body. Both were corrected to the real contracts.
- Extending reopening diagnostics produced 12 passes and one incorrect harness
  expectation for Closed → Open. Source allows Closed → Under Investigation;
  the test was corrected, not product behavior.
- A new documentation regression initially used an unsuitable frontend
  filesystem-import approach. Removed it and added the passing existing-toolchain
  Python filesystem test instead; no Vite protection or dependencies changed.
- Worker-restart evidence overwriting was fixed in the new harness before final
  evidence collection. Evidence now appends after every test and resets once
  per complete run.

Final evidence replaces those development attempts; their limitations and
classifications remain recorded here rather than counting failed setup attempts
as application defects.

## Changes and verification

Minimal product-facing remedy: `.env.example` now supplies
`VITE_API_BASE_URL=/api/v1`; README explains applying it before startup and that
the application intentionally has no implicit default. `ApiClient` validation
was preserved. Regression: `test_frontend_configuration.py`; real case 01 also
proves missing-setting failure and valid-setting recovery.

Added an opt-in real-stack runner and suite, isolated from the existing mocked
Playwright suite. No confirmed application-code defect required a production
logic change. Photo and absent screens remain visible scope gaps rather than
being masked by weakened assertions or implemented as broad new features.

| Check | Result |
| --- | --- |
| Final real-stack suite | 13 groups passed; two consecutive critical journeys |
| Independent PostgreSQL reconciliation | Both journeys and case 20 passed |
| Frontend Vitest | 84 tests passed |
| Frontend production build | TypeScript and Vite passed |
| Setup-documentation regression | 1 passed |
| New Python files: Ruff / Black | Passed |
| Diff whitespace | Passed before report publication; checked again at completion |

The Python test emits an upstream Starlette/AnyIO deprecation warning; it does
not fail the test and was not suppressed. No broad backend requalification,
dependency-security clearance, WCAG, performance, DST, browser/device matrix,
PDF visual acceptance, or production-policy qualification is claimed.

## Recommendation and approval boundary

**Bounded photo-free engineer journey: demonstrated, conditional on accepting
the explicit exclusions. Full-product release: no-go.** Open P1 scope gaps
remain for photos and supervisor/auditor screens. Product must disposition
these gaps and validate auditor persona/grants; QA cannot infer a waiver.

This proposal stops for requester review. It does not authorize commit or push.
After explicit approval, the requested publication step is commit, push, and
`git ls-remote`; none has been performed here.
