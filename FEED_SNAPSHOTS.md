# Feed snapshots and historical revisions

## Why the desk paused

Twelve Data documents different coverage for its default US intraday feed and consolidated historical data. Historical coverage becomes available after midnight Eastern on the next trading day. Small changes to previously stored candles can therefore occur without a strategy change.

Source: https://support.twelvedata.com/en/articles/9935903-us-equities-market-data

## Preserve the inputs actually observed

New candles record their first observation time and an inferred feed phase in `candle_origins`. For a candle first seen on its New York trading date, a later, valid provider observation may retain the original OHLCV for decisions when every OHLC difference is at most 0.1% and the documented historical publication time has passed. The phase is inferred from timing; the provider supplies no per-bar source identifier here.

This preserves point-in-time decision inputs. It does not declare the original feed consolidated truth. Quality reports retain both canonical decision inputs and raw provider observations, with transition evidence and a warning. No trusted candle or trade is rewritten by this policy.

Unknown legacy provenance, previously reviewed historical candles, premature changes, larger differences, invalid prices and crypto remain subject to the existing strict checks and quarantine. Existing rows are not retroactively assigned provenance. Material revisions still require explicit, audited review; there is no automatic unfreeze.

## Recovery and deployment

The revision-review API preserves originals and audit evidence. Held-position reviews must pass the existing stop, gap and moving-average exit consistency checks. Resume remains blocked while any quarantine or risk circuit breaker is active. A forced manual cycle now bypasses only the scan interval, retaining request budgets, quality checks and risk gates.

The additive database change creates `candle_origins`; back up the persistent database before deploying. Restart the service, confirm health and scheduler checkpoints, and verify new provenance records and raw/canonical quality evidence. Old quarantines need separate review because their provenance is deliberately not invented.

The complete automated suite passed 95 tests on 17 October 2026, including source transitions, invalid/unknown revisions, publication calendars, evidence persistence and unchanged ledger behaviour. At documentation time the preventive fix is tested source awaiting cloud deployment. Deployment is not established by these tests.

Research ETF corporate-action/history blockers remain unresolved. The change provides no new strategy evidence or permission to promote a strategy, increase risk or connect a broker.
