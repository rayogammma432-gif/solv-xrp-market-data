# XRP Forward Research Protocol V3.2

## Estado

**FROZEN BEFORE FORWARD START**

Version:
- `XRP_FORWARD_V3_2`

Operational lineage:
- V3.0: superseded before start.
- V3.1: deployment attempt aborted; no valid formal prospective collection was activated.
- V3.2: clean prospective relaunch with unchanged hypotheses and hardened deployment/runtime controls.

Forward start:
- `2026-10-02T12:00:00Z`
- `2026-10-02 06:00:00 America/Guatemala`

Historical 2026 holdout:
- **LOCKED / NOT READABLE**
- 2026-01-01 00:00 UTC -> 2026-08-31 23:59 UTC

## Reason for V3.2

V3.2 changes deployment/runtime mechanics only. It does not change the scientific hypotheses, thresholds, directions, horizons, economic floors, or outcome definitions from V3.1.

The V3.1 launch was aborted because the deployment path exposed implementation/operational defects before a valid prospective start:
- gate and collector used inconsistent Git cleanliness semantics (tracked-only vs including untracked local files);
- local backup/runtime artifacts could make the collector report a different Git identity after the gate passed;
- start/status scripts could present ambiguous state because process liveness and readiness were not the same thing;
- stale activation/runtime/state artifacts did not have a single safe reset workflow;
- runtime marker validation did not fully bind marker provenance to protocol/registry/collector/start;
- the tracker could advance across a transient missing 1m/15m bar, making later recovery of that skipped decision impossible;
- health rows could finalize before newly generated INCOMPLETE outcome status was reflected;
- CI did not automatically run on every relevant collector/receptor/protocol change.

No valid V3.1 formal collection rows exist in CHALLENGER_CANDIDATES, CHALLENGER_OUTCOMES, or CHALLENGER_HEALTH at the time V3.2 is frozen. V3.1 is retained as an immutable aborted prelaunch record.

## Objective and mode

Prospectively evaluate the same three historical relationships as V3.1.

Mode:
- shadow research only;
- no SIGNALS;
- no orders;
- no trades;
- no TP/SL operational logic;
- no Telegram trade alerts;
- no changes to XRP CURRENT.

## Candidate A — SCALP Taker-Flow Exhaustion

ID:
- `XRP-FWD-V3-A-TAKER-EXHAUSTION`

Grid:
- closed XRPUSDT 1m.

Features:
- xrp_taker_imbalance
- xrp_rel_volume20

Fixed rule:
- abs(taker_imbalance) >= 0.30
- rel_volume20 >= 1.5

Direction:
- imbalance > 0 -> SHORT
- imbalance < 0 -> LONG

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
- `XRP-FWD-V3-B-OI-MODERATOR`

Grid:
- PRIMARY_15M reconstructed exclusively from 15 exact consecutive XRPUSDT 1m bars aligned to UTC.

Features:
- xrp_ret_12
- xrp_oi_chg_15m

Fixed rule:
- abs(ret_12) >= 0.005
- expansion: oi_chg_15m >= 0.005
- contraction: oi_chg_15m <= -0.005

Base direction:
- sign(ret_12)

Primary effect:
- mean signed 60m expansion minus mean signed 60m contraction.

Minimum sample:
- >=600 expansion;
- >=600 contraction;
- >=150 eligible days.

Effect floor:
- 0.00040.

B remains a research moderator, not an entry signal.

## Candidate C — PRIMARY Momentum Exhaustion

ID:
- `XRP-FWD-V3-C-MOMENTUM-EXHAUSTION`

Grid:
- PRIMARY_15M reconstructed from exact consecutive 1m bars.

Features:
- xrp_ret_12
- xrp_rel_volume20

Fixed rule:
- abs(ret_12) >= 0.010
- rel_volume20 >= 1.5

Direction:
- ret_12 > 0 -> SHORT
- ret_12 < 0 -> LONG

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

## Live/historical parity

Semantics remain identical to V3.1:
- SCALP_1M uses the exact closed 1m kline;
- PRIMARY_15M is resampled from exactly 15 consecutive 1m bars;
- UTC bucket = floor(open_time / 900000) * 900000;
- ret_12 = close_t / close_(t-12 bars) - 1;
- rel_volume20 = current volume / mean(previous 20 bars), current excluded;
- taker_imbalance = 2 * taker_buy_base / volume - 1;
- invalid taker ratio fails closed;
- OI timestamp t is usable only at t+5m;
- oi_chg_15m requires exact t-15m;
- no future-nearest and no interpolation.

## Continuity and catch-up

The collector must never skip over a missing decision bar.

For 1m and PRIMARY_15M:
- only a consecutive sequence after the last evaluated decision may advance the cursor;
- if the next expected decision is missing, evaluation stops at the gap;
- later bars beyond that gap are not marked evaluated;
- subsequent cycles retry the missing interval;
- health records the unresolved missing coverage once the hour is finalizable.

This rule prevents a transient API omission from becoming an irreversible prospective hole.

## Outcomes

Reference:
- exact decision close.

For horizon h:
- target = decision_time + h;
- every exact 1m bar in the window is required;
- no nearest/interpolation.

Grace:
- 5 minutes after target.

After grace, an incomplete exact window is finalized as INCOMPLETE.

INCOMPLETE status must be represented in health accounting in the same cycle in which the outcome is generated, even before receptor acknowledgement.

## Recovery and state provenance

Persistent storage is the dedicated Challenger Google Sheet.

Local state must be bound to:
- protocol version;
- registry SHA256;
- formal start UTC.

A state file from another protocol/start must fail closed and require the explicit prelaunch reset workflow.

Recovery continues to use:
- recent Challenger candidates;
- existing outcome IDs;
- latest compatible health checkpoint.

## Activation/runtime invariants

The deployment is valid only if:
- activation protocol/version/start/registry match V3.2 exactly;
- deployment verification happened before formal start;
- deployed tracked Git tree is clean;
- activation Git SHA equals collector Git SHA;
- dedicated receptor version/storage/protocol/registry/collector identity all match;
- the first runtime marker is created before formal start;
- runtime marker hash matches the activation;
- runtime marker protocol/registry/start/collector version/Git SHA all match the running collector.

Untracked local files such as ignored config/runtime backups do not alter source Git identity. Tracked modifications do.

A pre-start reset is explicit, auditable, and forbidden once the safe launch window has closed.

## Readiness semantics

A background PID is not equivalent to a ready collector.

The process is READY only after:
1. activation validation passes;
2. the pre-start runtime marker exists and is valid;
3. dedicated receptor recovery succeeds;
4. a ready marker bound to the current PID, activation hash, Git SHA, protocol and receptor identity is written.

The start script must wait for this readiness marker or fail closed.

The status command must distinguish RUNNING_READY, RUNNING_NOT_READY, STOPPED and STALE_PID, and must not present historical log lines as current health.

## Storage/receptor isolation

Dedicated spreadsheet:
- `XRP_Challenger_Research`
- ID `14mVe2XXcsVBCojZSbp6A7qQKO2RFpovLtKntOYFDwvA`

Tabs:
- CHALLENGER_CANDIDATES
- CHALLENGER_OUTCOMES
- CHALLENGER_HEALTH
- CHALLENGER_AUDIT

The dedicated Apps Script receptor must:
- use its own CHALLENGER_SHARED_SECRET;
- reject CURRENT modes;
- expose its receptor version, spreadsheet ID, expected protocol version, registry SHA and collector version;
- serialize writes with a script lock to make retries idempotent.

## Health

Finalized hourly health records:
- expected/evaluated/missing 1m;
- expected/evaluated/missing 15m;
- OI checks/failures;
- events A/B/C;
- pending events;
- incomplete outcomes;
- last evaluated timestamps;
- collector provenance.

A finalized hour with any missing 1m or 15m remains visible for review.

## Statistical gate

Earliest common 180-day gate:
- `2027-03-31T12:00:00Z`

At that gate:
1. primary effect for A/B/C;
2. UTC-day block bootstrap, 2,000 replicates;
3. one-sided p per candidate;
4. Holm across the three primary p-values;
5. CI95 lower > 0;
6. candidate-specific effect floor;
7. candidate-specific sample minimum;
8. preregistered temporal stability.

A informational 90-day checkpoint:
- `2026-12-31T12:00:00Z`
- cannot promote or retune A.

## Immutability

From `2026-10-02T12:00:00Z`:
- thresholds do not change;
- directions do not change;
- horizons do not change;
- floors do not change;
- skipped adverse events are not removed;
- any scientific-rule change requires a new forward version and future start.

## Final prelaunch state

- Historical 2026 holdout: LOCKED
- V3.1: ABORTED PRELAUNCH / NO VALID FORMAL COLLECTION
- V3.2: FROZEN FOR CLEAN RELAUNCH
- forward results used to redesign hypotheses: NO
- validated operational challenger: NONE
