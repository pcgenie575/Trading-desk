# Fixed volatility entry-cap study

Research only. Registered before calculation. See `/volatility-study` and `/volatility-lab/result`.

Rule: 20 completed simple daily returns, sample standard deviation × sqrt(252), scale=min(1,0.15/volatility). Scale both $500 position and $25 planned-loss caps. Queue-time quantity is an additional fill ceiling; no held-position rebalancing. All daily signals/exits unchanged.

Two funded cost cases reuse the original daily baseline and 2006–2015 data. No holdout or provider calls. Screens are fixed in volatility_study.PROTOCOL. Lower turnover is not required for this sizing hypothesis. Rejecting this trial does not authorise another parameter search. Dollar returns and drawdown accompany R to avoid mistaking a changed denominator for an edge. ETF verification blockers remain. No promotion or live changes.

## Recorded development result — 17 October 2026

Decision: **REJECT_DEVELOPMENT**, inactive. This is hypothetical reused development evidence, not a live paper return or independent validation.

| Cost case | Daily baseline net | Volatility cap net | Baseline / candidate drawdown | Baseline / candidate closed trades |
|---|---:|---:|---:|---:|
| Funded USD + fee reserve | −$94.52 | −$127.46 | $171.20 / $189.72 | 50 / 71 |
| Funded USD + doubled costs | −$269.80 | −$297.34 | $257.60 / $273.25 | 51 / 71 |

Net is USD-equivalent after funding and withdrawal at the fixed illustrative exchange reference, not historical AUD performance. The primary candidate was $32.94 worse. Orders increased from 100 to 142. Smaller entry caps did not reduce portfolio drawdown in this test. Risk freezes are thresholds, not guaranteed loss ceilings: gap/exit handling may overshoot them.

Stress expectancy −0.1390R failed the +0.15R threshold; only 71 trades failed the 100-trade sample requirement. Profit factor, drawdown, net profitability, positive result excluding the best two trades and improved stress expectancy also failed. Primary R improved slightly while dollars and drawdown worsened—R alone would have given an incomplete picture.

No target/window search, activation, holdout inspection or provider request followed. ETF input verification and challenger qualification remain blockers. Original funding/weekly results, forward collection, ledger, live costs and limits are preserved. 119 backend tests passed plus page logic and element-reference checks.
