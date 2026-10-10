# Specialty agent brains

Release: specialty-brains-v1, 10 October 2026. [Open Agent Brains](https://tcr.161-33-69-185.sslip.io/brains) with the existing private dashboard login. Each agent card links directly to its specialty. [Analyst Brain](ANALYST_BRAIN.md) remains its separate trend-analysis workspace.

These brains combine coded diagnostic tools, approved assigned lessons and saved operational evidence. They are deterministic software, not trained language models. Reading notes cannot execute instructions, alter limits, create orders, resume a freeze or promote a strategy. Existing paper execution, risk gates and reserved research remain unchanged. No paid service, extra market-data request or broker connection is added.

## Responsibilities and tools

| Agent | Specialty evidence | Important boundary |
| --- | --- | --- |
| Market Data | Coverage flags, missing candle checkpoints, per-symbol timestamps/errors and persisted daily request utilisation | Missing checkpoints and provider errors are distinct; timestamps require market-session interpretation. This page does not fetch new prices. |
| Risk & Compliance | Open entry cost/planned loss, position count, daily realised P/L and equity drawdown versus configured thresholds | Descriptive current utilisation is not new-order approval. Active orders also recheck sizing, cash and sector/group/correlation exposure; gap losses can exceed planned risk. |
| Paper Trader | Pending order decision times, open positions, estimated recorded costs and queued-order evidence | Uses the existing later-opening and gap-stop model. No broker, live quotes or new exit variant. Legacy zero costs are not evidence of cost-free trading. |
| Logger | Cash reconciliation, missing original trade context and audit record count | Does not fabricate missing legacy plans or change an inconsistent ledger. It is not a full forensic audit or backup-integrity check. |
| Supervisor | Scheduler thread, freeze state/reason and last successful cycle | Review alongside health and market coverage. No new automatic remediation; VM backup timers/off-server recovery are not verified by this preview. |
| Performance Reviewer | Net closed P/L, win rate, eligible R expectancy, reviewed adherence, research count and four latest weekly reports | Empty outcomes stay unavailable. Unknown reviews are excluded. Research is separate from operational results; 30 trades is a review milestone, not proof of an edge. |

## Use and teach a specialty

1. Open Agent Brains or click a specialty link in an agent's dashboard details.
2. Select the role and read its metrics, checks and evidence limits. PASS means that displayed check passed; REVIEW asks for investigation; UNKNOWN means evidence is unavailable. A passing preview does not authorise an order.
3. Inspect approved lessons and the ten most recent related events within the latest 1,000 audit records. Missing recent events do not imply missing full audit history.
4. In Research Lab, draft a custom lesson, record evidence/limitations, assign the relevant role, then approve it. Only approved lessons assigned to that role enter its reference context. Hypotheses and experiments remain research notes. Version checks protect concurrent edits.
5. Load saved specialty history to inspect prior metrics, checks, lesson versions and events. The visible preview can reflect newer lessons; earlier snapshots stay intact. Refresh preserves an opened history list; selecting another role clears it.

Visible previews refresh every minute from stored data. Reports are persisted at startup and after scheduler attempts, including failed attempts where diagnostic collection succeeds. Startup may capture the scheduler before it starts; inspect report timing and current preview before treating that saved state as an incident. A diagnostic failure records a Logger review event when possible and does not interrupt the trading scheduler. API reads do not create snapshots, spend provider credits or mutate orders.

## Storage and access

Authenticated read-only routes: GET `/brains`, `/agent-brains`, `/agent-brains/{role}/history`. Unknown roles return 404; Analyst uses its own routes. History defaults to 20 reports and is capped at 50 per read. Viewing needs the dashboard login, not the control token. Knowledge edits still need the separate control token.

SQLite `agent_reports` has role, version, context_hash, created_at and JSON payload. Primary key: role + version + context_hash. The hash covers the report including its approved lesson versions and evidence; identical contexts deduplicate. Existing snapshots are not overwritten. Normal consistent SQLite backups include this table. Read limits do not purge stored history; retention and storage growth remain maintenance work.

Cash check: starting balance + closed realised P/L − open entry cost = cash. Costs embedded in recorded fills are not subtracted twice. Closed-trade metrics cover the operating ledger; mixed legacy/current cost records require care. No predictive confidence score or validated-edge flag is introduced.

## Verification

31 backend tests passed, covering authentication/read-only access, cash mismatch detection, missing original context, empty outcome metrics, role-assigned approved lessons, snapshot deduplication and immutable history, plus existing strategy, execution, risk, research and Analyst tests. Mocked interface checks passed for role selection, diagnostic display, unavailable metrics and escaped knowledge; existing dashboard interaction checks also passed. These are not a live visual/mobile/accessibility acceptance review.

Cloud verification on 10 October 2026 Perth time confirmed six specialty previews, authenticated HTTPS, a healthy running scheduler and saved Logger reports surviving restart. Existing entries and the reserved research registration/protocol were preserved; the paper cash ledger reconciled. No extra provider requests are made by these read-only previews. Zero operational paper trades were closed at this check. This dated verification is not a current-status guarantee or evidence of profitability.

See [documentation index](docs/README.md), [Agent learning](AGENT_LEARNING.md) and [Research Lab](RESEARCH_LAB.md). Future changes to executable rules need versioned implementation and separate validation; lessons alone never activate them.

## Decision controls release — 10 October 2026

[Open Decision Evidence](https://tcr.161-33-69-185.sslip.io/controls). New proposals carry durable single-use signed approvals; execution rechecks risk and the validated opening. Individual risk checks and raw proposal/fill evidence are retained. Session-aware quality gates block missing/stale entries and quarantine suspect prices. Existing signal/exit formulas, numeric limits and the reserved research protocol remain fixed, but stricter gates can prevent entries. New closed-trade attribution preserves regime and decision provenance; missing legacy evidence stays unknown.

Read [Control Boundaries](CONTROL_BOUNDARIES.md) for exact controls, migration, recovery and limitations. Unsigned legacy pending buys are cancelled with their original payload retained in audit; existing positions and exit queues remain. Validation: 47 backend tests and UI logic checks; live visual review remains incomplete.
