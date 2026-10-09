# Webull Australia market expansion

Scope confirmed by the operator: Webull Australia. Paper execution only; no broker connectivity.

## Verified product scope

Verified 10 October 2026 using Webull Australia's product pages:

- Australian shares and ETFs on ASX/Cboe, and listed warrants: https://www.webull.com.au/au-stocks
- US shares and ETFs: https://www.webull.com.au/us-stocks
- Hong Kong and eligible China Stock Connect shares/ETFs: https://www.webull.com.au/a-hk-shares
- US equity/index options: https://www.webull.com.au/
- Cryptocurrencies through Webull Pay Australia: https://www.webull.com.au/crypto
- Margin and short selling are execution features, not independent instrument universes.
- Auto-investing, portfolios and cash management require separate product/accounting models.

Do not infer Australian availability from Webull US or Hong Kong product pages. An exchange listing alone does not prove a security is available through Webull Australia. The complete current tradable-symbol/contract list must be verified against Webull's catalogue before claiming full coverage.

## Existing data entitlement check

The supplied Twelve Data key returned four-hour AAPL and BTC/USD data. ASX BHP, HKEX 0700 and SSE 600519 returned explicit Pro/Venture subscription requirements. This checks representative instruments; it does not prove complete market access. BTC/USD came from Binance and is not a Webull execution quote.

Twelve Data Basic advertises 8 API credits per minute and 800 per day: https://twelvedata.com/pricing

Scanning thousands of instruments every five minutes exceeds that allowance. The operator authorized free data only. No paid subscription or broker connection is configured.

## Required implementation

1. Instrument identities must include exchange, asset type, quote currency and timezone; identical ticker text must not collide.
2. Store candle checkpoints, positions and performance per instrument, with a portfolio-level USD cash/equity ledger and explicit FX marks for non-USD prices.
3. Apply aggregate portfolio exposure and risk limits; retaining a $25 limit per symbol without an aggregate cap would multiply account risk.
4. Use instrument-specific session calendars, stale-data policies, quantity increments, lot sizes, fees and order restrictions.
5. Options require expiry, strike, put/call, multiplier, bid/ask, assignment/exercise and expiration accounting. Warrants require issuer terms, maturity and settlement models. Neither may be simulated as ordinary stock shares.
6. Short positions require borrow availability/cost and unlimited-upside risk handling. Margin requires maintenance/liquidation accounting. These remain disabled until implemented and tested.
7. Preserve the existing SPY position and ledger during migration. Validate exits, restart recovery, duplicate prevention, FX and aggregate circuit breakers in isolated test ledgers before activation.

## Current operational status

The free-data engine uses this bounded watchlist: SPY, QQQ, IWM, DIA, AAPL, MSFT, AMZN, NVDA, GOOGL, META, TSLA, AMD, JPM, XOM, GLD, TLT, BTC/USD and ETH/USD. This is not the complete Webull tradable catalogue and availability of each instrument in a Webull account is not guaranteed.

The 16 US instruments are eligible for simulated long entries under the existing fixed strategy. BTC/USD and ETH/USD are observation only: Webull execution fees/spreads are not modeled. Australian, Hong Kong and China shares, options and warrants remain unavailable under the current free-data/model coverage. Margin and short selling remain disabled.

Every five minutes the scanner advances one watchlist item, so a full rotation normally takes about 90 minutes. Open positions receive priority refreshes every 15 minutes. These are completed four-hour candles, not live execution quotes. US entries are skipped when candle timestamps are older than 24 hours. Existing positions are reviewed for exits even while new entries are frozen.

Budget counters persist in SQLite: at most six requests per minute, 600 daily credits for new scans/backtests, and 720 total including prioritized position refreshes. The first deployment seeds usage already spent by the previous SPY scheduler. Counters reset by UTC date; external use of the same API key is outside this application's counter and can still exhaust the provider allowance. Budget exhaustion and feed failures appear in the dashboard coverage panel.

Portfolio limits are three open positions, $1,500 aggregate entry exposure and $75 aggregate planned loss, retaining $500/$25 per position, $75 daily realized-loss and $250 drawdown circuit breakers. Planned loss is a model, not a guarantee against price gaps. Marks, checkpoints, candles and audit messages are keyed by symbol. The original SPY checkpoint and positions are retained without resetting cash.

The automated checks cover multi-symbol marks and exits, independent checkpoints, duplicate prevention, portfolio limits, daily/drawdown freezes, persistent request budgets, restart recovery and crypto observation without entries. Live deployment evidence is recorded separately; a product listed above is not a claim of complete market coverage.
