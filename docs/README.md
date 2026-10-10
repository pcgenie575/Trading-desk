# Trading Desk documentation

The same six-document structure used for PC Genie, adapted to the deployed paper Trading Desk. Start with Product Requirements and App Flow; use the other documents for maintenance and future decisions.

**[Open the dashboard](https://tcr.161-33-69-185.sslip.io/)** · **[Analyst Brain](https://tcr.161-33-69-185.sslip.io/analyst)** · **[Open Research Lab & Knowledge](https://tcr.161-33-69-185.sslip.io/research)** · **[Login and access help](../START_HERE.md)**

## The six documents

| Document | What you will understand |
| --- | --- |
| [1. Product Requirements](product-requirements.md) | Purpose, users, current features, scope boundaries and acceptance |
| [2. App Flow](app-flow.md) | Dashboard journeys, seven-agent flow, queued trades, reviews and failure states |
| [3. Technical Requirements](technical-requirements.md) | Hosting, source modules, API/authentication, costs, risk, health and recovery |
| [4. Backend Schema](backend-schema.md) | Persistent tables, relationships, cash/P&L equations, versions and research provenance |
| [5. Design Brief](design-brief.md) | Visual hierarchy, agent interaction, journal/calendar, accessibility and honest metrics |
| [6. Implementation Plan](implementation-plan.md) | Completed phases, outstanding checks, forward collection and safe next releases |

## The desk in plain English

Market Data collects validated completed candles. Analyst applies fixed entry rules and records descriptive trend analysis with approved lesson versions. Risk & Compliance checks sizing, cash, overlapping exposure and circuit breakers. Paper Trader queues and fills simulated orders with estimated costs. Logger preserves the plan and audit. Performance Reviewer evaluates results and experiments. Supervisor oversees freezes and recovery. These are deterministic software roles in one application, not independently trained AI models.

The active entry remains Trend Breakout v1. Pullbacks and trailing/time/partial exits are research comparisons; none is activated by winning a backtest. Approved knowledge lessons become reference guidance and versioned context, not executable trading instructions. There is no broker connection or real-money order path.

## Useful definitions

| Term | Meaning here |
| --- | --- |
| Paper trade | Simulated execution and account record; no broker order |
| Candle | A four-hour OHLC price bar, used only after completion plus provider allowance |
| OHLC | Opening, highest, lowest and closing price within a bar |
| ATR | Gap-aware price-range measure of volatility; not direction |
| RSI | Momentum based on this instrument’s gains/losses; not return relative to SPY |
| Relative strength | Instrument return minus SPY return over matched candle timestamps |
| Analysis snapshot | Stored report with exact data context and approved lesson versions |
| SMA | Simple moving average of recent closing prices |
| Basis point / bps | 0.01%; 5 bps equals 0.05% |
| Planned loss | Entry-to-stop loss including modeled costs; gaps can lose more |
| R-multiple | Closed net P/L divided by that trade’s planned entry risk |
| Expectancy | Mean result per eligible trade, in dollars or R; not a promised return |
| Drawdown | Decline from an equity high-water mark |
| Passive benchmark | Buy-and-hold of the same symbol over the comparison dates with disclosed exposure/costs |
| Reserved forward test | Frozen rules evaluated on candles opened after registration |
| Reused test period | A historical date range already evaluated in this lab; not fresh validation |

## Evidence and currency

Package version 1.1, 10 October 2026. Baseline source: [a8e8ed0](https://github.com/pcgenie575/Trading-desk/tree/a8e8ed0f6a3a04bc8d63613fdf75397a4099729d). The main application and strategy/execution/research sources were checked against repository blob hashes before writing. Earlier deployment verification recorded 26 passing backend tests, authenticated HTTPS, scheduler health, restart persistence and ledger reconciliation. UI logic checks passed; browser visual/accessibility review remained unavailable.

The recorded first SPY comparison used 499 free candles and all eight later-period results were negative after modeled costs and below passive. The reserved forward plan was collecting 0/120 future candles at verification. These are dated observations, not today’s live status or a forecast. Check the private dashboard for current state and freshness. Historical data, source/data licensing, modeled fees and incomplete real-world execution assumptions still limit interpretation.

## Supplemental guides

- [Analyst Brain](../ANALYST_BRAIN.md): tools, knowledge, memory, practical use and limitations.
- [Start Here](../START_HERE.md): links and private login help.
- [Research Lab guide](../RESEARCH_LAB.md): comparison protocol, costs, overlap gates and forward/weekly details.
- [Swing journal guide](../SWING_JOURNAL.md): review/calculation conventions and exports.
- [Free-data scope](../MARKET_EXPANSION.md): selected watchlist and unavailable markets.
- [Book-informed lessons](../AGENT_LEARNING.md): curriculum method and limitations.
- [Earlier Oracle deployment notes](../ORACLE_DEPLOYMENT.md): setup/recovery background; its dated status/IP/shape guidance is historical. Use current console settings and these technical requirements when they differ.

Never place passwords, API keys, control tokens, SSH keys or operational database exports in these documents or GitHub.

## Specialty agent brains — 10 October 2026

The six remaining agents now have role-specific diagnostics, approved assigned lessons and persistent evidence reports. [Open Agent Brains](https://tcr.161-33-69-185.sslip.io/brains). Read [the specialty guide](../AGENT_BRAINS.md) for tools, interpretation, history and limits. Validation: 31 backend tests and interface logic checks. These descriptive previews leave trading/risk/research rules unchanged.

## Decision controls release — 10 October 2026

[Open Decision Evidence](https://tcr.161-33-69-185.sslip.io/controls). New proposals carry durable single-use signed approvals; execution rechecks risk and the validated opening. Individual risk checks and raw proposal/fill evidence are retained. Session-aware quality gates block missing/stale entries and quarantine suspect prices. Existing signal/exit formulas, numeric limits and the reserved research protocol remain fixed, but stricter gates can prevent entries. New closed-trade attribution preserves regime and decision provenance; missing legacy evidence stays unknown.

Read [Control Boundaries](../CONTROL_BOUNDARIES.md) for exact controls, migration, recovery and limitations. Unsigned legacy pending buys are cancelled with their original payload retained in audit; existing positions and exit queues remain. Validation: 47 backend tests and UI logic checks; live visual review remains incomplete.

## Daily edge research release

The [Edge Research guide](../EDGE_RESEARCH.md) describes the recorded cost diagnosis, fixed daily candidates, free-history collection, historical-validation limits and promotion screens. The separate /edge page preserves operational v1 and its reserved forward plan. The schema now has 23 tables including edge_lab_runs; raw research pages remain private. 55 backend tests passed before publication; see the guide for dated cloud acceptance evidence.






## Portfolio evidence release — 10 October 2026

The [Portfolio Evidence guide](../PORTFOLIO_EVIDENCE.md) documents the shared risk policy, development-only account replay, persisted MAE/MFE, and outstanding earnings/corporate-action/AUD gates. Open the private [Portfolio Evidence dashboard](https://tcr.161-33-69-185.sslip.io/portfolio). This release preserves the failed daily protocol/results and all operational risk limits. SQLite now has 24 tables.


## ETF input and portfolio evidence

[ETF Research guide](../ETF_RESEARCH.md) explains the fixed five-market experiment, raw-price fills, split/distribution accounting, shared risk gates and agent evidence report. [Open the private workflow](https://tcr.161-33-69-185.sslip.io/etf-research). Missing corporate-action coverage blocks performance calculations; this workflow does not activate a strategy. The schema remains at 24 tables and the current test suite has 68 passing tests.


## Reviewed research improvements

Read the [recommendations assessment](recommendations-review.md) and [versioned cost diagnostic](cost-diagnostic.md). The new diagnostic distinguishes gross signal results, FX/fee sensitivity and resized trade paths. Registered experiment counts do not imply independent statistical trials; confidence scores stay unavailable without valid inputs.
