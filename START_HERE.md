# Trading Desk — Start Here

## Open the dashboard

**[Open Trading Desk](https://tcr.161-33-69-185.sslip.io/)**

This is the autonomous **paper-trading** dashboard. There is no broker connection or real-money trading.

## Sign in

1. Open the dashboard in Chrome or Edge.
2. When the browser asks for a username and password, use **operator** and your saved **dashboard password**.
3. The credentials are in the local file `outputs/dashboard-access.txt` in this project's workspace. Keep this file private; it is not stored in GitHub.

The control token is separate from the login password. It is needed only for dashboard controls such as freeze, resume, or a manual cycle.

If you see `ERR_INVALID_AUTH_CREDENTIALS`, try Chrome Incognito or Edge InPrivate and enter the saved dashboard password again. The in-app browser may have trouble with the browser login prompt. Never put the password in a URL.

## Useful links

| Link | Purpose |
| --- | --- |
| [Dashboard](https://tcr.161-33-69-185.sslip.io/) | Account equity, positions, audit feed and controls |
| [Health check](https://tcr.161-33-69-185.sslip.io/healthz) | Minimal public service health; expected status is `ok` |
| [Project repository](https://github.com/pcgenie575/Trading-desk) | Source code, tests and documentation |
| [Oracle server](https://cloud.oracle.com/compute/instances/ocid1.instance.oc1.ap-melbourne-1.anwwkljr3psanaictrfbe3wocswuodjyqu2ur3nf4bz4bdhg5fb6d3kuoigq?region=ap-melbourne-1) | VM management; Oracle sign-in required |
| [Twelve Data account](https://twelvedata.com/account) | Market-data account; sign-in required |
| [Deployment and recovery guide](ORACLE_DEPLOYMENT.md) | Server configuration, backups and recovery |

## Check operation

**Agent learning** shows the five-book curriculum and what each agent applies.
Read [Agent learning guide](AGENT_LEARNING.md) for the coded checks and research
boundaries. The agents use rule-based software; this does not claim model
fine-tuning or full-book ingestion.

Use **Journal & analytics** for swing-trade outcomes, holding periods and saved
reviews. **Plan & playbook** contains the active strategy and a scenario calculator.
Read [Swing journal guide](SWING_JOURNAL.md) for metric definitions. New trade plans
are captured automatically; earlier trades are labeled when an original plan is
unavailable. Select a trade and use your control token to save its review.

Look for a running scheduler, advancing completed-candle timestamps, and new audit entries. The agent flow diagram animates new recorded messages; quiet links are normal between events. Select any agent for details. Polling runs every five minutes; decisions use completed four-hour candles across the bounded free-data watchlist, so a new trade is not expected every poll. Open positions receive priority refreshes every 15 minutes. Public health checks confirm scheduler/process health, not market-data freshness. Check the Market coverage table for each symbol's actual data status.

Last live verification: **10 October 2026 (Perth)**. The updated agent-flow dashboard was served over authenticated HTTPS, all 18 watchlist symbols returned data, and the scheduler was running. A container restart preserved positions, audit records, per-symbol checkpoints and request-budget counters; the cash ledger reconciled and the downloaded backup passed its integrity check. Two paper positions, SPY and AAPL, were open. This is a dated observation, not a continuously updated status report.

Animations follow newly received audit messages and run once per event; they stay still between messages. Older history is available by clicking an agent and in the audit feed. Reduced-motion preferences replace moving lights with link highlights. The automated interaction checks passed; a browser visual preview could not be completed in this session because local preview access was blocked.

Paper limits: $5,000 starting balance, three positions maximum, $1,500 aggregate entry exposure, $500 maximum per position, $25 planned loss per trade and $75 aggregate planned loss, $75 daily-loss stop, and $250 drawdown freeze. Crypto is observation only. See [Free-data coverage and limitations](MARKET_EXPANSION.md).

## Backups and access

Daily backups run on the VM. An additional ledger copy has been downloaded locally; automatic off-server backups remain unconfigured.

The server uses an ephemeral public IP. If Oracle changes it, the dashboard address and deployment configuration must be updated. SSH administration is restricted to an approved connection IP and may need updating when that IP changes.

## Research Lab & Knowledge

[Open the knowledge base](https://tcr.161-33-69-185.sslip.io/research) to save lessons, research ideas and experiment evidence. See [RESEARCH_LAB.md](RESEARCH_LAB.md) for approval, agent assignment and revision history.
