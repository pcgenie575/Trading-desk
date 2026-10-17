# One fixed weekly decision experiment

Open the private [Weekly Schedule workspace](https://tcr.161-33-69-185.sslip.io/weekly-study), linked from Profit & Evidence and the funding study. This test changes decision frequency only. It does not activate a strategy or combine the rejected exit buffer with a new rule.

## Protocol: weekly-review-v1

- Reuse the exact saved four-ETF 2006–2015 development dataset and unbuffered daily baselines from completed `funded-turnover-v1`. Bind original protocol/source and dataset hashes. Do not recalculate or replace either daily baseline.
- Keep SMA100 trend, previous 20-session breakout, unbuffered SMA50 exit, five-percent protective stops and all shared portfolio risk limits.
- Make new entry and moving-average exit decisions only at Friday close. Fill queued orders at the next observed reference-session open.
- Continue opening-gap checks, protective stops, queued fills, account marks and circuit breakers every day. Weekly review never delays a protective stop until Friday.
- If Friday has no observed session, skip that week's new decisions. Do not move the decision to Thursday or use the week's later prices. Research-end liquidation remains the original explicitly synthetic closing assumption.
- Use only the same primary funded-USD fee-reserve model and doubled-cost case as the funding study. Retain one-time funding and terminal conversion at the same illustrative constant exchange-rate reference.

The schedule engine is a frozen daily-engine replica with one isolated Friday decision gate. Exact daily-mode parity tests cover original and funded normal/stress costs. The original portfolio simulator and funding-study implementation remain unchanged so earlier source fingerprints and results stay valid. Shared execution, sizing, risk and concentration modules remain common dependencies.

## Inputs, calculation and rejection

Register this one hypothesis before loading prices or calculating its results. Only two new candidate calculations are performed: primary funded and doubled costs. The daily controls are referenced from the prior saved study. Four displayed comparison cells are not four independent trials. Both source studies reuse already inspected historical development data; no holdout or claim of independent evidence is introduced.

The candidate must meet the same declared sample, stress expectancy, profit-factor, drawdown, concentration, positive-after-funding and lower-turnover checks as the earlier study, and improve primary net performance. Passing records FURTHER_VALIDATION_REQUIRED; failing records REJECT_DEVELOPMENT. No automatic promotion, alternate weekday, threshold change, weekly buffer or replacement strategy follows a failure. The existing ETF input blockers remain unresolved.

Split-adjusted synthetic prices, missing verified distribution cashflows, a reference-session proxy, estimated fees, no historical FX path, taxes and USD cash interest remain limitations. Slower moving-average exits may increase losses. Daily protective stops constrain risk but cannot guarantee fills at the planned stop price.

## Persistence and access

The additive `schedule_studies` table brings the current database to 35 tables. It retains registration, protocol/source hashes, exact input dataset and result. The same fixed version cannot silently recalculate on new prices. Interrupted jobs remain interrupted. Compact `/schedule-lab` responses omit large per-trade/daily histories; `/schedule-lab/result` exposes the full private result for inspection. Both require existing dashboard authentication; `/schedule-lab/register` also requires the control token.

The central `/research-accountability` inventory now includes funding and schedule records, including blocked/rejected jobs. It identifies one new hypothesis for each, counts reused baseline slots explicitly, and distinguishes two new weekly calculations from referenced controls. It continues to report that the all-time independent search count is unknown; no guessed statistical confidence is added.

Production acceptance requires unchanged live trades, risk limits and cost model; preserved previous funding results and future-data registration; authentication; one-time calculation; and persistence after restart. No provider requests, paid services or broker connection are used.
