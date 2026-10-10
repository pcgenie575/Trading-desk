# Decision contracts, data quality and attribution

Release: decision-contract-v1 + session-quality-v1, 10 October 2026. [Open Decision Evidence](https://tcr.161-33-69-185.sslip.io/controls) with the existing dashboard login. This strengthens paper-operation controls. Trend Breakout v1 signal/exit formulas, cost estimates, numeric risk limits and the reserved research protocol remain fixed; stricter data and approval gates can prevent entries previously allowed.

## Proposal → risk → fill

Every new candidate saves a UUID proposal, its SHA-256 digest, raw candle snapshot, data-quality report and Analyst/knowledge context before risk evaluation. A QUEUE decision records each evaluated check, configuration, account state, open positions and assigned approved risk lessons. Rejections are retained. Approved proposals carry a durable approval ID.

The approval body is HMAC-SHA256 signed using the existing server control secret. It binds approval ID, proposal ID/digest, instrument, LONG side, contract version, phase, decision, maximum quantity/cash/planned loss, stop and expiry. Execution requires the exact original proposal, an approved signed QUEUE decision, a matching validated stored candle/opening and a passing current data-quality gate. Changing the symbol, side, quantity, stop or context invalidates the binding. A current freeze or failed risk check still vetoes the fill.

The opening must be after the recorded queue decision and signal opening + four hours 15 minutes, and within seven days of queue time. Expiry refers to the simulated opening time, not delayed receipt time. Data freshness and recovery gates can still cancel a historical entry. There is no newly invented spread or entry-zone bound: actual cost-adjusted size/cash/loss are checked at the reconstructed opening under existing limits.

Before insertion, a separate FILL decision records fresh sizing, cash, daily loss, drawdown, position count, aggregate exposure/loss, sector/equity-group and combined correlation/concentration checks. It captures the fill candle, estimated execution model and current quality evidence. No order can use a proposal merely because its earlier queue check passed.

The approval consumption, fill risk record, position, original context and cash update share one SQLite transaction and process lock. A unique approval ID prevents a second consumption across restarts. Transaction failure rolls all of them back. Proposal, queue/fill decision and trade IDs appear in audit/context records. Gaps or costs that invalidate sizing produce a linked execution-rejection audit event without a fill.

These are enforceable application controls in the existing single-process architecture. They are not independently permissioned services or a tamper-proof database. Administrators who control the database and signing secret are outside that boundary. There is no broker or real-money adapter.

## Data-quality gate

The gate checks fetched data before processing and checks each processed batch before saving prices or moving checkpoints. It preserves assessed input batches separately from trusted ledger candles.

| Finding | Behaviour |
| --- | --- |
| Invalid/non-finite/non-positive/inconsistent OHLC; invalid volume or timestamps | Quarantine the batch; freeze new entries; do not change marks, candle checkpoint or positions from that batch |
| Duplicate/unordered timestamps, incomplete candles or off-session US openings | Same quarantine behaviour |
| Previously saved OHLC revised beyond pricing-noise tolerance | Quarantine; retain the earlier trusted candle and evidence of the revision |
| Opening differs by more than 30% from previous supplied close | Quarantine for investigation; this can be real news, a split or bad data, not a confirmed corporate action |
| Missing expected sessions in latest 60 bars | Block new proposals/pending entries; trusted-price position management remains available |
| A later expected candle should already be completed but is absent | Block new entries as stale session data |
| Calendar year unavailable | Block entries; do not guess holidays |
| Old clock time during weekend/holiday with no later expected completion | Explain closed-session age; existing 24-hour entry-age rule still applies |

The calendar explicitly covers 2026–2028 from [NYSE holidays and trading hours](https://www.nyse.com/trade/hours-calendars). US core-session four-hour openings are assumed at 09:30 and 13:30 New York; an early close omits 13:30. The conservative opening + four hours 15 minutes completion allowance remains unchanged, including early-close days. New York timezone handling includes daylight saving. No calendar network request is made during operation.

Pricing-noise tolerance is 0.0001% relative or $0.00001 absolute, to accommodate provider floating-point representation; genuine revisions still require review. The 30% discontinuity threshold is a conservative engineering assumption, not a validated trading filter. Unscheduled closures, halts, verified splits/dividends, actual spreads and news events remain unavailable. Missing/zero volume does not invent volume confirmation; negative/non-finite volume is invalid. Crypto remains observation only and does not use the US session calendar.

Quarantined prices cannot safely trigger a simulated stop or fill; other symbols with trusted data can still manage positions while the desk is frozen. Missing/stale session history alone does not prevent trusted exits. Resume requires the existing control token, cleared financial breakers and no latest quarantined quality report. A later clean validated feed can clear the quality finding, but the global freeze still needs deliberate manual resume. Startup does not overwrite an existing quarantined provider report with saved-data previews. Startup previews alone do not auto-freeze the desk; live processing applies quarantine. Investigate persistent price revisions rather than bypassing validation or overwriting the ledger.

## Review an isolated provider revision

Decision Evidence offers **Review revised prices** only for isolated HISTORICAL_REVISION findings. The preview displays saved and provider OHLC values. Accepting needs a written reason, the control token and the exact current quality hash; concurrent evidence changes return 409. The server refuses non-revision anomalies, unknown instruments, pending orders or active positions without an explicit held-position incident review, incomplete evidence or revised batches failing current session/freshness checks.

An accepted correction records original and replacement candles in candle_revision_reviews and audit, then updates only the reviewed OHLC values in trusted saved candles. Original proposals, trades, research datasets and analysis snapshots are not rewritten. This is an explicit maintenance decision, not automatic acceptance of provider changes. The freeze remains until a separate deliberate resume passes the normal financial/data gates. Non-finite quarantined input values are retained as readable strings in evidence exports.

Read-only GET /data-quality/{symbol}/revision-preview provides comparison evidence; token-protected POST /data-quality/{symbol}/accept-revision records the reviewed correction. Neither creates a trading order.

### Held-position incident review

Ordinary review still refuses active positions. An explicit held_position_review flag, written reason, current hash and control token enable a separate guarded incident path. Pending orders always prevent correction. Each OHLC change must be at most 0.1% relative; this bound is a maintenance assumption, not a trading signal. Using saved history with replaced OHLC, the server compares protective-stop touch, opening-gap stop and 20-bar-MA exit predicates for every processed candle from the position entry through its checkpoint. Insufficient warm-up/history, no comparable processed bars or any changed predicate rejects the entire correction transaction. Existing quantities, stops, entry prices, cash and original trade contexts are never rewritten. The comparison result is recorded in the audit under the revision-review ID. A separate deliberate resume remains necessary.

This is a bounded retrospective consistency check, not a claim to reproduce every historical execution condition. Corrections that affect a past exit require separate incident resolution.

## Migration and recovery

Existing positions, trade contexts, exit queues, risk budgets and research history stay intact. Earlier trades are not assigned fabricated proposals or regime evidence. Unsigned legacy pending buys cannot satisfy the new contract: startup cancels them and preserves their original payload in a LEGACY_ORDER_CANCELLED audit event. They are not silently re-approved. New signed pending entries persist through restart. Rotating the control secret invalidates old signatures; old pending entries will be rejected rather than re-signed.

Back up consistently before deployment. The new tables are additive. Restoring older executable code removes these gates, so a rollback requires an explicit compatibility review and a stopped, protected ledger; it must not resurrect consumed approvals or cancelled legacy orders.

## Trade attribution

New trade context records instrument/strategy, entry and SPY regimes, ATR percentage, aligned relative-strength evidence, quality hash and decision IDs alongside existing execution costs. Closed results can be grouped by strategy, instrument, entry regime and exit reason, with net P/L, dollar expectancy, eligible R mean, estimated costs and legacy cost-record counts.

These are observed groupings, not causal explanations of wins/losses. Old missing regimes remain UNKNOWN. A small subgroup is not evidence of an edge. No regime filter/router, new exit, confidence calibration, MAE/MFE calculation, news restriction or automatic promotion is activated. Research on these features must use a separately versioned protocol without editing the existing reserved forward plan.

## API and storage

Authenticated read-only GET routes: `/controls`, `/decision-evidence`, `/attribution`, `/data-quality/{symbol}/history`. Viewing needs no control token and causes no provider request or order. Decision summaries default to 20 proposals with offset pagination and a 50 maximum. Data-quality history defaults to 10 and caps at 20 batches, including assessed input candles. Cryptocurrency symbols contain a slash and are not supported by the single-segment history route; their latest reports remain visible in decision evidence.

| New table | Key and payload |
| --- | --- |
| proposals | id PK; ts, symbol, immutable proposal JSON and digest |
| risk_decisions | id PK; proposal_id, ts, QUEUE/FILL phase, APPROVE/REJECT and full decision JSON |
| decision_consumptions | approval_id PK; unique trade_id and consumption time |
| candle_revision_reviews | id PK; symbol, time, quality hash, review reason, original/accepted candle evidence |
| quality_reports | symbol + context_hash PK; time and assessment/input-batch JSON |

The schema now has 22 tables. Relationships are application-enforced rather than SQL foreign keys. The latest quality report is also persisted under `quality:{symbol}` in state. API read caps do not delete history; storage growth remains operational maintenance work. Normal SQLite backups include all new records. Do not publish operational evidence exports, secrets or database backups in the public repository.

## Verification

47 backend tests passed: proposal mutation/replay/expiry/signature protection, fresh risk veto, rollback after consumption, restart, legacy migration, data quarantine, missing-session exits, holidays/early closes/DST, unmocked production session-calculation flow, authenticated read-only access and existing operation/research tests. Older operation fixtures intentionally use synthetic off-session times and mock the calendar assessor; separate control tests exercise the real assessor and one complete proposal-to-fill flow with controlled clocks.

Interface logic checks passed for escaped data-quality text, queue/fill trace, pagination and empty attribution, plus existing dashboard and specialty UI checks. A saved cloud-ledger copy passed calendar checks for all 16 US paper symbols before deployment. These checks are not a live visual/mobile/accessibility certification or evidence of profitability.

### Cloud acceptance — 10 October 2026

The release was deployed on the existing Oracle server. HTTPS authentication, scheduler health, restart recovery, ledger reconciliation, original entry history, numeric risk limits and the reserved forward-research protocol passed verification. The private Decision Evidence page is available at `/controls`; unauthenticated evidence requests return 401.

Later provider responses revised saved candles. The quality gate quarantined affected symbols and froze new entries. Maintenance reviews retained original and accepted OHLC evidence. Corrections involving held positions passed the stop, gap and moving-average exit predicate comparisons before acceptance; positions and original trade records were preserved. A larger opening-price correction on an unheld instrument was reviewed separately with no pending orders. These reviews did not increase the held-position correction tolerance. All 16 US quality gates passed and the desk was deliberately resumed after review.

There were no closed operational paper trades at acceptance and no proposals generated under the new contract yet. Contract execution was verified with controlled tests; deployment is not evidence of a profitable strategy. Live visual, mobile and accessibility verification remains outstanding. Subsequent provider revisions can legitimately trigger another quarantine requiring review.
