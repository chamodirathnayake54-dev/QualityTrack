# Batch 4 verification and dependency audit

## Scope and prerequisite

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
