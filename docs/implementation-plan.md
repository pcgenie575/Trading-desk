# Trading Desk Implementation Plan

Version 1.1 | 10 October 2026 | Owner: Trading Desk

Baseline: [source commit a8e8ed0](https://github.com/pcgenie575/Trading-desk/tree/a8e8ed0f6a3a04bc8d63613fdf75397a4099729d), checked against the retained source. Deployment evidence is the verification recorded on 10 October 2026 Perth time. This documentation update does not change trading rules or certify today’s live health. “Proposed” items require implementation and acceptance.

## Purpose and baseline

This is a handover and evidence-led improvement plan. Completed phases describe deployed work; proposed phases are not silently approved deployments. The owner’s boundaries remain paper trading, existing Oracle hosting and free data/services. A new broker/live-money operation is outside this plan.

## Completed phases

| Phase | Implemented outcome | Recorded acceptance |
| --- | --- | --- |
| 1. Cloud paper operation | Existing Oracle VM, Caddy HTTPS, private login/control token, persistent SQLite and scheduler | Authentication, process health, ledger/circuit-breaker tests and restart/reboot evidence from earlier releases |
| 2. Agent control room | Seven clickable roles, audit-driven links, coverage and free-request budget | Agent selection, event deduplication, escaped audit text and read-only refresh checks |
| 3. Swing journal | Saved candidate/context, reviews, R analytics, calendar and planning tools | Context/review persistence, legacy migration and timezone/calendar logic checks |
| 4. Learning/knowledge | Five original book-informed lessons, role references and revisioned knowledge tab | Seed, approval, role filtering, conflicts, history and restart checks |
| 5. Execution/exposure | Later eligible fills, estimated costs, gap handling, cost-aware sizing, sector/correlation limits | Queued-order persistence, no fill before decision, gap/cash and correlation/fallback tests |
| 6. Research/review | Eight fixed comparisons, passive baselines, all results retained, weekly decisions and forward plan | No later-data leakage into development, partial-exit accounting, dedupe/reuse, forward progress and report persistence |

The latest baseline recorded 26 passing backend tests plus JavaScript checks. HTTPS, scheduler, restart persistence, preserved entries and ledger reconciliation were verified. Browser visual/mobile/accessibility acceptance remains outstanding. There were zero closed operational paper trades at that recorded check; the initial historical comparison’s losses are separate from actual paper ledger results.

## Completed — Analyst Brain release

Descriptive Analyst tools are now implemented in analyst-tools-v1 and validated with 26 backend tests plus UI logic checks. Any promotion of trend/relative-strength/volume filters into entries still belongs to a new recorded protocol and separate validation period; the existing reserved forward test stays frozen. See [Analyst Brain guide](../ANALYST_BRAIN.md) for calculations, use and limitations.

## Phase 7 — Complete usability acceptance (proposed)

Review the deployed dashboard and lab in an authenticated browser, on desktop and narrow screens. Exercise keyboard navigation, focus, zoom, reduced motion, visible errors, calendar timezone changes, revision conflict recovery and full exports. Verify numbers against the API, including unknown metrics and legacy costs. Exit: a dated check records what passed, screenshots where useful and unresolved defects. Do not seed fictional trades in the live ledger to populate charts.

## Phase 8 — Improve recovery assurance (proposed)

Choose an owner-approved encrypted off-server backup destination with a verified free allowance. Preserve the existing daily 14-copy VM backups. Rehearse restoration into an isolated environment; test integrity, cash equation, open positions, pending orders, freezes, checkpoints, lessons and research provenance. Add explicit migration versions/checksums and source/deployment release identifiers. Exit: a restore drill succeeds and failure/retention ownership is documented. Off-server automation is currently not configured.

## Phase 9 — Collect the reserved forward sample (active collection)

Leave the frozen SPY protocol unchanged while collecting 120 completed candles opened after its registration, with 60 preceding warm-up bars. The scheduler records all eight variants once when ready. At four-hour swing cadence this takes weeks or months. Inspect freshness, request capacity and failures throughout. Keep negative and failed trials. Exit: full results, dataset hash, protocol, dates, costs, sample size and passive comparison are available. Completing the sample does not automatically validate an edge.

## Phase 10 — Decide whether a strategy warrants further testing (proposed)

The initial historical later-period SPY results were negative for all eight variants and below passive. Do not promote the “least bad” variant just because it ranks first. Review forward results, per-setup expectancy after costs, drawdown, exposure, holding time, execution assumptions and dependence between trades. Document the decision as continue collecting, investigate or pause with evidence and limitations. Thirty closed trades is a review milestone, not a significance threshold.

Any changed entry/exit/cost setting needs a new versioned protocol and a separate later validation period. Reusing tested periods must be labelled. A practical minimum review includes multiple market conditions and sensitivity to adverse costs/gaps; do not invent a universal profitable threshold. Exit: the owner has a concrete, reviewable decision, with no automatic strategy activation.

## Phase 11 — Release an approved paper-only rule change (proposed)

Prepare an isolated test ledger and implementation diff. Test no lookahead, queued fills, stops/gaps, costs/cash, partial-exit conservation if introduced, concentration, daily/drawdown gates, duplicates, migrations and restart/recovery. Keep existing position contexts immutable; explicitly decide whether old positions retain their exit version before modifying code. Back up before deployment, publish a coherent repository change, verify production health/auth/ledger and retain a compatible rollback. Exit: release evidence and any known limits are documented. Live broker connectivity remains excluded.

## Ownership, blockers and rollback

| Responsibility | Owner role |
| --- | --- |
| Risk policy, acceptable costs, research questions and promotion decisions | Desk owner/operator |
| Source, tests, migrations, documentation and release preparation | Maintainer |
| Coverage, storage, certificate/host access, backups and incident recovery | Operator |

Roles do not imply an external team or permission to send messages to third parties.

Release blockers include a failed ledger equation, lost pending order/history, auth bypass, schema rollback incompatibility, unhealthy scheduler, unexplained recovery data gap, unexpected paid dependency or unreliable execution timing. A health check alone cannot clear a stale-feed concern.

For rollback, preserve the database and current evidence; do not delete positions, pending orders or losing experiments. Restore a compatible prior application version or a rehearsed backup while stopped. Verify the cash ledger and breaker state before allowing operation. An older app may be incompatible with queued execution/cost semantics even if it can open the SQLite file; copying old code over a new ledger is not a safe rollback procedure.

## Documentation maintenance

Update these six documents when behaviour changes. Record the source commit, local checks, deployment evidence, research status and unresolved issues. Keep the root README and [documentation index](README.md) current. Source code is authoritative when an older feature note differs; never present historical health evidence as a live status guarantee.

## Specialty agent brains — 10 October 2026

The six remaining agents now have role-specific diagnostics, approved assigned lessons and persistent evidence reports. [Open Agent Brains](https://tcr.161-33-69-185.sslip.io/brains). Read [the specialty guide](../AGENT_BRAINS.md) for tools, interpretation, history and limits. Validation: 31 backend tests and interface logic checks. These descriptive previews leave trading/risk/research rules unchanged.

## Decision controls release — 10 October 2026

[Open Decision Evidence](https://tcr.161-33-69-185.sslip.io/controls). New proposals carry durable single-use signed approvals; execution rechecks risk and the validated opening. Individual risk checks and raw proposal/fill evidence are retained. Session-aware quality gates block missing/stale entries and quarantine suspect prices. Existing signal/exit formulas, numeric limits and the reserved research protocol remain fixed, but stricter gates can prevent entries. New closed-trade attribution preserves regime and decision provenance; missing legacy evidence stays unknown.

Read [Control Boundaries](../CONTROL_BOUNDARIES.md) for exact controls, migration, recovery and limitations. Unsigned legacy pending buys are cancelled with their original payload retained in audit; existing positions and exit queues remain. Validation: 47 backend tests and UI logic checks; live visual review remains incomplete.

## Daily edge research — 10 October 2026

[Edge Research](../EDGE_RESEARCH.md) adds a private `/edge` workspace for cost attribution, fixed daily swing candidates, persistent free-history collection, development-only selection and one historical validation. This is research-only: current paper v1, its cost/risk settings and reserved future-data test remain unchanged. Historical validation and a surviving present-day universe are not proof of a future edge; passing screens cannot activate a strategy.

The schema now includes `edge_lab_runs` (23 tables total). It retains the registered protocol, progress, accepted provider pages, exact dataset hash and results. The collector shares the existing credit gate and resumes saved pages after restart; denied free data stops collection. Detailed datasets/trade logs remain private. Validation: 55 backend tests and Edge Research UI logic checks; the new Edge Research desktop layout and live cost/progress display were inspected in Chrome. Comprehensive mobile/accessibility acceptance remains outstanding.


