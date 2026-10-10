# Daily data layer — current implementation

`market_data.py` supplies budgeted daily OHLCV pages with symbol, currency, exchange and interval validation. `daily_research.py` retains accepted pages and explicit boundary supplements. `etf_lab_api.py` saves raw, split-adjusted and total-adjusted prices separately and original issuer records privately with hashes. Dataset/protocol hashes are stored before calculation.

`corporate_actions.py` checks chronological finite OHLC, matching date sets, saved SPY session coverage, adjustment factors and issuer cash distributions. It computes action-rebased signals using effective-date information and raw fills. Missing distribution worksheets are UNKNOWN, not zero. SPY is a session proxy, not a certified historical calendar. No independent second-price-source validation or validated ASX feed is claimed.

Recorded gate: IWM/EFA passed; IEF dividend adjustment mismatches, IAU unverified action coverage and GSG history starting too late blocked the ETF run. Earlier daily price-only results retain their original limitations. Saved inspected history is not a fresh holdout. Viewing results does not fetch data. No replacement symbols, paid fallback or relaxed gate was used.
