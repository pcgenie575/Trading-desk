# Finding an edge without changing the operational strategy

Open the private [Edge Research workspace](https://tcr.161-33-69-185.sslip.io/edge). Source code and this guide are public; operational datasets and detailed results remain private.

## Cost diagnosis first

The original SPY experiment has 499 four-hour candles from 10 October 2025 to 9 October 2026. Its later period produced only 4–7 completed trades per variant. Reprice the same trades at the current 35-bps FX allowance, 0 bps, 10 bps, zero **all** costs, and doubled **all** costs. Also rerun sizing, fills and partial targets under those costs. These answer different questions: matched repricing isolates friction; resized simulation can change the path. Both retain their original reused-period label. They are not new validation samples.

On the saved dataset, all eight matched variants stayed negative when only FX was removed: approximately −0.035R to −0.098R per trade. Zeroing every modeled cost produced only +0.004R to +0.067R. This is weak gross performance on a tiny sample, not evidence that a currency-account change creates an edge. The raw $500/$25 illustration costs $6.20 round trip (0.248R); actual risk-sized trades can be smaller and partial exits can add orders.

The paper cost model remains an estimate. Webull Australia's [US market page](https://www.webull.com.au/us-stocks) advertises zero commission with regulatory/FX fees potentially applicable. Its [FX explanation](https://www.webull.com.au/help/faq/2041-How-is-the-FX-fee-calculated) specifies an exchange-rate spread, not a universal 35-bps tariff. [AUD settlement mode](https://www.webull.com.au/help/faq/2037) converts funds for trades and incurs FX charges; [manual currency conversion](https://www.webull.com.au/help/faq/1394) supports converting AUD to USD. A reusable USD balance should be modeled with separate funding/repatriation events once its account-specific operation is verified. Zero per-trade FX is a sensitivity scenario; it excludes funding costs and actual currency returns. Do not edit v1 costs retrospectively or describe these scenarios as exact broker invoices. Sources checked 10 October 2026.

## Daily protocol locked before calculation

`daily-edge-v1` is stored in `daily_research.py` and registered in SQLite before any history calculation. The existing `swing-research-v2` experiment protocol and reserved forward test remain unchanged. Daily data is research-only, with no order-generation connection to the paper ledger.

Development: 2006–2015 on SPY, QQQ, IWM, DIA. Historical validation: 2016–9 October 2026 on those four plus AAPL, MSFT, AMZN, NVDA, GOOGL, META, TSLA, AMD, JPM, XOM, GLD, TLT, F, INTC, IBM and CSCO. The additional names broaden outcomes; they do not cure survivorship bias. Symbols with later listing/history dates are not padded or presented as having 20 years of data.

Six candidates are fixed:

1. Trend/breakout/exit averages 100/20/50.
2. Longer daily baseline 200/55/100.
3. 100/20/50 plus SPY above its 200-day mean.
4. 100/20/50 with a 2.5× ATR initial stop instead of 5%.
5. 100/20/50 with a 3× ATR trailing stop replacing the MA exit.
6. 100/20/50 with a top-quartile relative-strength filter.

Each enhancement is tested individually, never silently combined. ATR is the simple mean of 14 true ranges, not Wilder smoothing. Relative strength averages 126- and 252-session price returns and ranks all eligible symbols on the signal day with at least 12 available. Other symbols can therefore supply development-time ranking context; they are separate validation **trade** symbols, not wholly unseen feature sources. Two fixed baseline neighbours, 90/18/45 and 110/22/55, are diagnostic only and cannot win selection.

Select exactly one candidate using positive pooled development expectancy under doubled costs, then highest such expectancy; ties follow declared order. If none survives, stop before historical validation. The selected candidate gets one historical validation, with normal and doubled costs. No replacement winner or revised parameters are tested after seeing that result. API deduplication prevents rerunning a completed job under the same protocol. Any future protocol must record prior data exposure and cannot relabel this period as fresh.

Signals use completed daily closes; fills use the next observed SPY trading session's open. Missing that next session skips the intended entry/queued exit instead of pretending a later opening was available. Stops use the worse opening across a gap. Trails calculated at close first apply on the next day. Terminal liquidation is explicitly labeled END_OF_RESEARCH. Overnight losses can exceed planned risk.

## Free history and persistence

[Twelve Data history documentation](https://support.twelvedata.com/en/articles/5214728-getting-historical-data) caps a request at 5,000 points. Twenty years can exceed that, and younger instruments have shorter histories. This job uses **40** bounded requests: two periods for each of 20 symbols, with daily interval, an explicit 23:59:59 end boundary and split adjustment. Initial date-only responses omitted their final trading day; these originals are retained and separately budgeted single-day supplements restore the declared boundary. A first deployment therefore uses additional requests; it does not overwrite the original responses. All requests reserve credits through the existing shared 6/minute and 600 scanner/day allowance inside the 720/day ceiling. Research requests run at most five/minute and yield when the shared budget is unavailable; the active-position reserve is preserved. This does not purchase subscriptions or bypass entitlements.

Every accepted page and its provider metadata are stored before the next request. Restart resumes missing pages; collected pages are not overwritten. A denial, invalid response or unavailable instrument stops the job as DATA_BLOCKED. It does not switch to paid data, fabricate history or omit a failing symbol. Two token-authorized data retries are available; completed calculations cannot be rerun. The full protocol and combined dataset hash are retained before calculation begins. Responses must match symbol, USD, exchange and daily interval. OHLC, chronological dates, weekday dates and coverage against saved SPY sessions are checked; development history must reach 2006 and validation history must reach the specified end. These checks are not an independent corporate-action or historical exchange-calendar audit.

The schema adds `edge_lab_runs` (23 tables total), containing protocol, status, progress, accepted pages and retained result. Normal SQLite backups cover it. Dataset exports are private and must not be committed to GitHub.

## Promotion screen

The declared historical validation requires:

- At least 100 completed trades, pooled across independent instrument sleeves.
- Net expectancy ≥ +0.15R and profit factor ≥ 1.3 under doubled spread, slippage, order fee and FX estimates.
- Top two winning trades ≤35% of total positive profit; positive total P/L after removing them.
- Positive stress expectancy on the separate validation-trade symbols.
- Both neighbouring baseline settings positive under stress on development data.
- Lower sum of individual sleeve drawdowns than same-$500-exposure passive sleeves.

Independent $5,000 sleeves are **not one portfolio**. Summed individual drawdowns are a descriptive comparison, not portfolio drawdown; overlapping trades are not independent statistical observations. R uses each simulated trade's cost-adjusted planned loss. Price-only passive results provide context, not the sole promotion bar. No dividends, funding FX, taxes or verified delisted universe are included.

Passing the numeric screen does not activate v2. A portfolio exposure/correlation simulation and genuinely future paper validation are required first. Even 2016–2026 results are retrospective, not provably untouched. Current survivors, multiple candidates and known market history limit confidence. Production v1 stays frozen to its current settings; no broker connectivity is introduced.

## Routes

Authenticated reads: `/edge`, `/edge-lab`, `/edge-lab/{id}`, `/edge-lab/{id}/dataset`. Summary reads omit full trade logs and raw pages without deleting them. Viewing performs no provider requests.

Control-token writes: POST `/edge-lab/cost-diagnostic` with `source_run_id`; POST `/edge-lab/daily` uses the fixed protocol; POST `/edge-lab/{id}/retry-data` resumes blocked collection only. All strategy changes remain outside these routes.

## Recorded acceptance and research decision — 10 October 2026

The Oracle deployment passed HTTPS authentication, health/scheduler checks and preservation of positions, numerical risk limits and the existing reserved forward protocol. Saved pages survived deployment restart without replacement. All 40 primary history pages completed using free data; 20 separately retained end-date supplements brought the first collection to 60 budgeted requests. A first calculation failed on a missing implementation of the **already-declared** 55-day neighbour exit. That failed attempt is retained with its dataset hash and development-stage location. The missing calculation was repaired; the protocol, data and selection criteria were unchanged. No candidate selection or validation calculation occurred before that failure.

55 backend tests passed, including execution of all six candidates and both neighbours, date boundaries, no future-price use, next-session fills, gap losses, fixed-path cost repricing, authenticated durable jobs and selection/stop behavior. UI logic checks passed. The live cost tables and collection progress were visually inspected in Chrome at the desktop viewport; comprehensive mobile/accessibility acceptance remains outstanding.

The completed development test on 2006–2015 returned:

| Candidate | Trades at doubled costs | Normal estimated net expectancy | Doubled-cost net expectancy |
| --- | ---: | ---: | ---: |
| 100/20/50 | 137 | −0.074R | −0.261R |
| 200/55/100 | 80 | −0.133R | −0.310R |
| SPY regime filter | 130 | −0.170R | −0.338R |
| ATR initial stop | 137 | −0.115R | −0.314R |
| ATR trailing exit | 150 | −0.056R | −0.246R |
| Relative-strength filter | 17 | −0.289R | −0.432R |

Both baseline neighbours were also negative under normal and doubled costs. Trade counts/paths can differ across cost scenarios; these figures describe independent sleeves, not one portfolio. All six candidates failed the development selection rule. **No candidate was selected, no 2016–2026 validation metrics were calculated, and no v2 was activated.** The validation data is saved, but its prices are accessible and the period is historical; it must not be advertised as provably unseen. A later cost or signal hypothesis requires its own predeclared protocol and explicit record of prior exposure. These results support stopping this experiment, not claiming that every swing strategy is unprofitable.



## Portfolio evidence release — 10 October 2026

The [Portfolio Evidence guide](PORTFOLIO_EVIDENCE.md) documents the shared risk policy, development-only account replay, persisted MAE/MFE, and outstanding earnings/corporate-action/AUD gates. Open the private [Portfolio Evidence dashboard](https://tcr.161-33-69-185.sslip.io/portfolio). This release preserves the failed daily protocol/results and all operational risk limits. SQLite now has 24 tables.
