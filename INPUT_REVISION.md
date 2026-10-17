# Action-based input revision draft

[Open the private input draft](https://tcr.161-33-69-185.sslip.io/input-draft). Version `etf-action-inputs-v2-draft` assembles data for methodology review. It does not rerun, amend or replace the original ETF experiment.

## Recorded draft — 17 October 2026

| Required component | Draft state | Basis |
|---|---|---|
| IWM | Assembled for review | Unchanged raw prices; reparsed original issuer file; original reconciliation retained |
| IEF | Assembled for review | Unchanged raw prices and exact issuer actions; separate adjustment reconstruction and publisher comparison |
| EFA | Assembled for review | Unchanged raw prices; reparsed original issuer file; original reconciliation retained |
| IAU | Blocked | Complete historical cash-distribution coverage remains unverified |
| GSG | Blocked | Early coverage and daily OHLC integrity remain unresolved |

**Three assembled components do not constitute a three-asset strategy test.** All five remain required in the manifest. The bundle materialises only the three reviewable components, and `require_complete` refuses partial drafts. Even a completed draft cannot start a simulator: this version has no recorded methodology approval or simulation capability. No performance, holdout or promotion follows.

## What changes for IEF in this draft

The original provider-adjusted series has 51 recorded reconciliation failures. It stays intact. This new draft uses the original explicitly unadjusted OHLC values and full issuer distribution records, including original precision and payable dates. It verifies the retained issuer file hash, reparses its complete distribution worksheet and checks that the events equal the saved original record.

The unchanged raw values agree with the retained alternative on all 2,517 sessions at the previously fixed $0.02 OHLC tolerance. The independent adjusted-close factors reconcile all 120 issuer events at the existing 0.0008 factor tolerance. A diagnostic history is reconstructed from issuer actions and compared with the independent adjusted closes after dividing each series by its own final retained close on 31 December 2015. This common relative-unit anchor removes an arbitrary historical adjustment scale; it is not a fitted parameter or replacement price. All 2,517 normalised levels match the same tolerance; the largest absolute normalised difference is about 0.0000330.

This is a newly declared **input methodology**. It does not silently clear the original price-provider check. Cross-source agreement does not certify every price or independent upstream data lineage. Yahoo's rounded dividend amounts are not substituted for the issuer amounts. IWM/EFA retain their original reconciliation route; they are not claimed to have received the same second-publisher coverage as IEF.

## Point-in-time boundary

Fully back-adjusted prices use future actions relative to early dates, so they are used **only for diagnostic comparison**. They are not included in the exported asset price inputs and never become opening fills. The draft contains unchanged raw bars and events whose ex-dates fall within the retained development period. Payable dates may extend beyond the final ex-date, preserving the original payment obligation.

Any future approved simulator must use raw fills and the existing `corporate_actions.signal_features` method, which rebases past signal prices only when an action becomes effective. Tests confirm a future action does not alter earlier feature snapshots. No future-price series, strategy calculation, asset substitution, shortened period or tolerance search is performed.

## Provenance, export and recovery

`input_revisions` records the fixed method, exact original ETF/source-review parents, source-code fingerprints, manifest hash, bundle hash and private original issuer files. Three original XML files are retained inside the database, so the bundle's issuer evidence is included in SQLite backups. Their full contents are excluded from the normal draft export. Original raw data, source probes, issuer audit and failed research records are preserved. The additive schema now has **39 tables**.

Authenticated reads: `/input-draft`, `/input-revision`, `/input-revision/bundle`. The private JSON export includes the manifest, component provenance, unchanged raw bars and issuer events. Do not publish it to GitHub. A control-token-protected `POST /input-revision/build` builds this version once from retained sources; repeated calls return the original result. It makes no source requests. Source-file, response, event or bundle integrity failures stop construction/export without fallback.

No approval or activation endpoint is supplied. These files do not change live trading, risk limits or the original ETF protocol. Missing IAU/GSG evidence remains mandatory. Investor withholding, tax, historical announcement availability and an independently certified exchange calendar remain limitations. Encrypted off-server backups are still unconfigured.

Validation: 140 backend tests passed, including issuer/source hashes, original raw-data preservation, no omitted required assets, separate diagnostic adjustments, effective-date isolation, partial-draft refusal, authenticated exports, one-time construction, restart persistence and corruption suppression.
