# Release readiness and notes — REL-2026.10.22-prep

## Recommendation

**Go for the bounded, photo-free engineer S1–S4 journey, conditional on explicit scope and security-risk acceptance and completion of the operational gates below. No-Go for the full product.** This is a recommendation for a controlled demonstration or bounded evaluation, not unconditional production authorization.

[QA Batch 2](../qa/system-validation-batch2.md) records 14 canonical cases passed, one failed requirement acceptance, and five not executable in this release. Its 13 automated groups include two consecutive engineer journeys and independent database reconciliation. The optional-photo acceptance failure remains a failure even though defensive photo rejection passed. Missing supervisor and auditor journeys cannot be accepted on the strength of API diagnostics.

## Readiness checklist

A recorded pass is historical evidence, not a release-owner sign-off at the current HEAD. Unchecked gates remain open; named roles below are proposed responsibilities, not recorded approvals.

| Gate | Evidence and current disposition | Required release-owner action |
| --- | --- | --- |
| Prerequisites | Ancestry command returned 0; required QA report exists. | Complete for this docs batch. |
| Build green | QA Batch 2 records successful TypeScript/Vite production build. | Frontend owner must confirm candidate/artifact identity and rerun on the intended release candidate. |
| Tests green | QA Batch 2 records 84 frontend tests, 13 real-stack groups, database reconciliation, and one setup-document regression passing. It does not claim broad backend requalification. | QA must retain reviewed evidence for the release candidate and run the [smoke checks](smoke-checks.md); use existing backend verification for the intended scope. |
| Dependency scans | Frontend audit review records 12 affected package entries: 5 moderate, 5 high, 2 critical. Production-only audit records 2 moderate Router entries. Findings remain unresolved. | Security owner must refresh full and production-only audits and explicitly disposition risks before bounded use; functional green is not security clearance. |
| Other security qualification | No backend dependency scan, secret-scan clearance, penetration test, or production security approval is established by this batch. | Security owner must define and execute applicable scans and review exposure and permissions. |
| Migrations reviewed | Revision `0001` creates the frozen schema; downgrade drops its tables. No migration is introduced by this docs batch. | Database owner must confirm target revision, application compatibility, backup and restore rehearsal. Downgrade is not data-preserving reversibility. |
| Release notes | Current notes and exclusions appear below. | Product must accept the exact bounded scope and disposition QT-SYS-02 through QT-SYS-04. |
| Runbooks and rollback | [Operations and rollback](operations-and-rollback.md) defines the proposed procedure; no deployment or restore drill was executed here. | Operations must name incident and database owners, pin a last-known-good artifact, and approve/rehearse recovery. |
| Configuration and data | Required assumptions are documented in the runbook. Real-stack QA used a disposable administrator connection. | Environment owner must verify routing, secrets, timezone, grants, isolated synthetic data, and runtime database-role restrictions. |
| Monitoring | A manual watch list exists; configured alerts, SLOs and production dashboards are not evidenced. | Operations must assign an observer and observation window before use. |
| Publication | Documentation is proposed, not committed or pushed. | Requester approval is required before publication; deployment approval is separate. |

## Security findings and limits

The [recorded dependency review](../../../frontend/docs/verification-and-audit.md) leaves Tinypool/Vitest critical development-tool findings, Braces-related high build-chain findings, selector-parser-related moderate findings, and moderate production Router findings open. Counts include propagated package effects, not twelve distinct root vulnerabilities.

The review found no compatible same-major security resolution for the inspected chains. BrowserRouter rather than SSR is used, but this does not establish non-exploitability. Keep development/test services off untrusted networks. Do not use `npm audit fix --force`, downgrades, or overrides as an unreviewed release action. A major-version remediation requires separate approval and regression work.

## Release notes

The delivered browser scope is authenticated defect listing and photo-free capture, saved preliminary causes, explicit reviewed transition to Under Investigation with attributable history, and corrective-action creation and association. The setup correction supplies the required public API-base example and explains explicit configuration; it does not weaken the client's configuration validation.

QA added opt-in real-stack validation with synthetic identities and independent PostgreSQL reconciliation. Recorded coverage includes stale revision handling without replay, permission denials, session isolation, and one committed action whose response delivery was lost. That experiment establishes observed one-attempt recovery, not idempotency or safe deliberate resubmission.

This documentation batch adds release preparation only. It does not deliver photos, overdue dashboards, broader supervisor lifecycle controls, browser PDF/export, auditor persona acceptance, analytics, persistent sessions, or autosave. API support is not browser acceptance. QT-SYS-02, QT-SYS-03, and QT-SYS-04 remain open P1 full-product scope gaps.

## Acceptance boundary

Product must explicitly accept the photo-free engineer limitation; security must explicitly disposition unresolved findings; operations must complete environment and recovery gates. Until then the bounded Go remains conditional. Full-product release remains No-Go even if the bounded demo succeeds. No waiver or approval is inferred from this document.
