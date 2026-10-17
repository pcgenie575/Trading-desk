# Funding and one fixed turnover experiment

Open the private [Funding & Turnover workspace](https://tcr.161-33-69-185.sslip.io/funding-study), linked from Profit & Evidence. This is research only. The live paper strategy, historical trade costs, account ledger, risk limits, original experiments and existing future-data registration are preserved.

## What the primary sources establish

Webull Australia states that US sale proceeds settle in USD, currency conversion uses a spread in the quoted exchange rate, and ETFs have advertised zero brokerage. These facts support modelling a USD cash account separately from AUD funding/withdrawal. They do not establish a complete account-specific fee schedule. Regulatory/pass-through fees, funding methods, fractionals and applicable account terms still require verification.

- [US proceeds and currency conversion](https://www.webull.com.au/help/faq/1617)
- [FX spread calculation](https://www.webull.com.au/help/faq/2041-How-is-the-FX-fee-calculated)
- [Advertised ETF brokerage](https://www.webull.com.au/help/faq/1423-How-much-does-it-cost-to-trade)
- [Research on buying/holding thresholds and turnover](https://www.nber.org/papers/w20721)

The turnover paper motivates a hypothesis; it does not establish that this particular moving-average buffer works.

## Frozen study: funded-turnover-v1

Register the protocol before reading the price dataset. Reuse only the saved, completed daily source's four development ETFs (SPY, QQQ, IWM, DIA), 2006–2015. Require original source-protocol identity, full endpoint coverage and matching symbol dates; do not download replacements or shorten the period. The period was inspected previously, so this is not untouched validation.

Keep SMA100 trend / previous 20-session breakout entries. Baseline exits below SMA50. The sole new candidate exits below 99% of SMA50. Five-percent protective stops, opening gaps, queue/fill risk checks, shared capital, sector/correlation gates and circuit breakers remain unchanged. No alternative buffer search, weekly variant or second strategy is added after seeing this outcome.

Four cost cases apply to each exit rule:

| Case | Trading costs | Funding and withdrawal |
|---|---|---|
| Original allowance | Existing 5bp half-spread, 2bp slippage, $1/order and 35bp per-side FX allowance | No separate conversion, matching the old modelling convention |
| Primary funded USD | Same spread/slippage; $1/order retained as an unverified total fee reserve; zero per-trade FX | 0.005 quoted-rate spread once each way |
| ETF brokerage floor | Same spread/slippage; zero brokerage and zero per-trade FX; unverified additional fees omitted | Same conversion assumptions; lower-cost sensitivity only |
| Funded stress | Doubled spread/slippage and $2/order reserve; zero per-trade FX | Doubled 0.010 quoted-rate spread each way |

The full contributed capital is USD5,000 equivalent. The illustrative constant bank reference is 0.655 USD per AUD; the reverse bank reference is its reciprocal. These are declared modelling assumptions, not historical exchange rates. A 0.005 quote spread is 50 pips, not a universal percentage. Convert once at funding, trade with the resulting USD cash, then convert terminal equity once at hypothetical withdrawal. Reinvested USD sale proceeds do not trigger repeated FX charges.

The results bridge trading P/L, funding spread, withdrawal spread and net contributed-capital return exactly. Trading drawdown starts from net funded cash; funding losses still reduce contributed-capital return. This reference conversion is not historical AUD performance. Taxes, USD interest, distributions, raw corporate-action cashflows and actual account tariffs remain unmodelled. Different costs and initial cash can change sizing and trade paths: comparisons are resized simulations, not pure fixed-path cost attribution.

## Rejection rules and persistence

This is one new exit hypothesis with four cost sensitivities, not eight independent discoveries. The funded stress candidate must have at least 100 closed trades, expectancy at least +0.15R, profit factor at least 1.3, drawdown no greater than $250 or its baseline, at most 35% of positive profit from the two best trades, positive results without those winners, positive return after funding, lower filled-order count and better net R than the matching baseline. Primary funded net must also improve. Every terminal position must have an actual closing observation.

Failing any screen records REJECT_DEVELOPMENT. Passing only records FURTHER_VALIDATION_REQUIRED; it never enables promotion. Existing ETF input blockers and future-paper requirements remain authoritative. A rejected study is not automatically replaced with another setting.

The additive `funding_studies` table brings the current database to 34 tables. It stores registration time, source/protocol fingerprint, exact development dataset and immutable result. The same version returns the original result without recalculating. Interrupted calculations remain interrupted. `/funding-lab` requires dashboard authentication; `/funding-lab/register` additionally requires the existing control token. Source and this guide are public; private prices, trade logs, credentials and account evidence are not published.

## Recorded development decision — 17 October 2026

The study completed once using the saved development dataset with zero provider requests. The fixed buffer reduced turnover and trading drawdown in the primary funded scenario, but net return after funding remained negative. Its doubled-cost expectancy, minimum sample and profitability screens failed. The decision is **REJECT_DEVELOPMENT**. A positive lower-cost brokerage-floor sensitivity does not override that rejection or establish actual account fees.

The live strategy and cost model were preserved. All 108 backend tests passed, including the unchanged default simulator, cash-conversion bridge, no-future-data checks, one-time registration and unchanged protective gap exits. UI checks covered registration, rejected results, cost presentation, escaping and stale states. The desktop layout was inspected using a separate empty fixture. Private results are available in the authenticated workspace; no holdout, parameter replacement or automatic activation followed the rejection.

Oracle acceptance verified 34 tables, one persisted study, identical results after restart and repeated registration, healthy scheduler/HTTPS authentication, and preserved live costs, trades, limits and future comparison registration.
