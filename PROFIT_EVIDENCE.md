# Profit, research readiness and the evidence lab

Open the private [Profit & Evidence workspace](https://tcr.161-33-69-185.sslip.io/evidence). Its data endpoints use existing dashboard authentication; isolated replay additionally requires the existing control token. Source and this guide are public. Trading records, inputs and credentials remain private.

## 1. Reconcile every dollar

`/profit-evidence` bridges the unchanged USD ledger to recorded execution evidence. New entry and exit fills save immutable spread, slippage, commission and FX components in the same transaction as the trade. Old entry contexts and original exit audit payloads can provide existing evidence without rewriting a trade.

Missing legacy components remain unknown. A zero fee column is not proof of free execution. Gross P/L is available only when all required fill evidence is present. Spread/slippage already affect execution prices; adding costs back explains gross results, and subtracting them again from net would double count them. Cash/equity residuals and mark freshness expose accounting discrepancies separately from feed problems. Open P/L excludes future liquidation costs. Costs remain conservative model estimates, not verified Webull tariffs or AUD investment returns.

## 2. Repair inputs before judging ETF performance

The workspace shows the existing ETF input failures and specific corrective actions. Original protocols, datasets and negative results are preserved. No automatic retries, paid feeds, shortened warmup period or tolerance relaxation is introduced.

An independent issuer announcement confirms IAU's ten-for-one split became effective for NYSE Arca pricing on 24 June 2010: [SEC-filed issuer announcement](https://www.sec.gov/Archives/edgar/data/1278680/000119312510137666/dex991.htm). This comparison fact does not clear missing distribution history, mismatched provider dates or incomplete GSG/IEF inputs. A current fact sheet saying no regular distribution is not complete historical evidence for 2006–2015. The ETF experiment remains blocked until all its registered checks pass using verified inputs. Repairs require a separately versioned input record; old experiments are never overwritten.

## 3. Replay the actual operational engine

`POST /evidence-lab/replay` first registers a source fingerprint and dataset hash, then runs at most 500 saved US provider-batch observations in a subprocess and a temporary database. A virtual clock uses the original observation times. Shared `process_received_bars` dispatch invokes the actual session-quality checks, proposal signatures, next-eligible-open queue, execution costs, portfolio overlap gates, protective exits, circuit breakers and ledger functions. No scheduler or provider worker is started. Provider calls are disabled. Each identical input/source combination runs once; interrupted or failed runs remain recorded.

This is a descriptive operational diagnostic, not the daily portfolio development experiment or a new strategy-validation trial. Saved quality reports deduplicate unchanged polls; manual historical revisions/resumes, unrecorded outages, liquidity and broker execution cannot be reconstructed. A replay can therefore remain frozen while the real desk was manually recovered. The existing daily multi-asset simulator remains a separate development tool with its documented corporate-action and timing limitations. Neither result activates anything.

## 4. Journal unexecuted decisions

New rejected/expired entries, data blocks, freezes and exit intentions create deduplicated shadow observations linked to the audit message. No old decisions are fabricated. Follow-up shows only a later observed price range, beginning strictly after the observation and next eligible opening timestamp. It does not assume a fill, ignore a stop, or label a rejected trade as lost profit. Historical revisions may affect these later descriptive ranges. Missing outcomes remain unknown.

## 5. Register one frozen comparison

On initial deployment, a persistent collection plan references the existing fixed controlled-learning breakout/trailing-exit experiment and snapshots the baseline's engine/risk settings. It collects first validated SPY observations only when the candle opened after registration. Stored comparison observations are immutable and restart safe. A source fingerprint change stops collection and requires protocol review; it cannot silently create another candidate.

The controlled-learning milestone of 30 closed trades and its development, cost-stress and future-data screens remain in force. Candidate orders remain disabled. Until those gates pass, this is future evidence collection, not an active challenger portfolio. Existing failed experiments are neither rerun nor replaced. No automatic promotion is enabled. Forward comparison still requires the previously declared sample size and portfolio validation before an operator could consider any software activation.

## Storage and operation

Five additive tables bring the database to 33 tables: `execution_evidence`, `shadow_observations`, `paired_collection`, `paired_observations` and `engine_replays`. Backups include them. Raw replay datasets and results stay in the private database; capped API lists do not delete historical records. Operator retention and resource monitoring remain necessary as data grows. Replay has a fixed 120-second limit and a single worker; run it outside market hours on the small free VM.

Deployment acceptance must verify authentication, ledger/risk preservation, the registered plan, zero accounting residuals, replay isolation and persistence after restart. The strategy, costs, risk limits, operational ledger, free-data budget and broker exclusion remain unchanged. These features improve evidence quality; they do not establish profitability.
