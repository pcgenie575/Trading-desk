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

The completed new diagnostic is recorded below; earlier stored results were not overwritten. See [recommendations review](recommendations-review.md) for accepted and deferred changes.

## Recorded result — 10 October 2026

The registered run completed on 499 saved SPY bars. The period was reused; there were zero new provider requests. Dataset hash: `468954066117716e202f57a6a9aec8bb0d6f27efd0d23aa07bf17ce7d5567ae1`. No edge was validated or strategy activated.

| Entry / exit | Matched trades | Gross R | Current R | ETF 50-bps FX R | ETF zero per-trade FX R |
| --- | ---: | ---: | ---: | ---: | ---: |
| breakout / full | 5 | +0.0225 | -0.1870 | -0.1532 | +0.0009 |
| breakout / trailing | 5 | +0.0225 | -0.1870 | -0.1532 | +0.0009 |
| breakout / time | 7 | +0.0036 | -0.2068 | -0.1734 | -0.0181 |
| breakout / partial | 5 | +0.0225 | -0.1870 | -0.1532 | +0.0009 |
| trend_pullback / full | 4 | +0.0463 | -0.1671 | -0.1347 | +0.0240 |
| trend_pullback / trailing | 4 | +0.0463 | -0.1671 | -0.1347 | +0.0240 |
| trend_pullback / time | 4 | +0.0668 | -0.1466 | -0.1142 | +0.0446 |
| trend_pullback / partial | 4 | +0.0463 | -0.1671 | -0.1347 | +0.0240 |

The current stored inventory has 6 registered records and 34 configuration slots, including repeated strategies and blocked jobs. This is not an independent-trial N; unknown earlier/external searching remains undisclosed. DSR and PBO remain unavailable.

All seven cost scenarios retain trades, gross/net expectancy, total estimated costs and cost per trade in R for both methods in the authenticated export. The small reused sample and omitted funding/tax/corporate-action effects prohibit a profitability conclusion.

Acceptance: HTTPS authentication, deduplicated v2 registration, preservation of previous research/ledger/limits/forward plan and persistence of the new result after restart passed. Health and scheduler passed. 72 backend tests and Edge UI logic checks passed; a fresh visual browser inspection was not performed.
