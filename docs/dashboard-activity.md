# Dashboard activity banner

The home page explains why a swing desk can look quiet. It shows a regular US stock-session estimate, the next regular opening in Perth time, latest scheduler checkpoint, latest successful stock-data fetch, latest processed stock candle (start timestamp, New York time) and latest stock audit event. Crypto observations do not masquerade as stock trading activity.

Priority: risk freeze; stopped/missing/stale scheduler; feed errors; outdated active-position fetch during an open regular session; recent recorded stock candle; open-session waiting; closed-session waiting. A dashboard request failure explicitly marks displayed values as old. Normal waiting is visually separate from warnings.

Clock correction deployed 14 October 2026 (Perth): the home page captures the HTTP Date on its authenticated status response and uses that clock for both session estimates and checkpoint age. This prevents a fast or slow device clock from creating false scheduler warnings or shifting the displayed session. Missing server clock information produces an explicit warning, not a guessed session. Tests cover a device one hour ahead, genuinely stale checkpoints with server time, and a missing response timestamp. Authenticated delivery of the corrected script and status-response clock binding was verified after deployment and service restart. Paper positions and risk limits remain unchanged.

The schedule handles US daylight saving, weekends, NYSE holiday closures and early closes for 2026–2028. It is a pinned display calendar, not a live halt feed or a trading control. Outside its covered years the next opening is unavailable. Provider delay and candle completion are distinct from dashboard refresh. No strategy, ledger, requests budget, risk limits or frozen protocol changes.

Calendar source: [official NYSE calendar and hours](https://www.nyse.com/trade/hours-calendars), checked 11 October 2026. Unscheduled closures and feed differences remain possible. Tests cover weekends, holidays, daylight saving, early closing, Perth formatting, unsupported calendar years, risk freezes, feed/scheduler failures and dashboard connection loss. All 75 existing backend tests pass.

A browser policy block prevented direct visual inspection of the live page. UI logic and authenticated delivery checks are used; visual acceptance remains outstanding.

Deployment status: live on the existing Oracle VM, verified 12 October 2026 (Perth). Restricted SSH access was restored with the user's approval. A database backup was taken before deploying. After the service rebuild and restart, health and the scheduler were verified, authenticated HTML and activity-script delivery passed, and an unauthenticated script request returned 401. The AAPL/SPY paper positions, risk limits and forward research plans matched their pre-deployment snapshots. This deployment changes the display only; it does not generate trades or relax entry rules.
