# Trading Control Room — Paper Operations

For the prepared Oracle Cloud deployment, follow **ORACLE_DEPLOYMENT.md** and
use **compose.oracle.yml**. The original Docker instructions below describe local
operation only. Dashboard authentication and a control token are now mandatory.
The Oracle deployment is operational in paper mode; see the deployment guide for
verified behavior and remaining limitations.

Project repository: https://github.com/pcgenie575/Trading-desk

This is the consolidated autonomous **paper-trading** release.

## Operational flow
Market Data → Analyst → Risk & Compliance → Paper Trader → Logger
                                  ↑
                              Supervisor
Performance Reviewer reads completed results and reports to Supervisor.

## What is autonomous
- Fetch SPY 4-hour data on a schedule
- Deduplicate completed candles
- Run the fixed Trend Breakout v1 Analyst
- Apply deterministic risk checks
- Open a simulated long position when approved
- Monitor protective-stop and 20-SMA exit rules
- Close simulated positions automatically
- Maintain cash, equity, realized/unrealized P/L
- Enforce $75 daily realized-loss stop
- Enforce $250 peak-to-equity drawdown freeze
- Persist positions, candles, messages and reviews in SQLite
- Recover persistent state after process/container restart
- Maintain the visible inter-bot audit feed

## Fixed paper limits
- Starting balance: $5,000
- SPY only
- Long only
- No leverage
- One position at a time
- Max position: $500
- Max planned loss: $25
- Daily realized-loss freeze: $75
- Drawdown freeze: $250

## Strategy
- Trend filter: completed close > 50-bar SMA
- Candidate: completed close > prior 10-bar high
- Exit: 5% protective stop OR completed close < 20-bar SMA
- 2 bps simulated slippage each side

## Security
Set `TCR_CONTROL_TOKEN`. Mutating controls (manual cycle, freeze, resume) require it.
For internet deployment, put the service behind HTTPS and provider/firewall access controls.

## Run with Docker
1. Copy `.env.example` to `.env`
2. Set `TWELVE_DATA_API_KEY`
3. Set a long random `TCR_CONTROL_TOKEN`
4. Run:

```bash
docker compose up -d --build
```

Open `http://SERVER_IP:8000`.

## Run without Docker
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

## Validation before considering any live-money project
Do not judge the system from a handful of trades. Leave it in paper operation and review:
- data-feed reliability and missing/stale bars
- duplicate prevention
- restart/recovery behavior
- every Risk rejection
- realized and unrealized P/L accuracy
- daily/drawdown circuit breakers
- trade count and win/loss distribution
- maximum drawdown
- backtest vs forward-paper performance
- whether the strategy's apparent edge survives realistic costs and different market regimes

## Deliberate boundary
There is **no broker adapter, broker credential storage, or live-order endpoint** in this release.
That is intentional. A future live-money version should be a separately reviewed deployment after
forward-paper evidence, security review, failure testing, and explicit approval.
