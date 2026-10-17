# Free historical price source review

[Open the private review](https://tcr.161-33-69-185.sslip.io/price-sources). This read-only investigation addresses ETF input blockers; it is not a strategy experiment, a replacement data feed or a new backtest.

## Bounded collection — 17 October 2026

A local plan was saved before four public requests: Yahoo chart history and Stooq downloads for GSG and IEF, restricted to 2006–2015. All responses and failures were retained. No retry, paid endpoint, credentials, Twelve Data credit or later-period price series was requested. Server recording occurs after collection and is explicitly not claimed as server preregistration before data.

Yahoo returned two daily USD ETF responses. Stooq returned HTML rather than historical CSV for both requests; no challenge or access restriction was bypassed. Source metadata is current, not a historical security master. Current quote metadata in the response is excluded from every historical diagnostic.

## Recorded findings

| Check | GSG | IEF |
|---|---:|---:|
| Returned daily sessions | 2,379 | 2,517 |
| First / last session | 21 July 2006 / 31 December 2015 | 3 January 2006 / 31 December 2015 |
| Meets original first-date requirement | No: original cutoff is 20 July 2006 | Yes |
| Missing SPY-proxy sessions after returned start | 0 | 0 |
| Overlapping sessions compared | 2,015 | 2,517 |
| Sessions with any OHLC difference above $0.02 | 390 | 0 |
| Largest OHLC difference | $2.9151 | about $0.000004 |

GSG supplies 364 sessions absent from the old saved response, but it is **not approved**. Its start still misses the fixed cutoff, and 390 overlapping sessions disagree: 253 in 2008, 113 in 2009 and 24 in 2010. Do not splice it into the old series, fit a scaling factor, shorten the registered period or move the cutoff to force acceptance. Verify early exchange history and price semantics against independent evidence first.

IEF's OHLC values corroborate the saved prices. All 120 issuer dividend ex-dates are present. Ninety-five published amounts fail the strict $0.0001 amount comparison; all 95 differences are compatible with nearest-three-decimal rounding (at most $0.0005). This precision classification was added after inspecting the discrepancies. It is descriptive and does not relax or clear the strict comparison.

The Yahoo adjusted-close ratio check reconciles all 120 issuer events at the original 0.0008 factor tolerance, compared with the 51 recorded failures in the saved Twelve Data adjustment series. This supports investigating adjustment coverage rather than changing the trading signal. It does **not** establish that Yahoo is fully accurate, independent of the original underlying data, or suitable for raw-price fills. The original mismatches remain recorded.

## Limits and next evidence

Both returned datasets are **QUARANTINED_SOURCE_CANDIDATE**. Raw fill-price semantics remain unverified, and an overlap match is not certification. Dividend amount/date comparison does not verify payable dates. A separate, versioned input revision would be needed before any replacement could be considered. No performance calculation or holdout test follows from this record.

GSG's issuer distribution supplement and IAU's split evidence remain separate from the original input bundle. IAU's full historical distribution coverage is still unknown. Original ETF DATA_BLOCKED status, all failed experiments, forward collection and operating risk limits remain unchanged.

The [Twelve Data adjustment guidance](https://support.twelvedata.com/en/articles/5179064-are-the-prices-adjusted) describes split adjustment and client-side corporate-action tools; it is not a certificate for the completeness of our saved dividend adjustments. The exact public publisher request URLs, dates, metadata and response hashes are retained in the authenticated review. Raw response data is private and is not committed to GitHub.

## Recording and storage

The fixed collector `ops/probe_free_sources.py` writes its plan before requests and refuses to rerun if that plan exists. It saves to ignored `data/free-source-probe-v1/`. It is not installed as an automatic task. No further request is made by viewing or recording the review.

`GET /price-sources` is the private read-only page. `GET /price-source-review` returns quality summaries, source identity and provenance. `POST /price-source-review/record` requires the existing control token, reads only fixed staged files, verifies hashes, and compares them with the immutable original ETF dataset. Repeat recording returns the original result. There is no raw-price export or source-activation endpoint.

`price_source_reviews` stores the plan/source identity, exact original dataset hash, calculation-source hash, summary hash and private source responses. Existing SQLite backups include the retained responses. Stored corruption suppresses positive summaries. The additive schema now has 38 tables. Encrypted off-server backups remain unconfigured.

Validation: 130 backend tests passed, including null/invalid/future data rejection, metadata checks, fixed OHLC tolerance, rounding without gate relaxation, HTML response rejection, source integrity, authentication, idempotence, original-row preservation and restart persistence.

## Saved-bar forensics — 17 October 2026

[GSG Data Integrity](GSG_DATA_INTEGRITY.md) records 253 consecutive saved 2008 GSG bars with identical OHLC and a separate issuer-range cross-check. It preserves this source review and all responses. It does not certify the alternative feed, replace any bar or change the original cutoff.
