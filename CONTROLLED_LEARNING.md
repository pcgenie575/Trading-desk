# Controlled agent learning

Version `controlled-learning-v1`. This is a deterministic evidence workflow, not AI-model fine-tuning. It is live on the existing Oracle VM, verified 14 October 2026 (Perth). Open the authenticated [Learning Cycle](https://tcr.161-33-69-185.sslip.io/learning). The `/learning-cycle` API supplies the same evidence.

## Weekly experience and lessons

On each scheduler checkpoint, the worker records any missing completed-week reviews using the existing New York weekly reports. Each review uses closed paper trades through the end of that week, excludes open gains, records the exact evidence hash, and adds a draft lesson assigned to Analyst, Performance Reviewer and Supervisor. Repeated checkpoints and restarts cannot duplicate a week's lesson. No lesson is automatically approved. The knowledge-base capacity remains 250 records.

An operator can approve the original lesson from the Learning page using the control token and a review note. Approval binds the recorded cycle hash and unchanged lesson version. Changed lessons require review through the existing versioned knowledge editor. Approval makes reference guidance available to assigned agents; it cannot execute instructions, change risk or activate a trading strategy.

## One fixed test, not an optimiser

Once the paper ledger has at least 30 closed trades, the desk is not frozen, and cached SPY data passes quality checks, the worker can register one research-only exit experiment. This is a collection milestone, not proof of an edge. It compares the existing breakout/full-exit baseline with the existing breakout/5% trailing-stop alternative, keeping all other existing four-hour parameters fixed. Development uses the older 70% of the frozen dataset. The remaining historical period is not scored. All historical development data is labelled reused, not untouched evidence.

It records the normal-cost candidate, doubled-cost candidate and doubled-cost baseline. Registration, protocol, input quality and dataset hash are stored before calculation. Rejected tests stay rejected; changing the protocol or dataset blocks continuation. Calculation failure stays failed. There is no fallback to a different symbol, neighbouring parameter set, larger risk or paid data. The registered baseline and candidate are included in the research inventory as two reused configuration slots, not independent discoveries.

## Forward paper comparison and promotion boundary

A development candidate must have 100 closed trades, +0.15R or greater expectancy after doubled costs, profit factor at least 1.3, no more than 35% of positive profit from its two largest winners, positive profit without them, and drawdown at most $250. An all-win sample has unestimable profit factor and does not pass. It must also improve on the baseline's stress expectancy without worsening drawdown.

Only then is a forward cutoff registered. The worker waits for the first 1,000 new completed SPY candles after that cutoff, with 50 earlier warm-up candles. Existing saved free candles are used; it makes no provider requests. Candidate and frozen baseline are compared on those same future prices at doubled costs, with the candidate also evaluated at normal costs. The original development and forward datasets are both retained. A passing forward result is `PORTFOLIO_REVIEW_REQUIRED`; failure is `REJECTED`. A freeze suspends research without changing the freeze or interfering with protective exits.

This is a separate shadow paper simulation calculated once at the fixed endpoint, not a second account placing orders or an intraday rolling profit estimate. The existing research engine models one position, delayed four-hour fills, spreads, slippage, fees and per-trade FX. Its synthetic terminal exit, corporate-action limitations and omitted multi-position exposure/circuit-breaker replay remain disclosed. These results cannot approve changing the full desk: portfolio validation and an explicitly approved software change are still required. No strategy-activation endpoint is introduced.

## Persistence, security and verification

Three additive SQLite tables retain weekly cycles, lesson approvals and the single registered test. Existing ledger and research tables are untouched. Reads require dashboard authentication; lesson approvals also require the control token. Snapshots, parameters and all automatic results remain private. The worker cannot change entries, exits, positions, costs, risk limits or credentials. Failures emit a learning error while the operational scheduler continues.

All 90 backend tests pass. Tests cover open-profit exclusion, insufficient/concentrated evidence, threshold screening, freeze preservation, rejected-test deduplication, protocol changes, future-period registration, forward calculation/dataset retention, authentication, stale approval rejection, approved lesson versioning and restart persistence. UI scripts pass syntax checks. Current lack of closed trades means the expected initial behaviour is collecting evidence, not inventing a successful experiment. Live acceptance verified two retained weekly reviews, no automatic tests or approvals, authentication, stale-approval rejection, preserved paper positions/risk limits/freeze, and persistence through service restart. The existing GLD historical-revision freeze remains active. The initial deployment check observed the existing data guards rewriting a freeze reason during startup; the subsequent restart preserved the stable GLD freeze. Browser visual acceptance remains outstanding.
