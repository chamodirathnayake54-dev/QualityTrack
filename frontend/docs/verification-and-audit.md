# Batch 4 verification and dependency audit

## Audit-trail correction verification

This section supersedes historical verification totals below for this correction.
The current branch is `polish/frontend-usability-20261024`; the actual starting
HEAD was `85c1dc5`, differing from the supplied prior-session summary.
`git merge-base --is-ancestor e0a24dc HEAD` exited 0.

Classification: repository implementation defect in presentation. Backend
`workflow.py` projects `actor_ref` and `owner_ref`; WorkflowPage omitted the
actor and AssociatedActionList omitted the owner. The correction renders
`Changed by {entry.actor_ref}` and `Owner: {action.owner_ref}` without changing
contracts, grants, queries or saved state. Record UUIDs remain hidden in text.
Focused routed tests cover both labels, hidden UUIDs, historical owners absent
from assignable choices, and inline journey progress/accessibility.

DateFilters and Journey are now inline page presentation, not distinct
components. Using the unchanged inventory method gives **11/26 = 42.31% reuse**.
The unchanged S1–S4 rubric gives **36/40 = 90% UX alignment**. Both meet target.

Fresh commands ran from `frontend/` using
`npm exec --yes --package=node@22.23.4 --package=npm@10.8.2 -- <command>`:

| Command | Result |
| --- | --- |
| `npm test` with `CI=true` | **105 tests passed across 6 files** |
| `npx --no-install tsc --noEmit` | **Passed** |
| `npm run test:e2e` with `CI=true` | **2 passed**, desktop and mobile mocked Chromium suites, no retries |

The first unit invocation failed because the WorkflowPage patch had not
applied, and existing polish tests expected badge classes and decorative alert
icons absent from the actual worktree. The patch was corrected and those narrow
presentation expectations restored; only the subsequent complete run is a pass.

Lint remains unavailable (no lint script). Real-stack automated verification
remains blocked by the previously documented services/QA07 configuration;
the requester's manual real-stack verification remains pending. Mocked browser
passes are not backend/database integration or accessibility certification.
Dependency findings below remain open; dependency files were not changed.
The requester authorized a correction commit and non-force push, not release
or pilot acceptance.

## Scope and prerequisite

The Batch 4 sections below retain the earlier verification record. See
[OPS-06 Task 1](#ops-06-task-1-dependency-remediation-review) for the current
dependency review and rerun results.

Checked `git merge-base --is-ancestor e0a24dc HEAD` first: exit **0**.
Baseline HEAD: `e5c9fe850cdf1c884f0b9a5f51f5db1d809423c5`, clean worktree.
Only Batch 4 frontend work and generated-artifact ignore rules are proposed.
No backend/schema/CORS changes, commit or push were performed.

## Functional checks

| Check | Actual outcome |
| --- | --- |
| Existing Vitest tests after final transport change | **84 passed across 5 files**, Node 22 runtime |
| `npm run build` after final transport change | **Passed**, TypeScript no-emit check and Vite production build, 104 modules |
| One Playwright critical-path scenario, desktop 1280×800 and mobile 360×800 | **2 passed**, Chromium; no retries |
| Browser checks | Login keyboard focus order; route heading focus; no document overflow on login/list/S1–S4; long action draft stays bounded |
| Live backend/database integration | **Not run**; browser HTTP is mocked |
| Accessibility conformance / real-user persona acceptance | **Not established** |

The E2E fixture intercepts all `/api/v1/**` requests, enforces bearer use and
expected bodies, and fails unexpected API routes. It asserts one photo-free
multipart capture part, no invented creation preconditions, recorded cause,
reviewed `"2"` If-Match, actual old/new history, and a confirmed Open action
with owner/date/status. Exactly four journey mutations are asserted in order.
Mock IDs and identities are synthetic test-only values, not production grants.

The browser scenario reaches all five reviewed presentation components through
`main.tsx` and routed pages. Existing unit/component tests additionally cover
validation, retained drafts, read states, permission failures, pagination,
uncertain writes and precondition distinctions. Browser coverage is intentionally
one happy path, not a complete browser error matrix.

### Environment and failures resolved during this batch

The default shell had Node 18.20.8; current pinned Playwright 1.64.1 requires
Node 20+. Validation used an isolated npm-provided **Node 22.23.4** runtime,
consistent with the README's Node 22 requirement. Initial browser launch failed
because Chromium revision 1248 was absent; the matching browser was installed.
These failed attempts are not counted as passing tests.

The first actual browser execution exposed a native-fetch receiver problem:
storing `fetch` directly and invoking it as `this.transport(...)` caused a
browser failure before login could reach the API. Wrapping the default fetch
call fixed this without changing injected test transports or backend behavior.
The complete browser path subsequently passed in both viewports. The browser
test is regression coverage for this issue; JSDOM tests alone did not catch it.

Reproduce on a configured Node 22 environment:

```sh
npm ci
npm test
npm run build
npm run test:e2e:install
CI=true npm run test:e2e
npm audit
npm audit --omit=dev
```

## Dependency audit

`npm audit --json` returned findings, **not a clean audit**:

- **12 affected package entries:** 5 moderate, 5 high, 2 critical.
- These counts include propagated dependency effects; they are not 12 separate
  root vulnerabilities.
- `npm audit --omit=dev --json` reports **2 moderate package entries**:
  `react-router` and direct `react-router-dom`.

| Dependency group | Audit severity / evidence | Disposition |
| --- | --- | --- |
| `tinypool`, propagated to `vitest` | Critical; GHSA-5gmw-xhrv-c9v3 and GHSA-85c8-ppgw-ccpr, prototype-pollution gadgets/RCE | Open, development-tool dependency |
| `@vitest/mocker`, `vitest` | Moderate root advisories GHSA-82fw-gwwq-j7x9 and GHSA-qxg6-89mg-rqv8, traversal/read and mock registration injection | Open; do not expose test services |
| `braces`, `chokidar`, `micromatch`, `fast-glob`, `tailwindcss` | High root advisory GHSA-vfj7-8cjw-p6xm, nested-pattern stack exhaustion and propagated effects | Open, build/development chain |
| `postcss-selector-parser`, `postcss-nested` | Moderate root advisory GHSA-rj75-hqrm-r3gf, selector parsing CPU exhaustion | Open, build/development chain |
| `react-router`, `react-router-dom` | Moderate GHSA-wrjc-x8rr-h8h6 (redirect/backslash) and GHSA-337j-9hxr-rhxg (SSR hydration constructor injection) | Open, production dependencies |

This application uses BrowserRouter, not SSR hydration; that observation is not
a blanket exploitability dismissal. Links use bounded application routes and
encoded record IDs; no penetration/security acceptance was performed.

The audit suggests major-version changes, including Tailwind 4.3.3 and
algorithm-selected downgrades to Vitest 2.0.5 and Router DOM 5.3.4. These are not
automatically safe or compatible remedies. No `npm audit fix --force`, overrides
or unreviewed dependency migration was applied. A dependency remediation change
needs reviewed supported upgrade paths plus regression/build/browser testing.
Do not expose development/test servers to untrusted networks or claim the app
is security-cleared because functional tests passed.

## OPS-06 Task 1 dependency remediation review

Session: `OPS-06-QualityTrack-Run`, verified 2026-10-22 against HEAD
`4be660f6c4ad7d1be3f1c642cfe20e18946bd40f`.
The mandatory ancestry check exited **0**, and `git ls-files
frontend/package.json backend/qualitytrack/main.py` listed both files.
Pre-existing untracked `.kavia/` and `logs/` directories were left untouched.

### Same-major remediation outcome

**Blocked for dependency remediation, not for verification:** no published
compatible same-major security fix was found for the reported dependency
chains. Registry version queries and the installed dependency tree establish:

| Chain | Installed / available evidence | Outcome within approved scope |
| --- | --- | --- |
| Production Router | `react-router-dom` and `react-router` are already **6.30.6**, the latest published 6.x release. Both root advisory ranges extend to `<7.18.0`. | No 6.x patch available; production findings remain open. |
| Vitest tooling | `vitest` and `@vitest/mocker` are already **3.2.7**, the latest 3.x releases; installed `tinypool` **1.1.1** is the latest 1.x. Mocker fixes require 4.1.12 for both advisories; Tinypool fixes require 2.1.2. | No compatible same-major patch; findings remain open. |
| Tailwind / Braces | Installed `tailwindcss` **3.4.17**; latest 3.x **3.4.19** still uses Chokidar 3, Micromatch 4, PostCSS Nested 6 and selector-parser 6. Installed `braces` **3.0.3** is the latest published release and remains affected. | A Tailwind patch bump would not resolve these advisories, so no ineffective bump was applied. |
| Selector parsing / glob chain | Installed selector-parser **6.1.5**, PostCSS Nested **6.2.0** and Fast Glob **3.3.3** are already their latest same-major releases. Selector-parser fixes require **7.1.6**; Braces remains vulnerable beneath Fast Glob/Micromatch. | No compatible patched chain found. |

`package.json` and `package-lock.json` are unchanged. No force fix, downgrade,
major-version migration, override or application-code change was applied.
The audit's suggested Router 5.3.4 / Vitest 2.0.5 downgrades and Tailwind 4.3.3
migration are outside this task's scope and were not accepted as safe remedies.
Resolution requires a published compatible backport, or explicit approval for
a separately scoped supported-major migration and regression review.

### Verification rerun

All commands ran from `frontend/`. The shell default is Node 18.20.8;
installation and functional checks used isolated **Node 22.23.4 / npm 10.8.2**
via `npm exec --yes --package=node@22.23.4 --package=npm@10.8.2 -- <command>`.
Audit commands used the shell's npm 10.8.2.

| Command | Actual result |
| --- | --- |
| `npm ci --no-fund` under Node 22 | Passed; installed from the existing lockfile |
| `npm test` under Node 22 | **84 passed across 5 files** |
| `npm run build` under Node 22 | **Passed**; TypeScript no-emit check and Vite production build, 104 modules |
| `CI=true npm run test:e2e` under Node 22 | **2 passed**, desktop 1280×800 and mobile 360×800 Chromium critical path; no retries |
| Final `npm audit` | Exit **1**: **12 affected package entries**, 5 moderate, 5 high, 2 critical |
| Final `npm audit --omit=dev` | Exit **1**: **2 moderate entries**, `react-router` and `react-router-dom` |
| `git diff --exit-code -- package.json package-lock.json` | Passed; neither dependency file changed |

Initial installation failed with `EACCES` beneath `node_modules`; local
dependency-directory ownership was repaired and clean installation then passed.
The initial E2E attempt failed before executing the journey because Chromium
revision 1248 was missing. Running the locally pinned
`npx --no-install playwright install chromium` under Node 22 installed the
matching browser, and a fresh E2E invocation passed both projects.
Neither failed attempt is counted as a pass.

The E2E still uses mocked HTTP, not a live backend/database. Passing functional
checks do not close security findings or establish accessibility conformance.
This update records verification and the remediation limitation only; Task 1's
requested production vulnerability resolution has **not** been achieved.
No commit or push was performed, and Task 2 was not started. Stop for requester
approval before any commit, push or expansion beyond same-major fixes.

## Accessibility and responsive limits

Source review covers semantic labels, description/error associations, grouped
severity, textual statuses, landmarks, error-summary focus, route focus,
scrollable table region and small-screen shrink/wrapping behavior. Shared panel
styles and required-field guidance were improved without changing DOM order.

Chromium viewport and focus checks are not screen-reader, contrast, zoom,
touch-device or keyboard-only full-journey certification. Not-found and unusual
error/long saved-content states were reviewed in source, not all browser-tested.
No axe scan, multi-browser run, WCAG 2.2 AA audit or factory-device pilot is
claimed. See [UX alignment](ux-alignment.md) and [persona review](persona-review.md).

## Approval boundary

Reports describe current proposed worktree evidence, not release acceptance.
The requester must approve this Batch 4 proposal before a commit or push.
Known dependency findings and evaluation limitations remain explicitly open.
