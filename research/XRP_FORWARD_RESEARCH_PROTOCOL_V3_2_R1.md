# XRP Forward Research Protocol V3.2 R1

## Estado

**FROZEN BEFORE FORWARD START**

Version:
- `XRP_FORWARD_V3_2_R1`

Operational lineage:
- V3.0: superseded before start.
- V3.1: deployment attempt aborted; no valid formal prospective collection was activated.
- V3.2: hardened relaunch specification; its frozen 2026-10-02 start passed without valid activation and it is retained as ABORTED PRELAUNCH / NO PROSPECTIVE EVIDENCE.
- V3.2 R1: clean prospective relaunch with unchanged scientific hypotheses and the same hardened deployment/runtime controls.

This Challenger lineage is independent from the operational XRP CURRENT rule lineage (including XRP_V3.4). CURRENT changes do not redefine Challenger hypotheses or storage.

Forward start:
- `2026-10-04T00:00:00Z`
- `2026-10-03 18:00:00 America/Guatemala`

Historical 2026 holdout:
- **LOCKED / NOT READABLE**
- 2026-01-01 00:00 UTC -> 2026-08-31 23:59 UTC

## Reason for V3.2 R1

V3.2 R1 exists solely because the V3.2 prospective start elapsed before a valid activation/runtime-ready state was established. The V3.2 scientific specification was not changed and no accepted V3.2 prospective evidence exists.

V3.2 R1 changes the prospective start/provenance only. It does not change the scientific hypotheses, thresholds, directions, horizons, economic floors, outcome definitions, bootstrap, multiplicity correction, or temporal-stability rules frozen for V3.2.

The V3.1 launch was aborted because the deployment path exposed implementation/operational defects before a valid prospective start:
- gate and collector used inconsistent Git cleanliness semantics (tracked-only vs including untracked local files);
- local backup/runtime artifacts could make the collector report a different Git identity after the gate passed;
- start/status scripts could present ambiguous state because process liveness and readiness were not the same thing;
- stale activation/runtime/state artifacts did not have a single safe reset workflow;
- runtime marker validation did not fully bind marker provenance to protocol/registry/collector/start;
- the tracker could advance across a transient missing 1m/15m bar, making later recovery of that skipped decision impossible;
- health rows could finalize before newly generated INCOMPLETE outcome status was reflected;
- CI did not automatically run on every relevant collector/receptor/protocol change.

No valid V3.1 or V3.2 formal collection rows exist in CHALLENGER_CANDIDATES, CHALLENGER_OUTCOMES, or CHALLENGER_HEALTH at the time V3.2 R1 is frozen. Both missed launches are retained as immutable aborted prelaunch records.

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
- the latest OI metric used by a decision must have available_at age <=10 minutes, matching HISTORICAL_FEATURE_CONTRACT_V1;
- oi_chg_15m requires exact source timestamp t-15m relative to that selected metric row;
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

Recovery is completeness-based and has no arbitrary event-age cutoff. It uses:
- every V3.2 R1 candidate still missing at least one required outcome;
- every V3.2 R1 candidate newer than the latest compatible health checkpoint;
- existing outcome IDs for those returned candidates;
- the latest compatible health checkpoint.

## Activation/runtime invariants

The deployment is valid only if:
- activation protocol/version/start/registry match V3.2 R1 exactly;
- deployment verification happened before formal start;
- deployed tracked Git tree is clean;
- activation Git SHA equals collector Git SHA;
- dedicated receptor version/build-ID/storage/protocol/registry/collector identity all match;
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

The status command must distinguish RUNNING_READY, RUNNING_DEGRADED, RUNNING_NOT_READY, STOPPED and STALE_PID, and must not present historical log lines as current health. A fresh CYCLE_ERROR heartbeat is RUNNING_DEGRADED, never READY.

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
- expose its receptor version, build ID, spreadsheet ID, expected protocol version, registry SHA and collector version;
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

Normative evaluation contract:
- `research/XRP_FORWARD_EVALUATION_CONTRACT_V3_2_R1.md`
  - frozen file commit: `dece3300dcd2e2b6c4eb385ecbf6cf0d7e1caf48`
- `research/experiments/XRP_FORWARD_EVALUATION_CONTRACT_V3_2_R1.json`
  - frozen file commit: `fe62072b14f5d6d1c9be6dc944f61cee2e15330a`

Earliest common 180-day gate:
- `2027-04-02T00:00:00Z`

The frozen evaluation contract defines exactly:
1. eligible primary rows and maturity cutoff;
2. candidate-specific primary effects;
3. UTC-day block bootstrap with 2,000 replicates and deterministic seed;
4. one-sided bootstrap p per candidate;
5. Holm across all three primary p-values;
6. percentile CI95 lower > 0;
7. candidate-specific effect and sample floors;
8. temporal stability: monthly median > 0 for A, quarterly median > 0 for B/C;
9. fail-closed handling of primary INCOMPLETE outcomes and provenance failures.

An informational 90-day checkpoint:
- `2027-01-02T00:00:00Z`
- cannot promote or retune A.

## Immutability

The evaluation contract is part of the frozen scientific specification.

From `2026-10-04T00:00:00Z`:
- thresholds do not change;
- directions do not change;
- horizons do not change;
- floors do not change;
- skipped adverse events are not removed;
- any scientific-rule change requires a new forward version and future start.

## Final prelaunch state

- Historical 2026 holdout: LOCKED
- V3.1: ABORTED PRELAUNCH / NO VALID FORMAL COLLECTION
- V3.2: ABORTED PRELAUNCH / NO PROSPECTIVE EVIDENCE
- V3.2 R1: FROZEN FOR CLEAN RELAUNCH
- forward results used to redesign hypotheses: NO
- validated operational challenger: NONE


## R1 preregistration identity

- protocol version: `XRP_FORWARD_V3_2_R1`
- registry file: `research/experiments/XRP_FORWARD_REGISTRY_V3_2_R1.jsonl`
- registry SHA256: `5caac1ec957545af503d18775a46d38363f7dadb8403b2ad3a34f5dbde5151bc`
- forward start: `2026-10-04T00:00:00Z`
- Guatemala: `2026-10-03 18:00:00 America/Guatemala`
- minimum deployment/readiness cutoff: `2026-10-03T23:30:00Z` / `17:30 America/Guatemala`
- evaluation contract version: `XRP_FORWARD_EVALUATION_CONTRACT_V3_2_R1`
- scientific-rule changes versus V3.2: **NONE**
