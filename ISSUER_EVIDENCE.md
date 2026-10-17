# Issuer source evidence audit

[Open the private source audit](https://tcr.161-33-69-185.sslip.io/issuer-sources). Recorded facts supplement the saved ETF input investigation; they never replace its dataset or clear a gate. This is data work, not another strategy trial.

## Findings reviewed 17 October 2026

Five explicit GSG Item 5 statements report no shareholder distributions over contiguous periods from 10 July 2006 through 31 December 2015:

| Period covered | Primary filing |
|---|---|
| 10 July 2006–2007 | [2007 joint filing](https://www.sec.gov/Archives/edgar/data/1346616/000119312508055731/d10k.htm) |
| 2008–2009 | [2009 joint filing](https://www.sec.gov/Archives/edgar/data/1346616/000119312510043163/d10k.htm) |
| 2010–2011 | [2011 filing](https://www.sec.gov/Archives/edgar/data/1332174/000119312512088566/d274091d10k.htm) |
| 2012–2013 | [2013 filing](https://www.sec.gov/Archives/edgar/data/1332174/000143774914003127/gsg20131231_10k.htm) |
| 2014–2015 | [2015 filing](https://www.sec.gov/Archives/edgar/data/1332174/000143774916027698/gsg20151231_10k.htm) |

The first two are joint Trust/Investing Pool filings indexed under the Pool CIK. Their Item 5 statements explicitly describe GSG Trust shareholders. This supports absence of shareholder distributions for those stated periods, not absence of futures income, tax allocations or redemptions. Coverage starts at commencement; no pre-inception prices or events are invented.

The [IAU issuer announcement](https://www.sec.gov/Archives/edgar/data/1278680/000119312510137666/dex991.htm) supports a ten-for-one split with NYSE Arca split-adjusted trading beginning 24 June 2010. The source audit compares that effective date and ratio with the saved provider-inferred split. The Toronto effective date differs and is not used for this USD instrument.

## What remains blocked

- GSG: verified early daily OHLC history is still missing. Its original missing-worksheet failure is preserved; using a different action-source format requires an explicit reproducible input revision, not a silent rerun.
- IAU: full 2006–2015 cash-distribution coverage is still unknown. A current frequency of “None,” absent spreadsheet or gold redemption accounting does not certify that whole historical period.
- IEF: 51 issuer/provider adjustment discrepancies still need independent reconciliation.
- All ETFs: Webull Australia eligibility remains separately unverified. No development performance, holdout test or trading activation follows from this audit.

## Evidence retention and limits

Direct automated SEC downloads returned HTTP 403. The accessible research tool returned filing excerpts; these excerpts are retained privately with their source URLs and SHA-256 hashes. They are **not original SEC filing byte archives**. The catalog explicitly records the distinction. No access restriction was bypassed. Full original archive retrieval and amendment review remain limitations; this supplemental audit is not a complete corporate-action certification.

The public catalog contains only reviewed scope, source URLs, capture hashes and limitations. Private captured text is recorded once into `issuer_evidence`, included in the existing SQLite backup, and available only through authenticated source exports. This is retrospective source evidence, not proof of announcement-time availability.

## Controls

`GET /issuer-sources` renders the read-only page; `GET /issuer-audit` reports the immutable audit and original input blockers; `GET /issuer-audit/source/{capture_id}` exports retained text after integrity verification. `POST /issuer-audit/record` requires the existing control token, accepts only the deployed fixed catalog and pre-staged files, and returns the original record on repeat. It fetches nothing and starts no simulation.

Missing excerpts, changed hashes, unsupported sources, gaps, overlaps, incorrect split scope and missing explicit statements fail closed. Original research rows, prices, results, performance gates, live strategies, limits and ledgers remain unchanged. No new data credits or paid services are used. Captures are local and in VM SQLite backups; encrypted off-server backup remains unconfigured.

Validation: 124 backend tests passed, including source-tampering rejection, exact period coverage, authenticated recording/export, one-time registration, restart persistence and preservation of original input blockers.
