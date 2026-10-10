# Reviewed recommendations — 10 October 2026

The supplied build instructions are third-party recommendations, not project policy. They were compared with the actual source and recorded results. The source repository remains public under the owner's earlier instruction; the supplied document, private data and credentials are not published. This report is an independent implementation assessment.

## Adopted now

- A separate `cost-diagnostic-v2` with seven named cost scenarios, registered before computation. Existing v1 diagnostic, live costs, original experiments and reserved forward plan remain unchanged.
- Both fixed-path repricing and resized simulation; explicit gross/net expectancy and cost per trade in R. Gross is not inferred from removing FX alone: commissions/spread/slippage also matter.
- An authenticated experiment inventory, including failed/blocked jobs and diagnostic neighbours. Counts distinguish registered configuration slots from cost/method calculations. Unknown all-time search exposure is disclosed.
- Missing statistical inputs return unavailable rather than an invented deflated Sharpe/PBO score. The DSR paper requires more than a candidate count: return distribution, sample length and cross-trial Sharpe dispersion matter. Overlapping trades cannot be treated as independent daily observations.
- Cost facts were rechecked against official broker material. Webull describes an FX exchange-rate spread, not a flat percentage. The 50-bps cases are sensitivity assumptions. Zero ETF brokerage is supported by current official material; tax/regulatory/funding charges are still excluded.

## Existing foundations retained

Daily history and cached pages, dataset hashes, next-session fills and adverse gap stops already exist. A shared-account portfolio harness applies the existing risk/exposure code. MAE/MFE, passive comparisons, immutable protocol registrations and failure reports are implemented. The last accepted release had 68 tests, not the document's 31.

The ETF corporate-action gate remains DATA_BLOCKED. IWM/EFA passed; IEF adjustment discrepancies, IAU action coverage and GSG's late history require investigation. A fresh strategy search is premature. Repricing the original four-hour experiment is expressly a reused-period diagnostic, not a remedy for that gate or a new validated edge.

## Deferred, with reasons

| Recommendation | Assessment |
| --- | --- |
| Slow monthly trend and diversified daily trend | Worth considering after complete action-adjusted data. Futures evidence does not validate a long-only ETF implementation. No new strategy tested now. |
| Separate allocation engine/slow sleeve | Architectural separation is sensible, but this requires a separate frozen protocol and explicit limits. No new ledger or relaxed deployment/risk caps now. |
| Rebalance-day offsets and prior-signal close fills | Useful for a future allocation protocol. Fix calendar mapping and order timing before any run; same close as a newly calculated signal would be lookahead. |
| Six catalogue strategies, all costs, neighbours, timing and offsets | A large search with many more than six trials. No automatic catalogue execution, optimizer or rescue variants. |
| DSR/PBO/bootstrap/Monte Carlo | Require suitable aligned portfolio returns and dependence-aware assumptions. Shuffling trades alone destroys calendar, overlap and circuit-breaker behavior. Not a licence to loosen a freeze. |
| 30–50% performance haircut | A scenario illustration, not a calibrated confidence interval or acceptance test. Deferred rather than displayed as evidence. |
| ASX ETF adaptation | Requires supported free prices, AUD execution assumptions, spreads and corporate-action coverage. Do not label US SPY data an ASX test. |
| Automatic global pause after unrelated research failure | Not adopted. Failed candidate remains unpromoted; existing deterministic operational freezes stay in control. |
| Stop after every phase for approval | Not adopted as an external instruction. The owner authorized useful changes. Only actual new operating limits/activation need a concrete decision. |

No broker code, paid service, fictional live trades, risk increase or strategy activation was added. New strategy parameters and promotion thresholds remain unregistered proposals rather than implicitly approved production choices.

## Sources checked

- [Official Webull FX explanation](https://www.webull.com.au/help/faq/2041-How-is-the-FX-fee-calculated): authoritative for its disclosed mechanism, not proof of a particular account's effective round-trip charge.
- [Official Webull ETF brokerage information](https://www.webull.com.au/help/faq/1423-How-much-does-it-cost-to-trade): current brokerage disclosure; additional applicable fees are not eliminated.
- [Bailey and Lopez de Prado, Deflated Sharpe Ratio](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf): A, peer-reviewed methodology; does not validate this project's inputs.

72 backend tests pass, including fixed partial-exit attribution, cost arithmetic, unchanged operational defaults, authenticated registration, deduplication and stored protocol preservation. Deployment/result acceptance is recorded in the cost report after the registered run.
