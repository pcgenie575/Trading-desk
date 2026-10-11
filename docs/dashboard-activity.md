# Dashboard activity banner

The home page explains why a swing desk can look quiet. It shows a regular US stock-session estimate, the next regular opening in Perth time, latest scheduler checkpoint, latest successful stock-data fetch, latest processed stock candle (start timestamp, New York time) and latest stock audit event. Crypto observations do not masquerade as stock trading activity.

Priority: risk freeze; stopped/missing/stale scheduler; feed errors; outdated active-position fetch during an open regular session; recent recorded stock candle; open-session waiting; closed-session waiting. A dashboard request failure explicitly marks displayed values as old. Normal waiting is visually separate from warnings.

The schedule handles US daylight saving, weekends, NYSE holiday closures and early closes for 2026–2028. It is a pinned display calendar, not a live halt feed or a trading control. Outside its covered years the next opening is unavailable. Provider delay and candle completion are distinct from dashboard refresh. No strategy, ledger, requests budget, risk limits or frozen protocol changes.

Calendar source: [official NYSE calendar and hours](https://www.nyse.com/trade/hours-calendars), checked 11 October 2026. Unscheduled closures and feed differences remain possible. Tests cover weekends, holidays, daylight saving, early closing, Perth formatting, unsupported calendar years, risk freezes, feed/scheduler failures and dashboard connection loss. All 75 existing backend tests pass.

A browser policy block prevented direct visual inspection of the live page. UI logic and authenticated delivery checks are used; visual acceptance remains outstanding.

Deployment status: prepared and tested, not live. SSH to the existing VM timed out before any upload. Authenticated dashboard API remains reachable. Restore restricted administration access before deployment and authenticated asset-delivery verification.
