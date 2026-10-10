# Registered cost sensitivity v2

Protocol: `cost-diagnostic-v2`, defined in `cost_scenarios.py`. One completed original SPY dataset, no new provider requests. Eight existing entry/exit combinations, seven fixed cost scenarios, matched repricing and resized simulation: 112 method/scenario calculations. This is not a claim of 112 independent strategies or of six total lifetime trials.

The protocol and implementation are committed before the new result calculation. The database separately registers the exact source protocol/dataset hash before running. There is no selection or strategy promotion. The original `cost-diagnostic-v1`, `swing-research-v2` and its forward test are untouched.

| Scenario | FX per side (sensitivity) | Commission per order | Flat $500 round trip | Cost / $25 risk |
| --- | ---: | ---: | ---: | ---: |
| Current model | 35 bps | $1 | $6.20 | 0.248R |
| Stock per-trade FX | 50 bps | $1 | $7.70 | 0.308R |
| Stock low FX | 10 bps | $1 | $3.70 | 0.148R |
| Stock USD balance | 0 | $1 | $2.70 | 0.108R |
| ETF per-trade FX | 50 bps | $0 | $5.70 | 0.228R |
| ETF USD balance | 0 | $0 | $0.70 | 0.028R |
| Zero all costs (gross diagnostic) | 0 | $0 | $0 | 0R |

Except for zero-all, examples retain 5 bps half-spread plus 2 bps slippage per side. They assume unchanged raw entry/exit price, $500 raw notional and one entry/one exit. Actual risk-sized trades and partial exits have different costs. Funding/repatriation conversion and AUD currency returns are omitted in USD-balance cases. Stock commission is a sensitivity assumption; no account-specific fee statement was supplied. ASX is not simulated with this USD dataset.

Fixed-path gross/net R uses each original trade's cost-adjusted risk denominator. Resized gross R adds modeled costs back to each scenario's P/L on its own path and risk denominator; this does not isolate the signal from path changes. Confidence intervals and statistical promotion scores are unavailable on this small reused sample.

Results pending the new registered diagnostic; earlier stored results are not overwritten. See [recommendations review](recommendations-review.md) for accepted and deferred changes.
