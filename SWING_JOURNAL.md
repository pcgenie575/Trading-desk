# Swing journal — Plan, record, review

Open the [Trading Desk](https://tcr.161-33-69-185.sslip.io/) and refresh the page after deployment. The existing agent network remains available.

## What the workspace shows

- Monthly closed paper P/L, open-position count, daily realized-loss headroom and marked-equity drawdown headroom.
- A filtered journal with win rate, profit factor, average win/loss, expectancy in R, closed-trade drawdown and assessed rule adherence.
- A cumulative closed-trade P/L curve, high-water mark and zero reference.
- Recorded results by captured strategy/setup and instrument, with sample counts.
- Average dollars per trade by holding period and entry weekday. Holding periods use New York calendar dates; weekend entries are excluded from this heat map.
- Up to eight closing-date weeks and review questions.
- Saved per-trade notes, review status, rule-adherence assessment and an optional rule-break tag.
- Active strategy playbook, a capped USD long-position risk-scenario calculator, journal JSON export and browser printing/PDF output.

## Definitions

Analytics use closed paper positions, sorted by exit timestamp and trade ID. R is realized P/L divided by the recorded planned loss at entry. Trades with a non-positive risk denominator are excluded from R calculations. Expectancy is the mean of eligible R-multiples. Profit factor is positive P/L divided by absolute negative P/L; when there are no losses the display says “No losses”, rather than inventing a finite ratio.

Closed-trade drawdown measures the decline from the high-water mark of cumulative realized results within the selected records, starting at zero. It differs from the operating circuit breaker, which uses the portfolio's marked equity and persistent peak. Monthly/weekly groups use New York closing dates; open records use entry dates for month filtering. Clear the month selector to see all history.

Rule adherence counts only closed trades marked reviewed with a yes/partial/no assessment. Only “yes” counts as adherence. A rule-break table reports the recorded outcomes of reviewed tagged trades; it does not establish the financial cost caused by that habit. Empty groups and insufficient history are shown explicitly. There is no composite Edge Score or trading recommendation.

## Plan and execution history

New paper entries save the candidate, strategy configuration, instrument and risk rules in the same transaction as the execution. Existing positions retain their executions and recorded stops; missing original plan/configuration snapshots are labeled unavailable rather than reconstructed. Review edits cannot change execution prices, cash, stops or the captured plan.

The current engine runs one fixed long strategy and closes a whole position at once. This release does not add partial exits, short strategies, prop-firm account rules, deposits/withdrawals or additional strategy automation. The current simulation includes two basis points of slippage per side and no commission. The risk planner accepts a flat round-trip cost assumption but does not create an order or modify operational rules.

## Save, export and review

Select a trade, write observations, choose its review status and save using the existing control token. Notes and tags live in the server SQLite database and survive restart. Journal JSON exports contain all journal records and captured plans/reviews, not the complete operational database. Use the server backup process for full recovery. The report prints the filtered results and the currently selected detail; use your browser's Save as PDF option.

No paid services, broker connectivity or real-money execution were added. No illustrative product sample trades were imported into the operational ledger.

The design takes inspiration from the descriptions/screenshots supplied by the operator. It uses original interface code and the desk's own paper records.
