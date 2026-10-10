# Analyst Brain and trend-analysis tools

Release: analyst-tools-v1, 10 October 2026. [Open Analyst Brain](https://tcr.161-33-69-185.sslip.io/analyst) using the existing private dashboard login. This is a descriptive analysis upgrade; active Trend Breakout v1 entries, exits, risk caps and the reserved research protocol remain fixed.

## What acts like its brain?

The Analyst combines three layers: coded analysis tools, an approved knowledge library and recorded experience. These are deterministic software and stored context, not a fine-tuned language model. Custom notes cannot execute instructions or change signals. Four installed book lessons are assigned to Analyst; further approved custom lessons can be assigned in Research Lab. Only approved lesson records are included. Drafts, hypotheses and experiments stay separate.

Each new candle records a TREND_ANALYSIS audit event and a persistent analysis snapshot. New candidate/trade context also includes the report. Snapshots preserve their exact lesson versions and market/data evidence. Startup seeds reports from saved data; no synthetic prices enter the live ledger. The page previews current cached data/approved lessons without writing orders, spending provider credits or changing risk settings. It also shows the latest up to 100 closed paper trades across the desk, with eligible R average and loss streak. Those outcomes do not trigger automatic rule changes.

## The tools

| Tool | Calculation | Meaning and limitation |
| --- | --- | --- |
| Trend alignment | Close, SMA20 and SMA50 | Uptrend requires close > SMA20 > SMA50 and rising SMA50; downtrend reverses all conditions; otherwise mixed |
| Trend slope | SMA50 percentage change over five bars | Requires 55 completed bars; measures four-hour trend slope, not daily/weekly confirmation |
| Market context | Same trend rules on saved SPY candles at or before the instrument candle | SPY is a US equity proxy; stale or missing alignment is disclosed |
| Relative strength | Instrument return minus SPY return over 20 exactly aligned intervals | Requires 21 shared timestamps ending at the current candle; expressed in percentage points; unavailable for SPY compared to itself |
| ATR14 | Wilder-smoothed true range, accounting for previous-close gaps | Expressed in dollars, percent and current stop-distance multiples; volatility, not direction |
| RSI14 | Wilder-smoothed average gains/losses | Momentum reading, distinct from relative performance versus SPY; flat data yields 50 |
| Price structure | Recent five-bar high/low compared with preceding five bars | Window comparison, not confirmed swing pivots |
| Volume context | Current volume divided by ten prior positive volumes from the same New York candle opening time | Missing/zero volume or insufficient matching samples stays unavailable; descriptive 1.2× reference |
| Extension | Distance above SMA20 divided by ATR14 | Above 2 ATR is flagged as extended; no automatic entry ban |

A condition count reports how many available checks are supported. It is not a confidence score, win probability or profitability estimate. RSI ≥70 flags elevated momentum without predicting a reversal. The fixed 5% stop is compared with ATR; actual gap losses can still exceed the planned loss. Four-hour candles are eligible only after their full interval plus 15 minutes. Clock-age flags may reflect closed sessions or weekends and are not proof of provider failure.

ATR/RSI definitions follow [Fidelity ATR guidance](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/atr) and [Fidelity RSI guidance](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/RSI). References explain indicators; our trend/volume/extension thresholds are explicit engineering assumptions, not validated recommendations. Wilder calculations are seeded from the retained history and can differ from longer charts.

## Access, persistence and scope

GET /analyst serves the private page. GET /analyst-analysis previews the 16 paper-enabled US instruments, lessons and paper experience from saved data only. GET /analyst-analysis/{symbol}/history returns up to 50 stored snapshots (20 by default). Authentication applies to all three routes. There is no new paid API, external model call, news feed or broker connection.

analyst_reports is keyed by symbol, bar_time, tools version and context hash; created_at and JSON payload preserve evidence. The hash includes input candles, market context and lesson versions so distinct contexts cannot silently overwrite earlier reports. History reads are bounded; stored reports currently have no automatic retention purge and are included in normal SQLite backups.

Main dashboard navigation and the Analyst card link to the Brain page; Research Lab links back to it. Missing data is shown explicitly. Current limitations include free delayed data, no fundamentals/earnings/news, incomplete volume, single-proxy market context and no calibrated predictive model.

## Validation and next step

26 backend tests passed, including known RSI/ATR cases, trend direction, aligned relative strength, unknown volume, no future-data leakage, immutable lesson provenance, authenticated read-only APIs, snapshots/restart and existing ledger/risk/research tests. Mocked browser logic checks cover chart rendering, instrument selection, empty data, escaped lessons and unavailable metrics. These do not constitute a live visual/accessibility browser review.

Changing entry rules to use these tools requires a separately versioned research hypothesis and validation period. This release enriches evidence and transparency without altering the existing forward test or promoting a new strategy.
