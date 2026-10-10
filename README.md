# Trading Desk — autonomous paper operations

**[Open the dashboard](https://tcr.161-33-69-185.sslip.io/)** · **[Analyst Brain](https://tcr.161-33-69-185.sslip.io/analyst)** · **[Research Lab & Knowledge](https://tcr.161-33-69-185.sslip.io/research)** · **[Login help](START_HERE.md)**

A private swing-trading control room on the existing Oracle Cloud VM. Seven named software roles connect free market data, a fixed strategy, deterministic risk checks, simulated execution, audit and performance review. **Paper only. No broker connectivity or real-money trading.**

## Understand how it works

Read the [documentation index](docs/README.md) for the glossary, evidence and recommended reading order.

1. [Product Requirements](docs/product-requirements.md) — what the desk does, who uses it and its boundaries.
2. [App Flow](docs/app-flow.md) — the agents, operator journeys, trade lifecycle and failure handling.
3. [Technical Requirements](docs/technical-requirements.md) — hosting, authentication, modules, risk/cost model and recovery.
4. [Backend Schema](docs/backend-schema.md) — stored records, ledger equations, lessons and research history.
5. [Design Brief](docs/design-brief.md) — dashboard hierarchy, agent links, journal/calendar and accessibility.
6. [Implementation Plan](docs/implementation-plan.md) — completed work, remaining verification and evidence-led next steps.

## Current operating scope

The desk scans a bounded list of 16 USD US shares/ETFs and observes BTC/USD and ETH/USD without executing crypto. It does not cover everything Webull Australia offers. Four-hour data is delayed; five-minute scheduler checks do not turn it into real-time trading. Per-symbol checkpoints and request budgets persist across restarts.

The active Analyst uses Trend Breakout v1: completed close above the 50-bar SMA and prior 10-bar high, with a 5% reference stop and 20-bar SMA exit. Approved buys and moving-average exits queue for a later eligible candle opening after the recorded decision. Stops account for adverse opening gaps. Estimated spread, slippage, order fees and an FX allowance reduce cash and results. Costs are assumptions, not broker tariffs; the account remains USD.

Risk gates enforce $500 all-in position cost/$25 planned loss, three open positions, $1,500 aggregate cost/$75 planned loss, a $75 daily realised-loss stop and $250 drawdown freeze. Additional sector, US-equity group and correlation limits restrict overlapping exposure. These are entry/operating gates, not guarantees against gap losses.

The dashboard has clickable agents, audit-driven links, coverage, swing analytics, a weekly trade calendar, saved plans/reviews, playbook and scenario calculator. The lab holds revisioned lessons and fixed eight-variant comparisons with passive baselines, weekly decision reports and a reserved future-data test. Approved notes are reference context; they do not train a model or change rules. Pullback and trailing/time/partial exits remain research only.

## Analyst Brain

[Open the Brain](https://tcr.161-33-69-185.sslip.io/analyst) to inspect trend alignment/slope, SPY context, relative strength, ATR/RSI, volume, structure and extension. It combines approved lessons with immutable analysis snapshots and closed-paper-trade experience. No model is fine-tuned and no lesson executes a trade. These descriptive tools leave active entries, exits, risk caps and the reserved forward protocol unchanged. [Read the practical guide](ANALYST_BRAIN.md).

## Deployment, access and evidence

The existing Oracle deployment uses Docker Compose with Caddy HTTPS and persistent SQLite. All private pages/APIs require the dashboard login; explicit write controls also use a separate token. The minimal health endpoint is public. Credentials stay outside GitHub.

Daily consistent backups retain 14 VM copies; automatic encrypted off-server backups remain unconfigured. Read [technical requirements](docs/technical-requirements.md) before maintenance. [Earlier Oracle notes](ORACLE_DEPLOYMENT.md) contain dated setup information and must not override the current host/configuration. Do not start a second application process against the operational ledger.

Documentation baseline: source [a8e8ed0](https://github.com/pcgenie575/Trading-desk/tree/a8e8ed0f6a3a04bc8d63613fdf75397a4099729d), recorded deployment verification on 10 October 2026 Perth time. That check passed 26 backend tests, authentication, scheduler, restart persistence and cash reconciliation. Browser visual/accessibility verification remained incomplete. Health evidence is dated, not a live guarantee or proof of profitability.

The first recorded SPY historical comparison used 499 free candles: all eight later-period variants lost money after modeled costs and underperformed the passive baseline. The forward plan was collecting, and there were no closed operational paper trades at that check. Use current dashboard records to assess present state.

## Development validation

Install `requirements.txt` and `httpx` in a disposable Python environment, then run `python -m unittest discover -s tests -v`. Tests use isolated ledgers. Do not supply production keys or point tests at the operating database. Framework pins and recorded tests do not replace dependency/security review, browser acceptance or restore rehearsals.

See [Start Here](START_HERE.md), [Research Lab](RESEARCH_LAB.md), [Swing Journal](SWING_JOURNAL.md), [Market Scope](MARKET_EXPANSION.md) and [Agent Learning](AGENT_LEARNING.md) for supplemental guidance. Keep runtime secrets, ledger/backups and private exports out of source control.
