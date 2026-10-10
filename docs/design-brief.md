# Trading Desk Design Brief

Version 1.1 | 10 October 2026 | Owner: Trading Desk

Baseline: [source commit a8e8ed0](https://github.com/pcgenie575/Trading-desk/tree/a8e8ed0f6a3a04bc8d63613fdf75397a4099729d), checked against the retained source. Deployment evidence is the verification recorded on 10 October 2026 Perth time. This documentation update does not change trading rules or certify today’s live health. “Proposed” items require implementation and acceptance.

## Design objective

Give the operator a calm, readable view of the complete paper desk, then allow focused inspection of each agent, trade and experiment. Visuals should explain evidence and relationships. They must not imply that animation, a book lesson, a high win rate or a positive backtest proves profitability.

## Audience and tone

Use plain Australian English for an owner who wants to operate and understand the desk without reading code. Explain paper status, date range, source, cost assumptions and missing evidence next to the relevant number. Keep engineering details in expandable plan/protocol views and documentation. Labels should describe actual actions: “Save record”, “Run and record comparison”, “Freeze” and “View revision history”.

## Existing visual direction

| Element | Current dashboard direction |
| --- | --- |
| Background | Navy #080e18 with restrained gradients |
| Panel | #111b2a; visible border #253449 |
| Primary text | #eaf0fa |
| Secondary text | #9badc3 |
| Positive/accent | Mint #71e2c0 |
| Negative | Soft red #ff9fa7 |
| Typography | System sans-serif, clear headings, tabular numeric values |
| Agent diagram | Seven role cards connected by SVG links |

These are retained source tokens, not a claim of measured contrast compliance. The Research Lab uses the same navy/mint direction with a records list and editor.

## Information hierarchy

Dashboard: paper equity, available cash, unrealised P/L and desk state first; agent flow and selected-agent detail next; then coverage, journal/calendar, playbook/risk scenario, learning library and audit feed. A link to the separate lab stays easy to find.

Research Lab: fixed comparisons and forward progress, weekly decision reports, then knowledge categories, search/filter, record list and editor. Installed lessons are clearly read-only. Custom notes and calculated experiment results have separate meanings and storage. Historical runs show development/later dates, costs, drawdown, invested time and passive comparison; full results and frozen data are exportable.

Journal: show each position once, its open/closed state, saved plan and assessment. Earlier trades lacking context are labelled accordingly. Calendar colours reflect closed P/L on the exit date, not presumed profits while a position is held. Use the selected Perth/New York timezone consistently.

## Interaction and motion

Clicking an agent shows what it received/sent and its latest operating state. Links animate once for new audit events and stay still between events. Respect reduced-motion preferences by using highlights. Do not simulate constant activity to make idle markets look busy.

Knowledge editing preserves unsaved input on save failure. Revision conflicts do not overwrite someone else’s change. Approval requires evidence and at least one assigned agent; only approved lessons are reference guidance. Avoid text suggesting that the software learned new trading rules merely because a note was approved.

Research lists are paginated to suit the small VM. Summaries omit large curves/trade logs; full result exports fetch one run. Display empty states and unavailable metrics without replacing them with fictional data. No demo trades belong in the operational ledger.

## Accessibility and responsive requirements

Use labelled inputs, semantic buttons, visible keyboard focus, accessible status/error announcements and meaningful table headings. Profit/loss must include a sign or label in addition to colour. Agent selection must work without hover, and all diagrams need a text explanation. Provide horizontal scrolling for dense comparison tables/agent layouts while retaining readable mobile controls. Proposed acceptance includes keyboard-only use, reduced motion, zoom and narrow-screen checks.

## Honest data presentation

Always distinguish recorded paper P/L from hypothetical research P/L. Use sample counts alongside expectancy/adherence. Unreviewed trades are not “compliant”. A healthy process is not the same as a fresh feed. Show reused historical periods and future collection progress. Costs are estimates, not broker tariffs; the account is USD and the FX allowance is not an actual currency return.

## Analyst Brain presentation

Analyst Brain adds a close/SMA20/SMA50 chart, readable evidence cards, supported/available conditions, uncertainty flags, approved lessons and historical reports. Condition counts are not win probabilities. Unknown values remain unavailable; RSI and relative return versus SPY have separate labels. Instrument changes clear the history selection; refresh preserves an opened history list. See [Analyst Brain guide](../ANALYST_BRAIN.md) for calculations, use and limitations.

## Acceptance status

Recorded JavaScript checks covered agent selection, event deduplication, escaped record text, research rows/benchmarks, unavailable weekly metrics, forward progress and revision protection. Browser visual/mobile/accessibility review was not completed because preview access was unavailable. Completing that review is proposed work; this brief does not claim visual or accessibility certification.

## Specialty agent brains — 10 October 2026

The six remaining agents now have role-specific diagnostics, approved assigned lessons and persistent evidence reports. [Open Agent Brains](https://tcr.161-33-69-185.sslip.io/brains). Read [the specialty guide](../AGENT_BRAINS.md) for tools, interpretation, history and limits. Validation: 31 backend tests and interface logic checks. These descriptive previews leave trading/risk/research rules unchanged.

## Decision controls release — 10 October 2026

[Open Decision Evidence](https://tcr.161-33-69-185.sslip.io/controls). New proposals carry durable single-use signed approvals; execution rechecks risk and the validated opening. Individual risk checks and raw proposal/fill evidence are retained. Session-aware quality gates block missing/stale entries and quarantine suspect prices. Existing signal/exit formulas, numeric limits and the reserved research protocol remain fixed, but stricter gates can prevent entries. New closed-trade attribution preserves regime and decision provenance; missing legacy evidence stays unknown.

Read [Control Boundaries](../CONTROL_BOUNDARIES.md) for exact controls, migration, recovery and limitations. Unsigned legacy pending buys are cancelled with their original payload retained in audit; existing positions and exit queues remain. Validation: 47 backend tests and UI logic checks; live visual review remains incomplete.
