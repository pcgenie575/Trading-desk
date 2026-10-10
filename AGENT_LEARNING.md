# Book-informed agent curriculum

Version: `book-curriculum-v1`. The operating agents are deterministic software.
Teaching here means coded checks, decision annotations, provenance and review
guidance. No AI model was fine-tuned, no full book was ingested, and no purchase
or paid service is required.

## Five books selected for this desk

This is a fit-for-purpose selection, not a claim of an objective global ranking.
Original lessons use public author/publisher descriptions rather than copied
chapters or reconstructed proprietary systems.

| Book | Author | Lesson focus | Primary source |
| --- | --- | --- | --- |
| The New Trading for a Living | Alexander Elder | Defined plans, risk and records | [Author](https://www.elder.com/books), [publisher description](https://uat.store.wiley.com/en-us/the-new-trading-for-a-living-psychology-discipline-trading-tools-and-systems-risk-control-trade-management-p-9781118443927) |
| Trade Your Way to Financial Freedom | Van K. Tharp | Position sizing, exits and R distributions | [Author's institute](https://vantharpinstitute.com/product/trade-your-way-to-financial-freedom/) |
| Trading in the Zone | Mark Douglas | Consistency across uncertain outcomes | [Publisher](https://www.penguinrandomhouse.com/books/350665/trading-in-the-zone-by-mark-douglas/9781440625411/) |
| Trade Like a Stock Market Wizard | Mark Minervini | Trend-oriented stock selection and capital preservation | [Publisher](https://www.mheducation.com/highered/mhp/product/trade-like-stock-market-wizard-how-achieve-super-performance-stocks-any-market.html) |
| Evidence-Based Technical Analysis | David R. Aronson | Objective tests and data-mining bias | [Publisher](https://onlinelibrary.wiley.com/doi/book/10.1002/9781118268315) |

## What runs in software

- **Market Data:** existing instrument/currency/OHLC/completed-bar validation and
  coverage reporting remain the data-quality foundation.
- **Analyst:** fresh entry analyses attach source IDs, curriculum version and
  objective trigger/sizing observations to the audit record. These annotations
  do not change the existing 50-bar/10-high entry rules.
- **Risk & Compliance:** a new arithmetic gate verifies that quantity times
  reference entry equals proposed capital, and quantity times entry-stop equals
  stated planned loss. It rejects mismatches, non-finite/non-positive values and
  invalid long stops before the existing portfolio limits. This calculation
  describes pre-execution stop risk; simulated fills still apply slippage and
  clamp the actual position to the existing caps.
- **Paper Trader:** existing fixed risk limits, sizing, protective stops and
  exits continue. A loss or win does not automatically increase risk.
- **Logger:** new plans capture curriculum version, learning annotations and
  their original configuration. Historical missing context is not backfilled.
- **Supervisor:** startup runs six positive/negative sizing/evidence self-checks
  and records the curriculum load. Existing freezes and restart recovery remain
  active. Passing these checks validates those code scenarios, not trading skill.
- **Performance Reviewer:** saved reports include eligible R count, mean R,
  current closed-trade loss streak and outstanding evidence requirements.

The dashboard's **Agent learning** section shows the books, role assignments and
active checks. Clicking an agent also shows its guidance. Authenticated
`/training` exposes the curriculum and an evidence review without writing a
report or consuming a market-data credit.

## Knowledge, tools and memory

[Analyst Brain](https://tcr.161-33-69-185.sslip.io/analyst) combines the curriculum with descriptive analysis tools and recorded experience. Four of the five installed book lessons are assigned to Analyst. Only approved lessons assigned to that role appear in its context; drafts, hypotheses and experiment notes cannot execute instructions. Custom lesson changes require evidence, assignment, approval and a version check. Earlier analysis/trade snapshots retain their original lesson versions.

The Brain shows trend/slope, SPY context, aligned relative returns, ATR/RSI, same-session volume and extension/structure flags from saved completed candles. New processed candles preserve reports; startup seeds saved-data reports. Viewing previews current cached context without creating orders or requesting new provider data. Experience is the most recent up to 100 closed paper trades across the desk, not a trained predictive model. See [Analyst Brain guide](ANALYST_BRAIN.md) for calculations and practical use.

## Research boundaries

Thirty eligible closed trades is our initial review milestone, not a threshold
prescribed by these books or proof of statistical significance. Reaching it never
sets `edge_validated` to true. Out-of-sample results, execution/cost sensitivity,
correlated observations and multiple strategy trials require further analysis.
Any future entry/exit variant must be versioned and compared in an isolated
paper/backtest run before being activated.

Minervini's complete SEPA process and Elder's specific multi-timeframe systems
are not implemented by these lessons. The existing four-hour free-data feed does
not supply the required full daily/weekly history, fundamentals and stock-ranking
coverage. Those ideas remain research items. A public book description is not a
substitute for studying the full licensed text.

## Validation and recovery

Tests cover correct and dishonest sizing, invalid values/stops, R arithmetic,
sample gates that never declare a proven edge, authenticated curriculum access,
entry/exit/risk limits and journal persistence. Deployment takes a consistent
ledger backup, preserves existing positions/checkpoints, verifies authenticated
HTTPS and restarts the service. Source lives in the private project repository.

Paper only, free data only; no broker or real-money connection is added.
