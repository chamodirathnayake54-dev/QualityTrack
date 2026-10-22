# Engineer demo walkthrough — REL-2026.10.22-prep

## Preparation outside the timer

Use the approved isolated environment with synthetic data and the real backend. Confirm configuration, active lookups, engineer grants, assignable owners, plant zone and the [smoke checks](smoke-checks.md) beforehand. Have the environment owner provide credentials securely; never display them in slides or recorded evidence. Prepare a unique synthetic part number, short preliminary cause, action description and valid future due date.

The target is **4 minutes 30 seconds**, leaving 30 seconds beneath five minutes. This is a presenter script, not a measured demo result. Use SPA links after login; full reload deliberately loses the memory-only session. If the network stalls or a write is uncertain, stop and explain recovery rather than retrying to keep time.

## Timed script

| Time | Presenter action | Suggested narration and visible proof |
| --- | --- | --- |
| 0:00–0:25 | Sign in as the permitted synthetic engineer and show identity/plant zone. | “This is the bounded engineer journey against the real API. Authority comes from explicit grants, not the role label.” |
| 0:25–1:20 | S1: open new defect capture, choose actual type/line/shift, enter the unique part number, quantity 1 and Major severity; submit once. | “Capture is deliberately photo-free. There is no upload control, and the backend rejects photo parts. Optional-photo product acceptance is still unmet.” Show saved defect ID and captured labels. |
| 1:20–2:00 | S2: follow the cause link, enter the preliminary cause and select Record cause. | “One saved nonblank preliminary cause satisfies the presence gate; it does not prove root-cause validity or require five answers.” Show the persisted cause and actor. |
| 2:00–2:50 | S3: open Review investigation step, inspect context, check the review box and select Move to Under Investigation. | “The transition uses the exact reviewed revision. Changed context requires renewed review, without automatic replay.” Show the confirmed status and attributable timestamped history. |
| 2:50–3:45 | S4: follow Add corrective action, enter description, choose an actual eligible owner, future due date and Open status; select Add action. | “The server supplies eligible owners and enforces authority. This creates assigned work, not verified effectiveness.” Show the associated action and matching fields. |
| 3:45–4:10 | Revisit saved cause, history and associated action through the journey links. | “These are saved server records. A lost response would require reconciliation, not blind resubmission. Reload requires sign-in; autosave is not promised.” |
| 4:10–4:30 | Close with recommendation and limits. | “Conditional Go for this bounded photo-free engineer journey; No-Go for the full product. Photos, broader supervisor screens, auditor/export acceptance and unresolved dependency findings remain open.” |

## Stop conditions and exclusions

Do not demonstrate closure/reopening, overdue dashboards, photo upload, auditor acceptance or browser PDF export as delivered capabilities. Some supporting APIs exist, but their presence does not create missing browser journeys. Do not add permissions or invoke destructive database recreation during the demo.

If a request fails, preserve safe evidence and use the [operations runbook](operations-and-rollback.md). Do not mask failure with mocked success, a second unverified POST, or a claim that all product requirements passed.
