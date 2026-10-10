# Research harness — implemented and pending

Implemented: fixed eight-variant four-hour research; isolated daily independent-sleeve research; daily shared-account portfolio replay using shared exposure/risk functions; raw-fill corporate-action ETF accounting gated by validated inputs; immutable cost diagnostics v1/v2/v3. All are deterministic, paper-only, with cached inputs and persisted results.

Completed-bar signals fill at the next eligible opening. Research protective stops account for adverse gaps. Trail updates apply later; stop-first assumptions disclose intrabar uncertainty. Execution/sizing reuse `execution.py`; risk checks reuse `risk_policy.py` and `exposure.py`. Saved logs include costs, risk, reasons, equity/drawdown and excursions where that engine supports them. Corporate-action accounting is available in the gated ETF engine, not retrofitted into old results.

Not implemented: monthly allocation/rebalancing engine, separate funded slow sleeve, exhaustive rebalance offsets, prior-signal close-fill comparison, ASX/AUD fills, withholding/tax or fully replayed live quality/signed-contract/downtime gates. These require a new declared experiment and test fixtures before any calculation. No allocation claim is inferred from the existing independent sleeves or passive basket.

No automatic promotion occurs. Failed development is retained; historical validation remains absent where no candidate was selected. Intrabar paths, survivor selection, hindsight and incomplete action coverage constrain inference. Reports must state sample size and actual omissions instead of asserting all recommended features exist.
