# XRP Forward Research Protocol V3.2

## Estado

**FROZEN BEFORE FORWARD START**

Versión:
- `XRP_FORWARD_V3_2`

Supersedes:
- `XRP_FORWARD_V3_1` for prospective collection only.

Reason:
- V3.1 was not successfully activated on the device before its frozen start.
- No V3.1 forward observations are accepted as prospective evidence.
- V3.2 changes deployment/runtime controls and the start timestamp only.
- Candidate hypotheses, thresholds, directions, horizons, effect floors and multiplicity remain unchanged.

Forward start:
- `2026-10-02T12:00:00Z`
- `2026-10-02 06:00:00` Guatemala (UTC-06:00)

Historical 2026 holdout:
- **LOCKED / NOT READABLE**
- 2026-01-01 00:00 UTC → 2026-08-31 23:59 UTC

## Objective

Prospectively evaluate the same three preregistered relationships under a clean independent Challenger deployment.

Mode:
- shadow research;
- no SIGNALS;
- no orders;
- no trades;
- no TP/SL operational;
- no changes to XRP CURRENT.

## Candidate A — SCALP Taker-Flow Exhaustion

ID:
- `XRP-FWD-V3_2-A-TAKER-EXHAUSTION`

Grid:
- SCALP_1M from closed XRPUSDT 1m bars.

Rule:
- abs(taker_imbalance) >= 0.30
- rel_volume20 >= 1.5

Direction:
- imbalance > 0 → SHORT
- imbalance < 0 → LONG

Primary:
- signed forward 15m

Secondary diagnostics:
- 5m
- 30m
- MFE/MAE 15m

Minimum sample:
- 90 calendar days;
- >=12,000 events;
- >=3,000 each side;
- >=75 unique event days.

Effect floor:
- mean signed 15m >= 0.00010.

The 90-day checkpoint is informational only.

## Candidate B — PRIMARY OI Momentum Moderator

ID:
- `XRP-FWD-V3_2-B-OI-MODERATOR`

Grid:
- PRIMARY_15M reconstructed exclusively from 15 consecutive XRPUSDT 1m bars aligned to UTC.

Rule:
- abs(ret_12) >= 0.005
- expansion: oi_chg_15m >= 0.005
- contraction: oi_chg_15m <= -0.005

Base direction:
- sign(ret_12)

Primary effect:
- mean signed 60m expansion - mean signed 60m contraction.

Minimum sample:
- >=600 expansion;
- >=600 contraction;
- >=150 eligible days.

Effect floor:
- 0.00040.

## Candidate C — PRIMARY Momentum Exhaustion

ID:
- `XRP-FWD-V3_2-C-MOMENTUM-EXHAUSTION`

Grid:
- PRIMARY_15M reconstructed from exact consecutive 1m bars.

Rule:
- abs(ret_12) >= 0.010
- rel_volume20 >= 1.5

Direction:
- ret_12 > 0 → SHORT
- ret_12 < 0 → LONG

Primary:
- signed forward 60m

Secondary:
- 15m
- 240m
- MFE/MAE 60m

Minimum sample:
- >=1,200 events;
- >=250 each side;
- >=150 eligible days.

Effect floor:
- 0.00043.

## Historical/live parity

Feature semantics remain identical to V3.1:
- SCALP_1M uses the exact closed 1m bar.
- PRIMARY_15M is reconstructed from exactly 15 consecutive 1m bars.
- ret_12 = close_t / close_(t-12 bars) - 1.
- rel_volume20 = current volume / mean(previous 20 volumes), excluding current.
- taker_imbalance = 2 * taker_buy_base / volume - 1.
- taker ratio outside [0,1] is invalid.
- OI timestamp t is treated as available at t+5m.
- oi_chg_15m requires the exact t-15m observation.
- no future nearest fill and no interpolation.

## Catch-up and recovery

Every cycle must:
- retain >=360 minutes warm-up;
- paginate 1m klines;
- evaluate every missed decision chronologically;
- reconstruct 15m only from complete consecutive 1m bars.

If OI cannot be recovered:
- Candidate B is not fabricated;
- health records the OI failure;
- A/C remain evaluable.

Google Sheets recovery remains persistent recovery storage.

## Outcomes

Reference price:
- exact close of the decision bar.

For horizon h:
- target = decision_time + h;
- every exact 1m bar in the horizon is required;
- no nearest and no interpolation.

After 5m grace:
- incomplete exact windows are recorded as INCOMPLETE.

## Deployment and runtime isolation V2

V3.2 uses versioned local files so stale V1 artifacts cannot satisfy or block V2:
- activation: `termux/challenger_v2_activation.json`
- runtime marker: `termux/challenger_v2_runtime.json`
- state: `termux/challenger_v2_forward_state.json`
- PID: `termux/challenger_v2_collector.pid`
- heartbeat: `termux/challenger_v2_heartbeat.json`
- logs: `termux/logs/challenger_v2_*.log`

The deployment gate:
- requires >=30 minutes lead before formal start;
- ignores chmod-only tracked mode changes;
- fails on tracked content changes;
- verifies dedicated URL and secret isolation from CURRENT;
- probes receptor version and dedicated spreadsheet identity;
- refuses placeholder config;
- writes activation only after every gate passes;
- may reuse an already-valid V2 activation idempotently;
- never silently overwrites an invalid activation.

The start wrapper:
- runs a foreground preflight including receptor probe;
- refuses to start with activation errors;
- starts the process only after preflight passes;
- requires the V2 runtime marker and heartbeat after startup.

Status uses the V2 PID/heartbeat and current V2 logs only; it does not infer health from historical V1 logs.

## Dedicated receptor

Expected receptor:
- source: `apps-script/XRP_Challenger_Receptor.gs`
- version: `XRP_RECEPTOR_CHALLENGER_V2_R1`
- script property: `CHALLENGER_SHARED_SECRET`
- spreadsheet: `XRP_Challenger_Research`
- spreadsheet ID: `14mVe2XXcsVBCojZSbp6A7qQKO2RFpovLtKntOYFDwvA`

Accepted modes:
- `challenger_recovery`
- `challenger_incremental`

## Formal statistical gate

Formal family gate:
- `2027-03-31T12:00:00Z`
- 180 days after V3.2 start.

A informational 90-day checkpoint:
- `2026-12-31T12:00:00Z`

At the common formal gate:
1. compute the preregistered primary effect for A/B/C;
2. UTC-day block bootstrap, 2,000 replicates;
3. one-sided p per candidate;
4. Holm across the 3 primary hypotheses;
5. require CI95 lower > 0;
6. require each effect floor;
7. require each minimum sample;
8. require preregistered temporal stability.

No secondary horizon can replace a primary after observing results.

## Provenance and immutability

Every row records protocol/registry/collector provenance and payload hash.

From `2026-10-02T12:00:00Z`:
- thresholds do not change;
- directions do not change;
- horizons do not change;
- floors do not change;
- catch-up cannot selectively exclude events;
- implementation changes affecting research semantics require a new forward version/start.

## V3.1 disposition

V3.1 remains preserved as an aborted deployment record:
- frozen start: `2026-10-01T06:00:00Z`;
- formal activation: FAILED / NOT ACCEPTED;
- prospective evidence accepted: NONE.

No V3.1 local activation/runtime/state file is reused by V3.2.
