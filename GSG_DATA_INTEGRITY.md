# GSG saved-bar integrity investigation

[Open Data Integrity](https://tcr.161-33-69-185.sslip.io/data-integrity). This investigation uses retained ETF data, the already saved Yahoo response and numerical issuer-table references. It makes no new historical-price requests, changes no dataset and runs no strategy test.

## Concrete finding — 17 October 2026

Every one of the saved GSG series’ **253 daily observations in 2008** has identical open, high, low and close. All saved volume fields are zero. The original adapter can normalise missing volume to zero, so these fields do not prove there was no actual trading. The already retained alternative has nonzero high–low ranges on all 253 dates.

This is insufficiently corroborated input for opening-gap, stop-hit and excursion replay. It is a source-integrity problem to investigate, not evidence of a profitable or losing trading signal. The cause has not been established: do not claim that the vendor fabricated prices or that the series is NAV.

The reusable `input_integrity.audit_bars` tool flags five consecutive **observed** flat OHLC bars for review, reports run dates, counts and yearly summaries, and never certifies a feed. This review threshold was chosen after observing the GSG anomaly; it is not a validated statistical test. A halt or illiquidity can legitimately produce flat bars. Its absence is not a pass for all other data checks.

The same saved-input check found no five-session flat run in IWM, IEF, EFA or IAU. That does not resolve their other data requirements or certify those feeds. This tool is an isolated diagnostic; it does not modify the frozen live data-quality code or registered research gates.

## Independent issuer cross-check

Numerical Item 5 references cover 18 quarters from 2006 Q3 through 2010 Q4:

- [2007 filing: 2006 Q3–Q4](https://www.sec.gov/Archives/edgar/data/1346616/000119312508055731/d10k.htm).
- [2008 filing: 2007–2008](https://www.sec.gov/Archives/edgar/data/1346616/000119312509040488/d10k.htm).
- [2009 filing: 2009](https://www.sec.gov/Archives/edgar/data/1346616/000119312510043163/d10k.htm).
- [2010 filing: 2010](https://www.sec.gov/Archives/edgar/data/1332174/000119312511047523/d10k.htm).

The source label describes quarterly high and low sale prices. Both intraday extrema and closing extrema are retained at the previous source review’s fixed $0.02 tolerance:

| Series | Quarters with observations | Intraday-extrema matches | Closing-extrema matches |
|---|---:|---:|---:|
| Saved Twelve Data GSG | 12 | 0 | 7 |
| Retained Yahoo GSG | 18 | 0 | 18 |

The closing-extrema comparison was added after observing the table mismatch. Its agreement supports further investigation of the saved series, but it is exploratory aggregate corroboration. It does not verify every daily close, raw opens/highs/lows, first trading date or a replacement feed. Both interpretations remain visible; the issuer label is not silently rewritten.

Facts were manually transcribed from the accessible primary filing tables. The fact hash binds that transcription, not the original filing bytes. Full archives and amendment review remain incomplete. GSG still misses the fixed early-history cutoff, and its daily-price discrepancies remain unresolved. No cutoff, tolerance, source or symbol was changed to obtain a pass.

## Record and access

The fixed investigation is retained as `gsg-ohlc-forensics-v1` in the existing `price_source_reviews` table, alongside the preserved `free-source-probe-v1` parent. The schema remains at **38 tables**. Its protocol binds the exact original ETF dataset, complete parent source record, publisher response, transcribed issuer facts and calculation-source fingerprints. SQLite backups retain the record and its referenced original/parent data.

Authenticated reads: `/data-integrity` and `/gsg-forensics`. The control-token-protected `/gsg-forensics/record` reads only those retained records, verifies hashes, calculates once and returns the original result on repeat. It fetches nothing and has no source-approval or strategy-activation capability. Tampered summaries do not produce positive displays; source/fact drift is separately reported.

Original research, source probes, issuer evidence, forward collection, trades, cash, costs and numerical risk limits remain unchanged. All source candidates remain quarantined. No backtest, holdout evaluation or promotion followed this diagnostic.

Validation: 136 backend tests passed, including flat-run review without certification, invalid data, separate intraday/closing comparisons, parent-response tampering, reference scope, escaped rendering, authentication, idempotence, restart persistence and preservation of original records.
