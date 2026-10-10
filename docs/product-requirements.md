# Trading Desk Product Requirements

Version 1.1 | 10 October 2026 | Owner: Trading Desk

Baseline: [source commit a8e8ed0](https://github.com/pcgenie575/Trading-desk/tree/a8e8ed0f6a3a04bc8d63613fdf75397a4099729d), checked against the retained source. Deployment evidence is the verification recorded on 10 October 2026 Perth time. This documentation update does not change trading rules or certify today’s live health. “Proposed” items require implementation and acceptance.

## Purpose and audience

Trading Desk is a private, cloud-hosted swing-trading research and paper-execution workspace. It connects a fixed strategy, risk gates, simulated orders, records and review so the owner can ask: what happened, why was it allowed, and does the evidence support continuing? It has no broker integration and cannot earn or lose real money.

The operator needs a bird’s-eye view of the seven agents, current positions and coverage. The researcher needs reproducible comparisons and a knowledge base. A maintainer needs recovery, safe changes and an accurate distinction between deployed behaviour and proposed features. One person can hold all three roles.

## Current product

The [dashboard](https://tcr.161-33-69-185.sslip.io/) contains a connected agent diagram, clickable activity detail, cash/equity cards, market coverage, audit feed, swing journal, weekly trade calendar, playbook and risk scenario calculator. The [Research Lab](https://tcr.161-33-69-185.sslip.io/research) holds lessons, hypotheses, experiment notes, calculated comparisons, passive benchmarks and weekly decision reports.

“Agents” are named deterministic software roles. Approved notes become reference context and provenance; they do not fine-tune a language model or execute new rules. The five installed book lessons use original summaries based on public author/publisher descriptions. Full books were not ingested.

## Requirements and acceptance

| ID | Priority / status | Outcome | Acceptance evidence |
| --- | --- | --- | --- |
| PR01 | Must / implemented | See what each agent is doing | Click each of seven roles; show actual audit activity and operating state |
| PR02 | Must / implemented | Know actual market coverage | Show symbol, feed status, last success and timestamps; no claim to scan all Webull instruments |
| PR03 | Must / implemented | Execute reproducible paper rules | Completed-candle signal queues an order; later eligible fill rechecks risk and costs |
| PR04 | Must / implemented | Restrict losses and overlapping bets | Test position, portfolio, sector/correlation, daily-loss and drawdown gates |
| PR05 | Must / implemented | Preserve records across restart | Ledger, queued orders, audit, checkpoints and budget counters remain consistent |
| PR06 | Must / implemented | Understand outcomes | Closed P/L, R, setup/instrument groups, calendar and saved review; unknown historical context stays unknown |
| PR07 | Must / implemented | Save agent lessons | Draft, review, approval, role assignment, immutable revisions and conflict rejection |
| PR08 | Must / implemented | Compare research honestly | Retain eight fixed variants, frozen data/protocol, later-period results and passive baselines |
| PR09 | Must / collecting | Evaluate future data | Frozen SPY forward plan waits for 120 future completed candles and records all variants once |
| PR10 | Must / implemented | Make weekly evidence decisions | Stored report explains continue collecting, investigate or pause; missing metrics remain unavailable |
| PR11 | Must / implemented | Protect access | HTTPS plus dashboard login; writes also require a separate control token; no published secrets |

Implemented means code and recorded functional checks exist. Browser visual/accessibility acceptance remains incomplete; it is not implied by this table.

## Scope and measures

Paper execution covers 16 selected USD US shares/ETFs; BTC/USD and ETH/USD are observation only. The owner chose Webull Australia as the market reference, but there is no Webull connection or complete tradable catalogue. Australian/Hong Kong/China markets, options and warrants remain unavailable in this free feed/model. Trading is long only, without leverage.

Measure net results after recorded estimated costs, drawdown, eligible R expectancy, sample size, reviewed rule adherence, missing/stale data, rejection reasons, restart integrity and research reuse. Separate recorded paper earnings from hypothetical research results. Thirty eligible closed trades is an initial review milestone, not proof of an edge.

The recorded initial SPY comparison used 499 free candles; all eight variants had negative later-period net P/L and lagged the same-symbol passive baseline. That is a dated research finding, not a forecast. Alternative entries/exits remain research only.

## Analyst knowledge and analysis

The Analyst Brain page adds descriptive trend, market, volatility/momentum, relative-strength and volume evidence, approved lessons and recorded outcomes. Active entries/exits and reserved research are unchanged; no prediction or autonomous rule-learning claim is made. See [Analyst Brain guide](../ANALYST_BRAIN.md) for calculations, use and limitations.

## Acceptance and next decisions

The baseline recorded 26 passing backend tests, UI logic checks and authenticated deployment/restart/ledger verification. Process health does not establish freshness or profitability. Before any strategy promotion, require an explicit versioned change, reserved-period evidence, realistic execution review and a tested rollback. No promotion or real-money path is authorised by these documents.

Proposed priorities are an encrypted automatic off-server backup with restore rehearsal, browser/mobile/accessibility review, and evidence-led improvements after the forward sample. Continue within free-service constraints. See [implementation plan](implementation-plan.md).

## Specialty agent brains — 10 October 2026

The six remaining agents now have role-specific diagnostics, approved assigned lessons and persistent evidence reports. [Open Agent Brains](https://tcr.161-33-69-185.sslip.io/brains). Read [the specialty guide](../AGENT_BRAINS.md) for tools, interpretation, history and limits. Validation: 31 backend tests and interface logic checks. These descriptive previews leave trading/risk/research rules unchanged.

## Decision controls release — 10 October 2026

[Open Decision Evidence](https://tcr.161-33-69-185.sslip.io/controls). New proposals carry durable single-use signed approvals; execution rechecks risk and the validated opening. Individual risk checks and raw proposal/fill evidence are retained. Session-aware quality gates block missing/stale entries and quarantine suspect prices. Existing signal/exit formulas, numeric limits and the reserved research protocol remain fixed, but stricter gates can prevent entries. New closed-trade attribution preserves regime and decision provenance; missing legacy evidence stays unknown.

Read [Control Boundaries](../CONTROL_BOUNDARIES.md) for exact controls, migration, recovery and limitations. Unsigned legacy pending buys are cancelled with their original payload retained in audit; existing positions and exit queues remain. Validation: 47 backend tests and UI logic checks; live visual review remains incomplete.

## Daily edge research — 10 October 2026

[Edge Research](../EDGE_RESEARCH.md) adds a private `/edge` workspace for cost attribution, fixed daily swing candidates, persistent free-history collection, development-only selection and one historical validation. This is research-only: current paper v1, its cost/risk settings and reserved future-data test remain unchanged. Historical validation and a surviving present-day universe are not proof of a future edge; passing screens cannot activate a strategy.

The schema now includes `edge_lab_runs` (23 tables total). It retains the registered protocol, progress, accepted provider pages, exact dataset hash and results. The collector shares the existing credit gate and resumes saved pages after restart; denied free data stops collection. Detailed datasets/trade logs remain private. Validation: 55 backend tests and Edge Research UI logic checks; the new Edge Research desktop layout and live cost/progress display were inspected in Chrome. Comprehensive mobile/accessibility acceptance remains outstanding.


