# Fixed volatility entry-cap study

Research only. Registered before calculation. See `/volatility-study` and `/volatility-lab/result`.

Rule: 20 completed simple daily returns, sample standard deviation × sqrt(252), scale=min(1,0.15/volatility). Scale both $500 position and $25 planned-loss caps. Queue-time quantity is an additional fill ceiling; no held-position rebalancing. All daily signals/exits unchanged.

Two funded cost cases reuse the original daily baseline and 2006–2015 data. No holdout or provider calls. Screens are fixed in volatility_study.PROTOCOL. Lower turnover is not required for this sizing hypothesis. Rejecting this trial does not authorise another parameter search. Dollar returns and drawdown accompany R to avoid mistaking a changed denominator for an edge. ETF verification blockers remain. No promotion or live changes.
