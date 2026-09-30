# XRP Forward V3 Capture Protocol V1

## Estado

**CAPTURE LAYER READY — PRE-FORWARD**

Forward start:
- `2026-10-01T00:00:00Z`

Historical 2026 holdout:
- **LOCKED**
- this capture layer never reads 2026-01-01 → 2026-08-31 outcomes.

## Purpose

Persist XRP_FORWARD_V3 shadow observations prospectively without changing CURRENT XRP logic.

Data flow:

`Binance closed bars → Termux market_collector → ForwardV3Tracker → XRP receptor → Google Sheets`

The capture layer creates:
- no SIGNALS;
- no orders;
- no trades;
- no changes to ANALYSES;
- no changes to USER_TRADES.

## Google Sheets

Spreadsheet:
- XRP_Market_Data
- `1ag0yaE0hcDoG8uED4qejfHGlD2OuXZxvUPYZRUzjqG0`

### FORWARD_V3_EVENTS

Append-only event snapshot table.

Columns:
1. Event ID
2. Protocol Version
3. Candidate ID
4. Asset
5. Decision Grid
6. Decision Time UTC
7. Bar Open UTC
8. Direction
9. Reference Price
10. XRP Ret 12
11. XRP Rel Volume20
12. XRP Taker Imbalance
13. XRP OI Chg 15m
14. Rule Parameters JSON
15. Feature Snapshot JSON
16. Feature Set Version
17. Normalization Version
18. XRP Bar Available At UTC
19. XRP Metrics Available At UTC
20. Registry File
21. Registry SHA256
22. Protocol File
23. Protocol Commit SHA
24. Collector Version
25. Created UTC

Primary key:
- Event ID

Event ID:
- `candidate_id|decision_time_utc`

The receptor deduplicates by Event ID.

### FORWARD_V3_OUTCOMES

Append-only direction-neutral outcome table.

One row per event + horizon.

Columns:
1. Outcome ID
2. Event ID
3. Candidate ID
4. Decision Time UTC
5. Horizon Min
6. Is Primary
7. Outcome Available UTC
8. Forward Return
9. Raw Up Excursion
10. Raw Down Excursion
11. Completeness
12. Outcome Engine Version
13. Source Last Bar UTC
14. Registry SHA256
15. Collector Version
16. Created UTC
17. Notes

Primary key:
- Outcome ID

Outcome ID:
- `event_id|H<horizon_min>`

The receptor deduplicates by Outcome ID.

## Candidate capture rules

Registry seal:
- `559728efd47599b629ecaca7b8cdc2191f5b21a6ee344c89490839ab7a532a7f`

### A — Taker exhaustion
Grid:
- every new closed XRP 1m bar.

Eligibility:
- abs(taker imbalance) >= 0.30
- relative volume20 >= 1.5

Direction:
- positive imbalance → SHORT
- negative imbalance → LONG

Horizon rows:
- 5m
- 15m primary
- 30m

### B — OI moderator
Grid:
- every new closed XRP 15m bar.

Eligibility:
- abs(ret_12) >= 0.005
- abs(oi_chg_15m) >= 0.005

OI live availability:
- uses Binance 5m open-interest history;
- a source point timestamp t is considered available at t+5m;
- 15m change requires the exact t-15m observation;
- no nearest future or interpolation.

Direction:
- sign(ret_12)

Snapshot also stores:
- oi_group = EXPANSION or CONTRACTION

Horizon:
- 60m primary

### C — Momentum exhaustion
Grid:
- every new closed XRP 15m bar.

Eligibility:
- abs(ret_12) >= 0.010
- relative volume20 >= 1.5

Direction:
- positive ret_12 → SHORT
- negative ret_12 → LONG

Horizon rows:
- 15m
- 60m primary
- 240m

## Outcome rules

Reference price:
- exact closed XRP bar close at decision.

For horizon h:
- target availability must equal `decision_time + h`;
- exact 1m bars are required;
- no nearest;
- no interpolation.

Forward return:
- `future_close / reference_price - 1`

Raw up excursion:
- `max(future highs) / reference_price - 1`

Raw down excursion:
- `min(future lows) / reference_price - 1`

The decision bar is excluded.

If an exact minute is temporarily missing:
- wait 5 minutes beyond target;
- if still unavailable, record `INCOMPLETE` with blank outcome values.

## Durability / retries

Local state:
- `termux/forward_v3_state.json`

Behavior:
- event is persisted locally before web posting;
- failed network post remains pending;
- deterministic IDs allow safe resend;
- receptor deduplicates by ID;
- row is acknowledged locally only after successful receptor response.

Completed local events keep a recent audit tail; Google Sheets is the persistent append-only store.

## Versions

Protocol:
- `XRP_FORWARD_V3`

Protocol file:
- `research/XRP_FORWARD_RESEARCH_PROTOCOL_V3.md`

Protocol commit:
- `69895b7c110deb838b62e3bf70a5b84455f09ca9`

Features:
- `FEATURES_V1`

Normalization:
- `HIST_NORM_V1`

Collector:
- `XRP_FORWARD_V3_COLLECTOR_V1`

Outcome:
- `XRP_FORWARD_V3_OUTCOME_V1`

## Implementation

Termux:
- `termux/forward_v3_tracker.py`
- integrated into `termux/market_collector.py`

Google Apps Script source:
- `apps-script/XRP_Receptor_Incremental.gs`

Sheets:
- `FORWARD_V3_EVENTS`
- `FORWARD_V3_OUTCOMES`

## Smoke-test gate

GitHub Actions workflow:
- `.github/workflows/xrp-forward-v3-capture-smoke.yml`

Required PASS:
- pre-start block;
- exactly 3 synthetic candidate events;
- exactly 7 synthetic outcomes;
- retry idempotence;
- exact-window behavior;
- incomplete target does not use nearest;
- Python syntax gate.

## Deployment boundary

GitHub source changes do not automatically deploy the user's Motorola working tree or an existing Apps Script web-app deployment.

Before live capture:
1. Motorola must pull the new Termux code.
2. XRP Apps Script project must receive the updated receptor source and be redeployed while preserving `SHARED_SECRET` and the existing web-app endpoint.
3. The two Google Sheets tabs must exist with the exact headers defined above.
4. Run the smoke/dry checks before the forward window is allowed to persist events.

No event before `2026-10-01T00:00:00Z` is eligible.
