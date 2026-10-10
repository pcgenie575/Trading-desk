# Portfolio evidence and the next research gates

Open the authenticated [Portfolio Evidence dashboard](https://tcr.161-33-69-185.sslip.io/portfolio). Public source and documentation do not include private datasets, trade records or credentials.

## What this release does

The operational desk and portfolio research now call `risk_policy.assess` for the same sizing, cash, per-position, portfolio, duplicate-position, daily-loss, drawdown, sector and correlation checks. Operational signed approvals, data-quality checks and atomic accounting remain additional requirements. Extracting the policy changes no limits or eligibility.

`portfolio-development-v1` records a single, fixed diagnostic of the previously declared daily 100/20/50 baseline on SPY, QQQ, IWM and DIA during 2006–2015. It shares one $5,000 account rather than creating four accounts. Queue and next-open fill checks both apply the shared policy. Normal and doubled costs are recorded; denied orders and the equity/high-water curve are retained. The existing completed daily experiment supplies only development prices, so this replay needs no additional provider requests and calculates no 2016–2026 holdout metrics.

It is a daily migration diagnostic, not an exact reconstruction of the live four-hour scanner. A missing held-symbol bar blocks entries; fills are not invented. At each session, opening marks and opening-gap/queued exits precede entries in the declared symbol order, followed by intrabar stops and closing marks/signals. This fixed order is an assumption, not tick-level execution. Missing next sessions expire orders. A drawdown or daily-loss freeze persists through the remainder of the experiment; protective exits continue. Missing final prices leave a position unliquidated and flagged. Otherwise research end liquidation is explicitly synthetic.

A $500 SPY passive allocation in a $5,000 account provides a price-only reference after the same costs. It is neither time nor risk matched to the strategy and excludes dividends; it is not a promotion rule. Aggregate portfolio drawdown replaces the sum-of-sleeve approximation in this separate diagnostic. The original daily selection protocol and all its stored results remain unchanged.

## MAE and MFE

The new `trade_excursions` SQLite table persists excursions for paper trades; `/trade-excursions` provides authenticated evidence. New entries record the raw opening reference, quantity and original cost-adjusted risk. Earlier open trades begin collecting without manufacturing earlier observations, and display **incomplete legacy history**. Trades without observations display unknown values.

MAE is adverse price movement and MFE is favourable price movement before costs, expressed in dollars, percent and original R. An opening exit includes only its opening price. At an intrabar protective stop, OHLC cannot establish whether the high preceded the stop: only guaranteed pre-exit prices are included and `exit_order_uncertain` marks lower bounds. Duplicate or older bars cannot revise observations. These measurements do not change stops or train a strategy automatically.

The replay stores excursions for each closed trade and flags losses exceeding planned risk. Such a flag alone does not prove an earnings gap; it needs the recorded opening, stop and verified event history. Zero closed paper trades means no operational gap-loss sample, not proof that gaps are harmless.

## Gates still outstanding

The saved free account was probed on 10 October 2026: IEF, DBC, EFA and XLF returned USD ETF daily data. For AAPL on 28 August 2020, `adjust=none` returned a close of 499.23001 versus 124.8075 for `adjust=splits`, approximately a 4:1 ratio; both returned 129.039993 on 31 August. Six requests were charged through the shared credit gate and their evidence was saved privately. No earnings-calendar request was made.

1. **ETF diversification:** IEF, DBC, EFA and XLF are availability-check candidates alongside existing TLT and GLD. A successful free quote does not establish historical coverage, diversification, Webull AU eligibility or an edge. Freeze a separate ETF protocol before multi-year testing, use histories since inception, verify exposures and correlations, and retain unavailable/delisted-universe limitations. No instruments are added to the live universe by this release.
2. **Earnings:** a verified, dated, point-in-time event source and a written exclusion window are needed. Twelve Data documents its earnings-calendar endpoint at **40 credits per request**, exceeding this desk's conservative six-credit-per-minute gate. This release does not call that endpoint, buy an upgrade, or claim an earnings blackout is operating. Until a suitable free source is verified, stock earnings risk remains an explicit operating limitation. [Provider endpoint documentation](https://twelvedata.com/docs).
3. **Corporate actions:** daily time-series requests already specify split adjustment; the provider documents `all`, `splits`, `dividends` and `none`. An account-specific probe checks whether raw and adjusted prices actually differ across AAPL's 2020 split. Both research signals and fills remain in the same split-adjusted synthetic units. Mixing adjusted signals with raw fills requires verified split factors, quantity/stop conversion and dividend cashflows; it is not achieved by changing a request parameter. Live intraday data is unadjusted and abnormal gaps still trigger quality controls. [Adjustment documentation](https://support.twelvedata.com/en/articles/5179064-are-the-prices-adjusted), [API modes](https://twelvedata.com/docs).
4. **Higher risk and a second strategy:** deferred. Fixed $25 planned risk and the existing circuit breakers stay in force. Mean reversion is not added to compensate for a failed trend test.
5. **AUD and tax:** the USD signal ledger and per-side FX allowance are not AUD investment returns. An AUD view needs actual dated funding/conversion/withdrawal cashflows and exchange rates, with currency effects separated from strategy effects. Tax treatment needs the user's accountant; no assumed tax rate or after-tax profit is displayed.

## Stop rule and current conclusion

The development portfolio replay recorded 51 trades, net P/L **−$172.18**, expectancy **−0.1350R**, maximum observed drawdown **$263.75** at normal estimated costs. Its drawdown entry freeze began on 22 July 2015. At doubled costs it recorded 40 trades, **−$217.31**, **−0.2173R**, and **$266.59** maximum drawdown, with a freeze on 17 November 2011. A threshold is not a guaranteed loss ceiling: observed gaps and existing-position exits can push drawdown beyond $250. These are simulated development results, not actual money or holdout evidence.

All six declared daily candidates failed the development cost screen. No candidate was selected and no historical validation results were calculated. This blocks promotion to a new forward paper version. Existing v1 remains an unchanged paper observation operation, not an endorsed profitable system. A future validation failure must stop that candidate; further parameter searching on the same holdout would require a new protocol and genuinely new evidence. The whole desk has not been paused on the basis of a holdout that was never scored.

## Verification

All **59 backend tests** pass. The suite includes shared-account exposure rejection, unchanged earlier results after future prices are added, gap losses and persistent entry freeze, pre-exit excursion bounds, and cash/daily-loss rejection at fill. Deployment acceptance confirms authentication, unchanged paper positions/rules/forward registration, completed replay deduplication and persistence through restart. There are now **24 SQLite tables**; the original 23 remain intact. A subsequent calculation repair counts entry-day exposure in the time-invested percentage; the earlier percentages are retained in the job's metric-correction record. Trades, P/L, drawdowns, gates and protocol do not change.
