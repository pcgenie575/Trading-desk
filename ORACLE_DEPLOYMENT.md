# Oracle Always Free deployment

Status (5 October 2026): deployed on an Always Free eligible AMD E2.1.Micro VM in Melbourne (1 GB RAM, 46.6 GB boot volume, 1 GB swap). The supplied Twelve Data key is installed in the protected server environment. Real SPY data is saved, the paper scheduler runs, and HTTPS health is healthy. Container restart and full VM reboot with the API key configured preserved ledger, checkpoint and audit history and restarted the scheduler. Five local tests passed, including risk circuit breakers, rollback, authentication and a simulated scheduler feed. Automatic daily backups retain 14 copies on the VM; an additional copy is downloaded locally. Automatic backups outside the VM are not configured. Strategy performance still requires forward observation.

Dashboard: https://tcr.161-33-69-185.sslip.io/

SSH is restricted to the authorized administration connection IP, 187.14.91.137/32. Update that rule if the connection's public IP changes. Public TCP access is limited to 80/443. The generated login details are in the separately supplied dashboard-access.txt; keep that file private. The VM has an ephemeral public IP, so its hostname must be updated if the address changes.

## Account and VM

Create an account at https://www.oracle.com/cloud/free/. Complete Oracle's identity/payment verification yourself. Keep account passwords and SSH private keys out of chat. Choose your home region carefully; free compute capacity is not guaranteed.

In the home region create an **Always Free eligible** VM.Standard.A1.Flex Ubuntu 24.04 VM with 1 OCPU, 2 GB RAM, and a 50 GB boot volume. Confirm the console shows Always Free eligibility, and account for all existing tenancy resources before creating it. Current public Free Tier limits list 2 OCPUs/12 GB total and 200 GB combined boot/block storage. If capacity is unavailable, try another availability domain in the home region; do not select a paid shape as a fallback.

Use a public subnet with an internet gateway. Allow TCP 22 only from your current IP, TCP 80/443 publicly. Match these rules in the guest firewall without removing Oracle's existing rules. Do not expose port 8000. Keep the boot volume when terminating a VM. Free instances can be reclaimed; a backup outside this VM is required for disaster recovery.

## Address and installation

Create a DNS A record for a domain/subdomain pointing to the VM public IPv4. A free DNS subdomain is an alternative if you do not own a domain. HTTPS setup requires control of the chosen address; do not put login credentials into an HTTP dashboard.

Install Docker Engine and the Compose plugin using Docker's official Ubuntu installation instructions: https://docs.docker.com/engine/install/ubuntu/. The Python base image supports Arm; the Docker build must be verified on the selected VM.

Upload this folder to `/opt/trading-control-room`. Create `/opt/trading-control-room/data`. Copy `.env.example` to `.env` and set:

```
TWELVE_DATA_API_KEY=<set directly on the server>
TCR_CONTROL_TOKEN=<long random token>
TCR_DASHBOARD_USER=operator
TCR_DASHBOARD_PASSWORD=<different long random password>
TCR_POLL_SECONDS=300
TCR_DOMAIN=<your dashboard hostname>
```

Generate both random credentials independently, for example with `openssl rand -hex 32`. Protect `.env` with `chmod 600 .env`. Never commit it. Confirm the Twelve Data plan supports SPY 4-hour history and sufficient API credits; a key alone does not guarantee access. No broker secrets are needed.

From the deployment folder:

```
docker compose -f compose.oracle.yml up -d --build
sudo cp ops/tcr-watchdog.service ops/tcr-watchdog.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tcr-watchdog.timer
```

Caddy obtains and renews HTTPS certificates using ports 80/443. The dashboard and APIs require Basic authentication. Freeze/resume/cycle also require the separate control token, requested by the dashboard. Only the minimal health endpoint is public. Run one application process and one container against this SQLite ledger.

## Backup and recovery

Schedule `python3 /opt/trading-control-room/ops/backup.py` daily as the server operator. It uses SQLite's online backup API and retains 14 copies. Save encrypted copies outside the VM as well. Same-volume copies cannot survive volume loss. OCI volume backup usage must remain inside the account's current free allowance.

To restore: stop the application, preserve the old DB, restore a verified backup to `data/control_room.db`, then restart. Never replace a database while the app is running. Startup preserves cash, positions, freezes, and the processed-candle checkpoint. A recovery history gap freezes entries for operator review. Missed bars are processed for exits; historical entries are skipped.

## Required validation before unattended operation

Run the included tests in a disposable environment with `pip install -r requirements.txt httpx` then `python -m unittest discover -s tests -v`. Do not point tests at the operational database.

Verify unauthenticated dashboard/API requests receive 401 and authenticated requests succeed over HTTPS. Confirm `/healthz` is healthy, `/status` reports a running scheduler, and audit messages show actual SPY completed bars without feed errors. A health check verifies the process/scheduler, not data freshness; inspect candle timestamps and audit errors separately.

Use a separate test ledger to verify deterministic entry/exit, gap-stop fills, duplicate prevention, cash/P&L, transaction rollback, $75 daily-loss and $250 drawdown breakers, and resume rejection while a breaker remains active. No synthetic bars should enter the operational ledger.

Record ledger state and audit IDs, restart the container, then reboot the VM. Verify the same balances/positions/freeze/checkpoint/audit history survive both, and the scheduler resumes. Stop the scheduler in a disposable test container and confirm the watchdog restarts the unhealthy container.

The application conservatively waits a full four-hour interval plus 15 minutes before using a candle. This can delay short final-session bars. It polls every five minutes but simulates fills from completed candles; protective stops are not real-time market orders. Actual feed entitlement, timestamps, session behavior, and provider delays must be checked with live data before accepting operation.
