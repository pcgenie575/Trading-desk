# Research Lab & Knowledge

Open https://tcr.161-33-69-185.sslip.io/research using your dashboard login. The dashboard navigation links to this page.

Create a lesson, research hypothesis or experiment record. Record the idea, supporting evidence, limitations and optional source URL. Assign the agents who should reference it. Save with your existing control token.

Draft and in-review records are research only. Approval requires evidence and an assigned agent. Only approved lesson records are included in agent reference context. Archive a lesson to stop future references. Revision history remains available, and new trade plans preserve the exact approved lesson versions used by the Analyst, Risk & Compliance and Paper Trader. Earlier trades are not retroactively relabeled.

The five installed book lessons are read-only records of the existing coded curriculum. Use Create related lesson to develop a draft from one. Custom lessons are saved reference guidance: they do not train an AI model, execute instructions, change signals, alter risk caps or enable broker connectivity. Hypothesis and experiment notes do not execute backtests. The separate fixed comparison engine calculates and retains recorded runs. Evidence is entered by the operator; approval is not proof of profitability.

Records and revision history are held in the persistent server database and included in its regular backups. Concurrent edits are rejected using version numbers. All read routes require dashboard authentication; writes also require the control token. Source links accept HTTP(S) only and are not fetched by agents.

Paper trading and free data remain the operating scope.


## Fixed strategy comparison engine

The page compares Trend Breakout and Trend Pullback, each with full-position MA/stop, a 5% trailing stop, a 10-bar time exit, and a half exit at 1R with the remainder using MA/stop. Rules are predeclared in research_engine.py, not optimized. No alternate entry or exit is activated in autonomous paper operation.

Supply 120–5,000 completed 4-hour bars from saved free data or import a JSON OHLC array with naive New York timestamps and a source description. The first 70% is a development period; the remaining 30% is evaluated separately. Prior bars supply indicator warm-up, but no trade crosses the split. The protocol and exact dataset are durably registered before calculations. Every one of the eight variants, including losers, is retained. Repeating the same dataset and protocol returns its existing run. Overlapping test periods for the same symbol are labeled reused. First recorded use in this lab does not establish that data was truly unknown elsewhere. Failed or interrupted runs remain in history. No backtest-overfitting probability is claimed.

Each comparison includes net P/L, account return, drawdown, expectancy in R, estimated costs, time invested, and passive buy-and-hold of the same symbol/date range at $500 exposure. A fully invested $5,000 baseline is also reported, with different exposure clearly disclosed. Benchmarks include the same entry/exit costs but exclude dividends, taxes and actual currency-market returns. Dataset/protocol and result exports support reproduction.

## Execution and cost assumptions

New autonomous entries and moving-average exits are queued persistently, then reconstructed at the opening price of the first later eligible candle (at least four hours plus the 15-minute provider allowance after the signal candle timestamp, and after the actual recorded decision time). Risk and cash are checked again at fill. Research applies the same four-hour-plus-15-minute eligibility rule, without live scheduler latency. This is delayed OHLC simulation, not a quote observed at the time of execution. A gap below a protective stop uses the lower opening price. Stops get priority if both stop and partial target are touched in a research candle; trailing stops ratchet after close for the next candle. Pending entry orders expire after seven calendar days. Pending buys are polled with open-position priority and cannot bypass a freeze or risk limits.

Model estimated costs per side: 5 basis points half-spread, 2 basis points adverse slippage, $1 order fee, and 35 basis points on notional as an AUD funding/repatriation allowance. These conservative assumptions are not Webull fee schedules. The ledger is USD; no actual AUD conversion or exchange-rate return is simulated. Spread/slippage are embedded in fill price, while fee/FX allowance is charged to cash. Quantity respects original candidate size, $500 all-in position cost and $25 planned stop loss including modeled exit costs. Gaps may exceed planned risk. Existing entry costs and history are preserved; legacy positions incur the new estimated exit costs only when closed.

## Overlapping exposure

New entries must pass $750 sector, $1,000 combined US equity and $750 positively correlated cluster limits, alongside existing caps. Correlation uses at least 30 aligned saved 4-hour returns over up to 100 bars with latest data no older than ten days; threshold is 0.8. Unknown correlation in the same market group counts as overlap. Gold and Treasury proxies use separate fallback groups. Static sectors and ETF groupings are approximations, not constituent-level look-through. Historical correlations can change; existing positions are not forcibly liquidated by this migration.

## Weekly decisions

A report for the most recently completed New York calendar week is generated once at startup and then on weekly scheduler cycles, stored durably and shown on the page. It includes closed sample count, net expectancy after recorded costs, R expectancy, observed equity drawdown, assessed rule adherence, provider failures and legacy-cost coverage. Unassessed trades are excluded from adherence rather than counted as compliant. Equity drawdown is measured against the recorded account peak and may include a peak from before the week; absent historical observations are unavailable.

A frozen desk recommends pause. Recorded data failures or negative weekly results with at least 30 closed trades recommend investigate; otherwise continue collecting. These are operational review rules, not a significance test. Reports do not change strategies or risk controls. No trades, no assessed reviews or missing historical equity produce unavailable metrics rather than invented results.

Sources: [Backtest overfitting research](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf) supports retaining trials and avoiding repeated selection on reused data. [FINRA concentration guidance](https://syndication.finra.org/content/concentrate-concentration-risk-0) supports reviewing overlapping exposure. The numerical caps, protocols and costs above are this desk's explicit engineering assumptions, not rules from those sources.

## Reserved forward period

A SPY forward plan freezes the eight-variant protocol at registration. It waits for 120 completed free-feed candles whose opening timestamps are after registration, with 60 preceding bars for warm-up. The scheduler then records every result once, without selecting settings or activation. Progress appears in the lab. This takes weeks or months at a 4-hour swing cadence. Historical comparisons are exploratory; this reserved future period supplies genuinely later data relative to registration. If the protocol changes, the old plan requires review rather than silently using new rules.
