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

Look for a running scheduler, advancing completed-candle timestamps, and new audit entries. Polling runs every five minutes; trading decisions use completed SPY four-hour candles, so a new trade is not expected every poll. Public health checks confirm scheduler/process health, not market-data freshness.

Last live verification: **9 October 2026**. The service was healthy, the scheduler was running, and one SPY paper position was open. This is a dated observation, not a continuously updated status report.

Paper limits: $5,000 starting balance, $500 maximum position value, $25 maximum planned loss per trade, $75 daily-loss stop, and $250 drawdown freeze.

## Backups and access

Daily backups run on the VM. An additional ledger copy has been downloaded locally; automatic off-server backups remain unconfigured.

The server uses an ephemeral public IP. If Oracle changes it, the dashboard address and deployment configuration must be updated. SSH administration is restricted to an approved connection IP and may need updating when that IP changes.
