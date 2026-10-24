# QualityTrack bug and improvement report

## Summary table

| Item | Severity | Review status | Outcome |
| --- | --- | --- | --- |
| UX-01 | Low | Fixed | Cause success has an investigation next-step link. |
| UX-02 | Low | Fixed | UI checks all cause pages and asks before recording a normalized duplicate; API duplicates remain possible by design. |
| UX-03 | Low | Fixed | Heading and navigation both use “Investigation”. |
| UX-04 | Info | Fixed | Username disables capitalization, correction and spellcheck. |
| UX-05 | Low | Fixed | Investigation success is explicit; repeated transition is disabled. |
| UX-06 | Low | Fixed | Capture and filter options render labels rather than internal codes. |
| UX-07 | Info | Confirmed | Session remains memory-only, now explained on login; not a security defect. |
| UX-08 | Low | Fixed | Journey includes Back to defect and post-save onward links. |
| UX-09 | Medium | Fixed | List has a wider container, scroll region, minimum column widths and no-wrap badges. |
| UX-10 | Low | Fixed | Mutual date limits and immediate reversed-range error exist. Paired dates are also required by the API. |
| UX-11 | Low | Fixed | First/Previous/Next and current-page count are always rendered. |
| UX-12 | Medium | Fixed | Approved fallback hides inaccessible lookup selectors and displays historical labels; it does not grant lookup access. |
| UX-13 | Low | Fixed | Plain filter wording and readable signed-in plant timezone are shown. |
| UX-14 | Medium | Fixed | Write routes redirect unauthorized readers to the summary; no auditor workflow forms. |
| UX-15 | Medium | Fixed | Both cause lists show author and plant-local timestamp. |
| UX-16 | Medium | Fixed | Action choices require owner/supervisor authority and explicit grants. |
| UX-17 | Low | Confirmed | Actions are cards, but history is expanded and Close defect remains below all collections. |
| UX-18 | Medium | Confirmed | PDF exposes technical fields/UUIDs and ISO-style times; timezone conversion already exists. |
| UX-19 | Low | Confirmed | Closed defects still offer cause input. Claimed server refusal is not supported by current service code; see NEW-01. |
| GAP-01 | Medium | Fixed | Grant-aware audit PDF export exists on summary and workflow pages. |
| GAP-02 | Medium | Fixed | Supervisor defect/action transition controls exist. |
| GAP-03 | Info | Confirmed | Identity has no role field; header shows display name and plant time. |
| OPS-01 | Info | Fixed | PostgreSQL helper checks standard macOS locations and retains Linux behavior. |
| OPS-02 | Low | Confirmed | No lint script; shell Node is 18.20.8. README already requires Node 22. |
| OPS-03 | Info | Needs manual check | Historical lost work/platform instability cannot be reconstructed. This session did observe Git metadata errors. |
| OPS-04 | Info | Needs manual check | Local Mac credential/Keychain behavior is outside this checkout. |
| QA-01 | Info | Needs manual check | Historical blocked real-stack automation remains an acceptance gap; not rerun here. |
| REG-01 | High | Fixed | History actors and action owners are rendered again. |
| REG-02 | Medium | Fixed | Existing recorded measures meet thresholds; not remeasured in this review. |
| Manual-log dependency audit note | Security risk | Needs manual check | Existing audit documentation records unresolved findings; no fresh audit or exploitability assessment. |
| NEW-01 | Medium | Confirmed | Cause service accepts a Closed parent instead of enforcing the expected lifecycle restriction. |
| NEW-02 | Low | Confirmed | Closed defects offer Add corrective action although the server rejects it. |
| NEW-03 | Low | Confirmed | Supervisor can be offered Reopen action on a Closed parent although the API returns policy unavailable. |
| NEW-04 | Low | Confirmed | Summary heading levels invert inside action cards and skip a level for defect transition controls. |
| NEW-05 | Medium | Confirmed | Permission/lifecycle policy remains embedded in presentation components, risking the Stage 6 boundary. |

## Scope and evidence standard

Reviewed on 24 October 2026 against develop commit `3e55d5595b93b75b2670fbcb2985b8858f6d5c4b`, which merges DEV-11. The requested PR branch is `docs/qa-bug-report-20261024`, targeting `develop`. The initial commands were `git branch --show-current` and `git log --oneline -3`; they showed `develop`, `3e55d55`, `40734eb` and `48d1395`. `git ls-remote --heads origin develop` independently returned the same full develop SHA.

“Confirmed” means demonstrated by source or the explicitly described command, not necessarily reproduced in a browser. “Fixed” means the original symptom is addressed in the reviewed implementation; it is not a fresh cross-browser acceptance signoff. “Needs manual check” is used where historical, device, platform or live-environment behavior cannot be established here. No item is labeled Not reproducible merely because no browser was run.

Paths and one-based line ranges below are relative to the QualityTrack repository and pinned to the reviewed commit. Short inline excerpts are literal evidence. The authoritative manual log supplies expected behavior, not proof of current implementation. Only this new document is authorized for editing; indexes, source, tests and the two measurement documents are intentionally unchanged.

## Manual-log review details

### Engineer journey and capture

UX-01, UX-05 and UX-08 are Fixed. `useWorkflow`, `frontend/src/features/defects/useWorkflow.ts:136-141`, sets `setSucceeded(true)`, supplies distinct success messages, clears the saved draft and refreshes. `WorkflowPage`, `frontend/src/features/defects/WorkflowPage.tsx:73-81`, renders a success link to investigation, action or the defect summary. Lines 82-98 render `Back to defect`; lines 117-123 disable the investigation checkbox and button when `w.investigationReached`. The latter is prepared in `useWorkflow.ts:161`. Staying on the form is deliberate; a separate completion screen is not necessary to provide the requested onward guidance. `workflow.test.tsx:190-216` and `:282-311` assert cause success/onward links and investigation feedback/disabled controls.

UX-02 is Fixed at the UI warning level requested by the log, not as an API uniqueness rule. `useWorkflow.submit`, `useWorkflow.ts:111-123`, normalizes whitespace/case, follows every `next_cursor`, and uses `window.confirm('This cause is already recorded. Record it again?')`. `workflow.test.tsx:163-188` covers a duplicate on a later page, cancellation and explicit confirmation. `backend/qualitytrack/workflow.py:81-90` remains append-only without deduplication. API callers or concurrent clients can still append duplicates; a hard prohibition would require a separate policy decision. This is not evidence of an unguarded double-click: `useWorkflow.ts:95-107` uses a synchronous lock and aggregate mutation guard, and `frontend/src/ui/Button.tsx:7` uses `disabled={disabled || pending}`.

UX-03 is Fixed: `WorkflowPage.tsx:57` chooses `'Investigation'`; lines 64-65 use the same label in navigation. UX-04 is Fixed: `LoginPage`, `frontend/src/features/auth/LoginPage.tsx:48-50`, sets `autoCapitalize="none" autoCorrect="off" spellCheck={false}`. Backend case-sensitive credential comparison remains intentional in `issue_token`, `backend/qualitytrack/security.py:58-66`, with `User.username == username`; the fix does not silently change login semantics.

UX-06 is Fixed. `CaptureFields`, `frontend/src/features/defects/CaptureFields.tsx:16-20`, renders `{choice.label}`. `DefectListPage`, `frontend/src/features/defects/DefectListPage.tsx:37-47`, renders `{item.label}`. Real plant label quality still requires representative data, but internal codes are not appended by these option renderers.

UX-07 is Confirmed as a deliberate session property, not a request to persist tokens. `AuthProvider`, `frontend/src/features/auth/AuthProvider.tsx:19-30`, starts with null identity and clears session/query state on logout; lines 52-55 establish only an in-memory client session and expiry timer. `LoginPage.tsx:43` now states, “For your security you are signed out if you refresh this page.” No session-storage change is suggested for this review.

### Defect list, filtering and pagination

UX-09 is Fixed in source. `frontend/src/styles/tokens.css:28` restores normal word breaking; lines 39-41 set minimum table-cell widths; lines 55-57 retain the form default but widen pages containing defect pagination. `DataTable`, `frontend/src/ui/DataTable.tsx:9-10`, uses a focusable `overflow-x-auto` region and `min-w-[72rem]` table. `StatusBadge`, `frontend/src/ui/StatusBadge.tsx:18`, uses `whitespace-nowrap`. These address the narrow-table cause; Safari/device and extreme saved-text layouts still need manual confirmation.

UX-10 is Fixed within the current API contract. `DefectListPage.tsx:21-22` derives immediate reversed-range feedback; lines 49-52 bind Start `max` and End `min` to the opposite input. `validateFilters`, `frontend/src/features/defects/validation.ts:45-48`, requires a valid paired range. `Filters._date_pair`, `backend/qualitytrack/schemas.py:167-173`, also rejects a missing partner; therefore one-sided ranges are not an existing supported API feature. `list_defects`, `backend/qualitytrack/defects.py:129-135`, uses independent plant-local midnight boundaries, with exclusive next-day end, rather than adding a fixed UTC day.

UX-11 is Fixed. `DefectListPage.tsx:83-88` always renders `Showing ... defects`, First, Previous and Next, disabling unavailable actions. `useDefectList`, `frontend/src/features/defects/useDefectList.ts:17-18,35-54`, stores an identity-bound cursor stack in navigation state and pops it for Previous. The count is current-page size, not total matching records or a snapshot guarantee. `defects.test.tsx:93-103,116-140` covers empty-state controls, cursor encoding, Previous and filter reset.

UX-12 is Fixed by the manual log's allowed hide-and-friendly-label fallback, not by broadening grants. `choices`, `backend/qualitytrack/main.py:208-209`, still calls `require(caller, "defect.capture")`. `DefectListPage.tsx:37-47` returns a selector only when `lookup.isSuccess`; table columns at lines 70-73 use `label_at_capture`. `defects.test.tsx:73-88` explicitly checks supervisor/auditor denial responses and URL filter IDs without unavailable text or visible raw IDs. A hidden filter can remain active from a shared URL until Clear filters is used: `useDefectList.ts:21-22` preserves supported URL parameters. This is a residual usability caveat, not proof that readers now have interactive access to those lookups.

UX-13 is Fixed. `DefectListPage.tsx:30,56` says “Showing defects that match all filters” and explains inclusive dates using `plantTimeLabel(controller.zone)`. `frontend/src/features/defects/plantTime.ts:2-5` maps `Etc/UTC` to readable UTC rather than printing internal zone syntax.

### Permissions, summary and export

GAP-02 and UX-14 are Fixed. `RecordEntry`, `frontend/src/app/App.tsx:45-48`, opens `DefectSummaryPage`. `WorkflowRoute`, lines 51-58, checks the operation grant before rendering an editor and redirects unauthorized readers. `useDefectSummary`, `frontend/src/features/defects/useTransition.ts:148-157`, prepares grant-filtered links and status-specific transition choices. The summary renders transition controls at `DefectSummaryPage.tsx:48-50,95-96`. `supervisor.test.tsx:147-160` covers close/reopen with reviewed parent revisions; lines 180-187 cover auditor routes with no forms or writes. Server enforcement remains mandatory: `require`, `backend/qualitytrack/security.py:36-39`, rejects absent grants, and `workflow.py:28-39` reloads the principal around the parent operation.

UX-15 is Fixed. `CauseList`, `frontend/src/features/defects/WorkflowViews.tsx:18-23`, renders `Recorded by` using `cause.recorded_by_ref` and `cause.recorded_at`. `RecordAttribution`, lines 8-15, formats with the supplied plant timezone. It is consumed by `WorkflowPage.tsx:105` and `DefectSummaryPage.tsx:85`; `supervisor.test.tsx:111-121` verifies multiple authors in plant time on both routes.

UX-16 is Fixed. `transitionChoices`, `useTransition.ts:18-37`, requires explicit permissions and owner/supervisor authority, using the same explicit demo supervisor binding as the backend rather than guessing a role from display name. `ActionCard`, `DefectSummaryPage.tsx:48-51`, renders only those choices and otherwise shows owner guidance. `supervisor.test.tsx:91-109` checks owner/supervisor completion and the absence of forms, checkbox, buttons and writes for an engineer on a supervisor-owned action. Backend `_owner_authority`, `workflow.py:159-162`, retains final enforcement. The guidance is generic: an owner without the grant still cannot act, and reopening remains supervisor-only.

UX-17 is Confirmed as remaining optional polish, partly improved. `ActionCard`, `DefectSummaryPage.tsx:42-47`, already supplies cards and short status/due/owner lines, but always renders the history collection without a disclosure. `DefectSummaryPage.tsx:84-96` places all causes, defect history and actions before the defect transition controls. With many actions the supervisor still reaches Close defect only after the long content. Expected behavior is a readily reachable close control and initially collapsed per-action history. Reproduce with multiple populated actions as supervisor; suggested follow-up is a top summary action area in `DefectSummaryPage` and native disclosure around action history in `ActionCard`, preserving reviewed-context validation.

GAP-01 is Fixed. `AuditExport`, `frontend/src/features/defects/AuditExport.tsx:7-15`, hides the panel when not visible and exposes progress and the photo-free note. `useAuditExport`, `frontend/src/features/defects/useAuditExport.ts:44-48,58-62`, requests `${record.base}/audit.pdf`, saves a sanitized filename and derives visibility from `defect.export`. `audit.test.tsx:65-110` covers routes, grant denial, pending state, one request and error feedback. The backend `audit` route, `backend/qualitytrack/reporting_routes.py:89-107`, delegates to `export_record`; `backend/qualitytrack/evidence.py:55-59,289-303` checks both read/export grants and reauthorizes after rendering.

UX-18 is Confirmed, with a correction to the reported timezone diagnosis. `load_snapshot`, `evidence.py:88-100`, emits raw schema keys; its excerpt `(f"{key}.{name}", str(item))` includes captured lookup IDs/codes. Lines 139-152 include cause/action UUIDs. `_display`, lines 62-67, already uses `value.astimezone(zone).isoformat()` with the plant-zone key: timestamps are local-zone ISO strings, not necessarily unconverted UTC. `PdfRenderer.render_complete`, lines 242-247, also prints the defect UUID in the report header. Expected behavior is friendly field labels and readable plant-local dates while retaining actor usernames and full evidence. Reproduce by exporting a populated defect and inspecting details and history. Suggested fix is explicit presentation mappings in `load_snapshot` and a human-readable formatter in `_display`, with wording/timezone tests; do not remove evidence rows or snapshot/authorization safeguards.

UX-19 is Confirmed in the UI. `WorkflowPage.tsx:108-111` renders the cause form whenever `kind === 'causes'`; `busy` at line 59 only covers mutation/fetch activity. `useDefectSummary` links are grant-only at `useTransition.ts:149-153`, so a permitted engineer can navigate there from a Closed summary. Expected behavior is no cause editor on Closed records and a short explanation. Reproduce as engineer on a Closed defect, following Record cause or opening `/defects/{id}/causes`. Suggested fix is to prepare cause eligibility and a Closed explanation in `useWorkflow`, consume them in `WorkflowPage`, and remove the ineligible summary link in `useDefectSummary`. The log's assertion that the server refuses is contradicted by the current service path; NEW-01 documents that independently.

### Regressions, tooling and process

REG-01 is Fixed. `EventList`, `WorkflowViews.tsx:32-37`, uses `label="Changed by" actor={entry.actor_ref}`; `AssociatedActionList`, lines 49-52, renders `Owner: {action.owner_ref}`. The summary also shows the owner at `DefectSummaryPage.tsx:44`. `workflow.test.tsx:82-109` asserts readable actors/owners and hidden record UUIDs.

REG-02 is Fixed according to existing recorded measurements only. [Component reuse](component-reuse.md), line 57, records **18/33 = 54.55%**, above 40%; [UX alignment](ux-alignment.md), line 16, records **36/40 = 90%**, at the threshold. These files were read but neither remeasured nor edited. They are manual static metrics under the existing method, not independent proof that all Stage 6 criteria or acceptance tests pass.

OPS-01 is Fixed in source. `_postgres_bin`, `backend/scripts/demo_db.py:23-34`, retains Linux `PG_BIN` and checks PostgreSQL.app-style installer and Intel/Apple Silicon Homebrew locations on macOS. Its `all(os.access(...))` requires executable `initdb` and `pg_ctl`. No Mac command was run here.

OPS-02 is Confirmed for lint and the current shell, but Node documentation is already present. `frontend/package.json:6-12` defines dev/build/test/E2E scripts without lint; tracked-file search found no lint configuration. Fresh `node --version` returned `v18.20.8`. `frontend/README.md:8` already specifies Node 22 LTS; `verification-and-audit.md:120-124` records Playwright's Node 20+ requirement and prior isolated Node 22 execution. Suggested follow-up is a separately scoped ESLint setup and supported CI/runtime pinning, not claiming an unavailable lint pass.

GAP-03 is Confirmed as a contract/design limitation. `Identity`, `frontend/src/api/contracts.ts:2-8`, and `MeView`, `backend/qualitytrack/schemas.py:75-82`, have no role field. `AppShell`, `App.tsx:33-35`, shows display name and plant time. Expected role labeling needs an explicit contract decision; permissions should not be translated into an invented role.

QA-01 Needs manual check. `verification-and-audit.md:38-42,63-74` records blocked historical real-stack verification, distinct from mocked browser passes. `frontend/playwright.real.config.ts:4-13` targets the real-stack suite with localhost 4173; `frontend/e2e/real-stack.spec.ts:6,92,101` also needs QA07 password/evidence configuration and visits 4174. Prepared services and separate evidence-output authorization are needed before a fresh live run. No historical blocked check is closed by this source review.

OPS-03 Needs manual check for the original platform events. In this session, `git fetch origin develop` failed with `cannot open '.git/FETCH_HEAD': No such file or directory`; branch creation reported inability to create `.git/logs/HEAD`, then `git branch --show-current` confirmed the requested branch. Remote develop was independently checked as described above. This does not prove silent switching or lost work. OPS-04 also Needs manual check: the review has no access to the requester's Mac Keychain, revoked tokens or historical authentication failures. Preserve small commits and remote-ref verification; never publish credentials.

The manual-log npm audit note Needs manual check for current counts. `frontend/docs/verification-and-audit.md:147-169,210-217` records unresolved findings, including a later historical total of 12 affected package entries and two moderate production entries, which differs from the manual log's eight. These are dated audit results, not a fresh count or proof of exploitability. No audit fix, dependency migration or force operation was performed. Existing functional test passes do not establish security clearance.

## New findings

### NEW-01 — Closed-parent cause writes are accepted by the service

**Severity: Medium. Where:** `add_cause`, `backend/qualitytrack/workflow.py:81-90`, reached by `workflow_routes.py:65-81`. This is the server-side counterpart of UX-19, not a second UI symptom.

**What happens:** after permission, existence and lock checks, the function unconditionally inserts a cause and increments the parent revision:

```python
parent, caller = _parent(session, caller, defect_id, "cause.create", True)
row = RcaEntry(
    defect_id=parent.id, cause_text=body.text, recorded_by_ref=caller.ref
)
session.add(row)
parent.revision += 1
session.flush()
```

`RcaEntry`, `backend/qualitytrack/models.py:209-224`, has content/FK constraints, not a parent-status guard. A fresh no-database probe patched `_parent` to return an authorized Closed parent at revision 7 and mocked `cause_view`; `add_cause` queued an insert, flushed and returned revision 8. This proves service behavior, not live PostgreSQL commit behavior.

**Expected and reproduction:** under the lifecycle expectation supplied with UX-19, an authorized POST to `/api/v1/defects/{closed-id}/causes` should reject the write without changing evidence/revision. The isolated reproduction is a Closed parent, caller with `cause.create`, valid `CauseCreate(text=...)` and a mock session; invoke `add_cause`.

**Suggested fix:** after `_parent(..., True)` in `add_cause`, reject Closed with a 409 lifecycle failure before constructing `RcaEntry`; add service and PostgreSQL tests for no insert/revision change. Confirm that this is the intended backend policy before implementation, because the current code does not implement the log's assumed refusal. Pair it with the UX-19 presentation correction.

### NEW-02 — Closed defects still offer corrective-action creation

**Severity: Low. Where:** `WorkflowPage`, `frontend/src/features/defects/WorkflowPage.tsx:126-139`; `useWorkflow`, `useWorkflow.ts:49-55,94-106`; `useDefectSummary`, `useTransition.ts:149-153`.

**What happens:** a Closed record with `action.assign` still has the grant-based Add corrective action link. If assignable owners load, the form and Add action button are available because eligibility is based on `busy` and `ownerReady`, not parent status. The literal button gate is `disabled={busy || !ownerReady}`. In contrast, `add_action`, `backend/qualitytrack/workflow.py:198-202`, explicitly raises `Failure(409, "defect_closed", "Defect is closed")`.

**Expected and reproduction:** as an engineer or supervisor, open a Closed defect, follow Add corrective action, fill valid fields and submit; the offered operation is refused. Closed records should show saved actions and a clear explanation rather than an impossible creation form.

**Suggested fix:** prepare `canAddAction` from grant and current parent lifecycle in `useWorkflow`; use it to omit the form and owner request, and filter the summary link in `useDefectSummary`. Keep server checks and cover direct Closed-route access in component tests.

### NEW-03 — Reopen action is offered while its parent is Closed

**Severity: Low. Where:** `transitionChoices` and `useActionSummary`, `frontend/src/features/defects/useTransition.ts:18-37,110-131`; `transition_action`, `backend/qualitytrack/workflow.py:286-287`.

**What happens:** the choice builder receives action status, permissions and actor/owner, but not parent status. Its excerpt `status === 'Complete' ? [{ label: 'Reopen action', ... }] : []` therefore offers a permitted supervisor reopening even on a Closed defect. The server explicitly returns `503 policy_unavailable` for `reopening and parent.status == "Closed"`.

**Expected and reproduction:** as supervisor, open a Closed defect with a Complete action. Reopen action is offered; valid notes/review still encounter the closed-parent policy refusal. The page should explain that the defect must first be reopened rather than implying an infrastructure outage.

**Suggested fix:** pass parent lifecycle to the controller choice builder from `useActionSummary`; withhold action reopening and expose clear guidance while the parent is Closed. Do not change the settled backend policy as part of presentation work. Add a Closed-parent choice/component regression test.

### NEW-04 — Summary heading hierarchy is inconsistent

**Severity: Low. Where:** `ActionCard` and `TransitionControl`, `frontend/src/features/defects/DefectSummaryPage.tsx:14,43-46,95-96`; `WorkflowCollection`, `WorkflowViews.tsx:76`.

**What happens:** an action's H3 title is followed by its history collection's unconditional H2, making nested history appear at a higher level. Defect transition sections render H3 directly under the H1 page without a wrapping H2 section. Literal evidence is `<h3>{action.description}</h3>`, `<WorkflowCollection title="Action history" ...>` and `<h2>{title}</h2>` in the collection.

**Expected and reproduction:** load a summary with actions and a supervisor transition, then inspect headings in DOM order or a screen-reader heading list. Headings should reflect nesting, not invert or skip levels. This source defect is confirmed; user impact was not screen-reader tested.

**Suggested fix:** give `WorkflowCollection` a presentation-only heading-level option for nested use, adjust action-card history accordingly, and group defect transitions under an H2. Add heading-structure assertions and perform keyboard/screen-reader confirmation without removing labelled regions.

### NEW-05 — Stage 6 presentation boundary still contains policy

**Severity: Medium. Where:** `WorkflowPage`, `frontend/src/features/defects/WorkflowPage.tsx:59-67,85-87`; `DefectListPage`, `DefectListPage.tsx:17-22`; `ReadFeedback`, `ReadFeedback.tsx:10-17`.

**What happens:** the workflow component selects permission names and filters visible journey steps using `w.identity?.permissions.includes(...)`. The list component derives invalid date-range feedback itself; `ReadFeedback` identifies a 403 and decides which permission explanation/retry behavior applies. These are concrete rule decisions within TSX presentation, even though saving, most validation and action authority have correctly moved to hooks. The strongest policy example is:

```tsx
steps.filter((step) => w.identity?.permissions.includes(
  step.key === 'causes' ? 'cause.create' : step.key === 'investigation' ? 'defect.investigate' : 'action.assign',
))
```

**Expected and reproduction:** source-inspect these components against the strict “no business logic in UI components” measure. Hook-prepared visibility, validation and retry state should be consumed by presentation rather than recomputed there. Whether date-error derivation is considered purely presentation must be agreed in the Stage 6 rubric; permission policy is the clearer boundary risk.

**Suggested fix:** return prepared journey steps from `useWorkflow`, move list date draft/validation into `useDefectList`, and supply retry/message decisions from the relevant controller to `ReadFeedback`. Keep router authorization and server guards intact. Add controller tests rather than changing component-count methodology.

## Stage 6 quality-measure review

| Measure | Evidence and review outcome |
| --- | --- |
| Component reuse at least 40% | Existing `component-reuse.md:57,104-111` reports 54.55%. Read only; no recount, denominator change or new score. |
| UX alignment at least 90% | Existing `ux-alignment.md:16-31,82-102` reports 90% under its S1–S4 rubric. It is not summary-page, full acceptance or accessibility certification. |
| No business logic in UI components | Most writes/validation/authority live in `useCapture`, `useWorkflow`, `useTransition` and `useAuditExport`; NEW-05 identifies remaining policy in presentation. Do not assert blanket compliance. |
| Loading, error and empty states | `ReadFeedback.tsx:9-23`, `WorkflowViews.tsx:78-83`, `DefectListPage.tsx:59-80` and `LogDefectPage.tsx:21-38` provide distinct states. Owner loading/empty/403/503 and collection errors are covered in `workflow.test.tsx:112-159`; Closed lifecycle guidance remains incomplete. |
| At least two validation rules per form | Login checks nonblank username/password (`LoginPage.tsx:25-26`). Capture validates part and quantity plus choices/severity (`validation.ts:17-31`). Cause checks nonblank and 2000-code-point maximum (`workflowValidation.ts:11-14`). Action validates description, owner, real calendar date, status and conditional notes (`workflowValidation.ts:18-35`). Investigation checks strong parent revision and current explicit review (`useWorkflow.ts:100-102`). Summary transitions require reviewed current context/revision and readiness (`useTransition.ts:58-72`); completion/reopen notes additionally require 1–2000 characters. A confirmation-only Close/Reopen defect form has no free-text field: review and revision/readiness are safety checks, not two independent input-field constraints. If Stage 6 requires two field validations even there, that requirement needs clarification rather than inventing irrelevant inputs. |

Accessibility positives include associated labels/hints/errors (`frontend/src/ui/Field.tsx:10-16`), focusable error summaries (`ErrorSummary.tsx:6-13`), keyboard-scrollable semantic tables (`DataTable.tsx:9-14`) and skip navigation/route heading focus (`App.tsx:13-18,31`). However, current call sites pass summary error labels without `href` values (`WorkflowPage.tsx:82`, `LogDefectPage.tsx:28`), so field-link support in `ErrorSummary` is not itself evidence of linked errors on real forms. Full keyboard, contrast, zoom and assistive-technology acceptance remain unverified.

## Fresh commands and verification limits

The focused existing backend suites ran from `backend/` with dependencies installed only in `/tmp/qualitytrack-qa-review-deps`:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=/tmp/qualitytrack-qa-review-deps:. \
python -m pytest -q -p no:cacheprovider \
tests/test_workflow_unit.py tests/test_reporting_unit.py
```

Result: **114 passed, one Starlette/AnyIO deprecation warning, 1.98 seconds**. No test or source was edited. A separate in-memory `add_cause` probe confirmed NEW-01 as described above. Tests ran on Python **3.12.3**, whereas `backend/pyproject.toml:9` declares Python `>=3.11,<3.12`; this is useful focused evidence, not supported-runtime certification. Temporary dependency resolution is not a fully locked production environment.

Frontend unit/component tests were read, not rerun: `frontend/node_modules` was absent. No build, lint, Playwright, full backend integration, fresh npm audit, live PDF download or Mac/Safari run is claimed. PostgreSQL tests use private database metadata and create/drop test databases (`backend/tests/conftest.py:27-83`); they were not invoked in this read-only review. No services were started or real business data changed.

The repository's PDF renderer intentionally supports a Latin/WinAnsi repertoire and fails rather than silently dropping unsupported glyphs (`evidence.py:234-238`; `backend/tests/test_reporting_unit.py:315-321`). That is an existing documented scope limitation, not newly certified internationalization. Historical audit totals and previous frontend test counts are not fresh outcomes.

Remote develop equality was verified despite the fetch metadata error. Pre-existing untracked `.kavia/` and `logs/` were left untouched. This document is the only intended commit payload; Git commit/push outcome and the final remote branch SHA must be verified from the actual Git command results, not inferred from report creation.
