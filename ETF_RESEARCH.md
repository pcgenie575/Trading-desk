# ETF evidence workflow

[Improvement priorities and input diagnostics](docs/edge-improvement-roadmap.md) explain what is needed before this desk can claim a validated edge. The ETF page now groups saved dividend-adjustment discrepancies by year and lists next evidence actions. This read-only diagnostic neither clears a gate nor changes the registered experiment.

[Open ETF Research](https://tcr.161-33-69-185.sslip.io/etf-research) (dashboard login required).

This workflow implements four improvements in order: verify daily inputs and corporate actions; register a diversified ETF experiment; test a shared portfolio with normal and doubled costs; record an agent evidence report. Every stage depends on the preceding data gate. It does not change the active paper strategy, live universe or risk limits.

## Fixed experiment

Protocol `etf-corporate-actions-v1` was stored before collecting its prices. Its five research instruments are IWM (US small caps), IEF (Treasuries), EFA (international equities), IAU (gold) and GSG (commodities). The common issuer makes free distribution records easier to audit. These instruments are research candidates; individual Webull Australia eligibility is unverified.

The warm-up starts in 2006. Development runs from 3 January 2007 to 31 December 2015, allowing for GSG's 2006 inception. One daily 100/20/50 breakout baseline and 5% reference stop are declared. The portfolio shares the $5,000 account, $500 position cost, $25 planned trade risk, three-position maximum, $75 daily realised-loss freeze and $250 drawdown freeze. Research overlap groups include international equity in the aggregate equity cap. The existing live configuration remains unchanged.

Normal and doubled estimated costs are compared with an equal-weight $1,500 passive basket plus cash in the same starting account. The basket is not matched for risk or time invested. No historical holdout is evaluated and no paper version is automatically promoted.

## Input evidence and accounting

Fifteen free Twelve Data pages cover raw, split-adjusted and total-adjusted daily prices for all five ETFs. Collection uses the existing persistent free-data budget. Original issuer SpreadsheetML downloads are saved privately with hashes and downloadable authenticated evidence links; raw market data and issuer exports are not published to GitHub.

The gate checks date/price consistency, missing sessions against the saved SPY session proxy, adjustment-factor changes and distribution reconciliation. SPY is a proxy, not an independently certified exchange calendar. Split events need independent verification. Missing distribution worksheets are UNKNOWN, never zero distributions.

Signals rebase older prices using only actions effective by that decision date. Fills use raw prices. Splits adjust quantities, stops and excursion quantities without changing original cost or risk. Cash distributions accrue to prior-close holdings on the ex-date, count as receivables in equity, and become spendable cash on payment day. Closed-trade profit includes earned distributions once. Entry sizing uses settled cash. Stop levels are reduced by the cash distribution to preserve economic risk. Fractional-share split accounting is modelled; cash-in-lieu is not.

Investor withholding, tax and AUD conversion are not included. Issuer records are retrospective; as-of price rebasing does not prove historical availability of every event announcement. Overnight gaps and uncertain intrabar stop ordering remain disclosed simulation limitations.

## Evidence and promotion boundary

If any input fails, normal/stress results stay empty and the report says INVESTIGATE with the recorded failures. Once all inputs pass, the shared-account simulator records cash flows, equity/drawdown, blocked entries, closed trades and MAE/MFE. The report compares net expectancy, sample size, profit concentration and market-level outcomes. These are evidence notes, not automatic changes to agent rules.

Development gates require 100 closed trades, at least +0.15R expectancy after doubled costs, profit factor at least 1.3, at most 35% of positive profit from the two largest winners, positive profit without those winners and lower drawdown than the basket. Passing means eligible for further validation only. Historical prices already examined cannot later be called untouched validation data.

## Operation and verification

The workflow lives in the existing `edge_lab_runs` table with kind ETF; the database remains at 24 tables. Accepted pages, issuer originals, protocol and reports survive service restart. Running collection resumes; completed calculations do not automatically repeat. A bounded retry is available only for collection failure without a computed result, and prior failures remain recorded.

Authentication covers the page, result, dataset and issuer exports. Registration/retry also requires the control token. The 68-test suite covers corporate-action accounting, future-information isolation, blocked inputs, authentication, deduplication, protocol persistence and existing operating controls. Live dashboard visual rendering still needs a browser check where browser policy permits it.

Sources: [Twelve Data adjustment documentation](https://twelvedata.com/docs), [official IEF data page](https://www.ishares.com/us/products/239456/ishares-710-year-treasury-bond-etf), [Webull Australia ETF overview](https://www.webull.com.au/etfs).

## Recorded first input check — 10 October 2026

Job `b980448d-f5f2-4e2a-89d0-2052d427e0c7` used 15 provider requests and five issuer exports. IWM and EFA passed the declared reconciliation gate. IEF has distribution-adjustment mismatches. IAU has no distribution worksheet and its inferred ten-for-one 24 June 2010 split still needs independently recorded verification. GSG has no distribution worksheet and the free price response begins 2 January 2008, too late for the fixed development start.

Status is DATA_BLOCKED. The agent verdict is INVESTIGATE; normal/stress metrics and historical validation are absent. No replacement symbols, relaxed tolerances, shortened period, paid endpoint or strategy promotion were used to obtain a result. The next research action is to diagnose the saved discrepancies and obtain complete free corporate-action evidence.
