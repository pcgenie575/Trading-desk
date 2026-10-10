# Second implementation review — 11 October 2026

The pasted recommendations were reviewed as external proposals. Useful omissions were identified and implemented; the pasted document itself remains local.

## Changes

1. `cost-diagnostic-v3` declares all seven v2 scenarios at normal and doubled spread, slippage, commission and per-trade FX. Eight existing variants, fourteen scenarios, two methods: 224 calculations, not independent strategy trials. Normal cells use exactly the v2 computation. Existing registrations/results are unchanged. Zero per-trade FX stays zero under stress; absent funding charges are not invented.
2. The research page exposes gross R, net R, total costs and cost/trade R for every fixed-path and resized scenario. Missing fields in older results show unavailable. Sample size and reused-period limitations stay visible.
3. Experiment configuration counts are derived from stored variants, diagnostic neighbours and entry/exit combinations. Unrecognized protocols are explicitly unclassified rather than silently assigned eight trials. Registered slots include repeated configurations and blocked jobs; neither lifetime trial count nor statistical independence is claimed.

No new signals, holdout calculations, allocation ledger, paid feed, risk changes or activation. The v3 sensitivity registration is committed before the saved-data calculation. Cached input needs no new provider request. All v1/v2 outcomes remain auditable.

## Remaining recommendations

Complete corporate-action data remains the prerequisite for trusted ETF portfolio comparisons. The free-only gate is still blocked. Allocation strategies, offset/fill-time comparisons and volatility targets need a separate fixed protocol and validated inputs; they are not silently implemented as active strategies. Bootstrap/DSR/PBO/Monte Carlo require appropriate aligned returns and dependence assumptions. Current short trade samples do not support a confidence claim. See [data layer](data-layer.md) and [research harness](research-harness.md) for actual implementation boundaries.

75 backend tests cover all doubled components, unchanged normal v2 cells, protocol-derived counting, authenticated/deduplicated v3 registration and prior-result preservation, alongside existing operation/accounting tests. Cloud acceptance and numerical results will be recorded after the registered run completes.

## Recorded diagnostic — 11 October 2026

Completed on 499 saved SPY four-hour bars; dataset hash `468954066117716e202f57a6a9aec8bb0d6f27efd0d23aa07bf17ce7d5567ae1`. Eight reused variants, fourteen scenarios, two methods: 224 calculations. Zero provider requests. Every normal scenario cell equals the saved v2 result exactly.

| Entry / exit | Matched trades | ETF zero per-trade FX net R | Doubled-cost net R | Doubled cost / trade R |
| --- | ---: | ---: | ---: | ---: |
| breakout / full | 5 | +0.0009 | -0.0207 | +0.0432 |
| breakout / trailing | 5 | +0.0009 | -0.0207 | +0.0432 |
| breakout / time | 7 | -0.0181 | -0.0399 | +0.0435 |
| breakout / partial | 5 | +0.0009 | -0.0207 | +0.0432 |
| trend_pullback / full | 4 | +0.0240 | +0.0018 | +0.0444 |
| trend_pullback / trailing | 4 | +0.0240 | +0.0018 | +0.0444 |
| trend_pullback / time | 4 | +0.0446 | +0.0224 | +0.0445 |
| trend_pullback / partial | 4 | +0.0240 | +0.0018 | +0.0444 |

Inventory: 7 stored records, 42 registered configuration slots, 0 unclassified records. Repeated/blocked registrations are included; lifetime search count and independent statistical N remain unknown.

No confidence, edge, new holdout or promotion claim. Tiny trade count, inspected single-symbol history, missing funding/tax/dividend effects and assumed execution costs limit inference. Full authenticated export retains all scenarios; this table is a named sensitivity view, not candidate selection.

Cloud acceptance passed: authentication, deduplication, ledger/limits/forward-plan and prior-result preservation; new result survived restart. Health and scheduler passed. 75 backend tests and UI logic checks passed; a new visual browser check was not performed.
