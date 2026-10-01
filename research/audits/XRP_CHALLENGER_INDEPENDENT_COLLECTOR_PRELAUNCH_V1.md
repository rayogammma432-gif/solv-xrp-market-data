# XRP Challenger Independent Collector — Prelaunch Audit V1

## Estado

**IMPLEMENTED / PASS_PRELAUNCH_NOT_ACTIVATED**

Formal collection started:
- **NO**

Historical 2026 holdout:
- **LOCKED**
- 2026-01-01 → 2026-08-31

Frozen V3.1 forward start:
- `2026-10-01T06:00:00Z`

## Architecture

CURRENT:
`Binance → termux/market_collector.py → operational XRP receptor → XRP_Market_Data`

CHALLENGER:
`Binance → termux/xrp_challenger_collector.py → dedicated Challenger receptor → XRP_Challenger_Research`

The independent Challenger collector does not import or invoke the CURRENT collector.

The CURRENT collector no longer imports or invokes `ForwardV3Tracker`.

## Dedicated storage

Spreadsheet:
- title: `XRP_Challenger_Research`
- ID: `14mVe2XXcsVBCojZSbp6A7qQKO2RFpovLtKntOYFDwvA`

Tabs:
- `CHALLENGER_CANDIDATES`
- `CHALLENGER_OUTCOMES`
- `CHALLENGER_HEALTH`
- `CHALLENGER_AUDIT`

Prelaunch verification:
- candidates rows: 0
- outcomes rows: 0
- health rows: 0

Operational XRP workbook:
- CHALLENGER_* destination tabs: 0

The provisional Challenger tabs previously created in XRP_Market_Data were verified empty and deleted before formal activation.

## Dedicated receptor

Source:
- `apps-script/XRP_Challenger_Receptor.gs`

File commit:
- `53e02edcb48188c681a165d0becd7cecedbefe23`

Version:
- `XRP_RECEPTOR_CHALLENGER_V1`

Required Script Property:
- `CHALLENGER_SHARED_SECRET`

Accepted modes:
- `challenger_recovery`
- `challenger_incremental`

Fail-closed provenance:
- protocol must equal `XRP_FORWARD_V3_1`
- registry SHA must equal `4905aa1e94cbf2fe9318c761942d440a298ba5655d78e8e3a80bfc5cb85caded`
- collector version must equal `XRP_CHALLENGER_COLLECTOR_V1`

The operational XRP receptor contains no Challenger modes or Challenger destination writes.

Operational receptor cleanup commit:
- `345e1bf60129e169d0eb22945e135e91c167d7f3`

## Independent process

Collector:
- `termux/xrp_challenger_collector.py`

Latest file commit:
- `7319021cd663749aa11f14ee9c40afc49100b996`

Collector version:
- `XRP_CHALLENGER_COLLECTOR_V1`

Own runtime files:
- `challenger_activation.json`
- `challenger_runtime.json`
- `challenger_forward_state.json`
- `challenger_collector.pid`
- Challenger-specific logs

These local files/secrets are ignored by Git.

CURRENT detachment:
- `termux/market_collector.py`
- commit `656dedc63fc154aff53cef4c58b3f1f34d51ee2c`

## Rule engine

Shared frozen research engine:
- `termux/forward_v3_tracker.py`
- commit `c9aa5f2dec0755b50731f6b387fdb960530d6a0e`

Upstream protocol:
- `XRP_FORWARD_V3_1`

Registry SHA:
- `4905aa1e94cbf2fe9318c761942d440a298ba5655d78e8e3a80bfc5cb85caded`

No thresholds, horizons, directions or effect floors were changed to create the independent process.

A:
- directional research candidate
- taker-flow exhaustion

B:
- research OI moderator
- not an operational entry rule

C:
- directional research candidate
- momentum exhaustion

No candidate creates:
- SIGNALS
- orders
- Telegram trade alerts

## Process scripts

- `termux/start_challenger_collector.sh`
- `termux/stop_challenger_collector.sh`
- `termux/status_challenger_collector.sh`

Configuration:
- dedicated top-level `challenger` block in local `config.json`
- separate web-app URL
- separate shared secret

## Activation guard

Example:
- `termux/challenger_activation.example.json`
- disabled by default

Formal activation requires:
- `enabled=true`
- exact V3.1 protocol/registry
- exact deployed collector Git SHA
- dedicated receptor version
- deployment verification strictly before frozen start

First valid pre-start boot creates a runtime marker.

If the first live boot occurs after `2026-10-01T06:00:00Z` without a valid pre-start runtime marker/state:
- collector fails closed;
- it refuses to backfill and call the data prospective;
- a new forward version/start is required.

## Recovery and coverage

The independent collector:
- catches up all missing 1m decisions chronologically;
- paginates Binance klines;
- reconstructs PRIMARY 15m from exact 1m;
- uses no nearest/interpolation;
- recovers recent candidates/outcome IDs/latest health from the dedicated workbook.

Health is independent from CURRENT.

## CI validation

Workflow:
- `.github/workflows/xrp-challenger-independent-collector-v1.yml`

Final run:
- `36801481690`

Head:
- `a179b02e50eba637c2c072c0db33983296d6c910`

Conclusion:
- **SUCCESS**

Artifact:
- `11136251654`

Artifact digest:
- `sha256:aad964b627fbfc2ca7455c19f7b6142b8517690981d02ea257b8af2d00a9f673`

Passed:
- Python syntax
- shell syntax
- operational Apps Script syntax
- dedicated Challenger Apps Script syntax
- existing V3.1 parity/recovery smoke
- pre-start gate
- multi-bar catch-up
- pagination
- resample parity
- feature parity
- state recovery
- health
- late-first-start block
- post-start restart recovery after valid pre-start marker
- CURRENT process detachment
- dedicated receptor/storage isolation
- prelaunch registry validation

Validator result:
- `PASS_PRELAUNCH_NOT_ACTIVATED`
- errors: 0
- formal_collection_started: false

## Remaining shared failure domain

Scientific/software/storage independence is now achieved.

CURRENT and CHALLENGER still share:
- Binance as market source;
- the same Motorola hardware/network if deployed on that device.

A Motorola/network failure can therefore stop both processes simultaneously.

This does not compromise statistical independence of their opportunity logic, but it is not full infrastructure redundancy.

Full operational redundancy would require a second device/server and is not required for the current research phase.

## Deployment boundary

The independent collector is **not activated**.

Before formal activation:
1. Motorola pulls the validated repository revision.
2. Dedicated Apps Script project is created/deployed from `XRP_Challenger_Receptor.gs`.
3. Set `CHALLENGER_SHARED_SECRET`.
4. Put dedicated Challenger web-app URL/secret into local config.
5. Run receptor/prelaunch check.
6. Fill `challenger_activation.json` with exact deployed revisions.
7. Verify/start before the frozen forward start.

If deployment cannot be verified before the frozen start:
- do not activate V3.1 late;
- do not backfill it as prospective;
- create a new forward protocol/start.

## Conclusion

Independent Challenger collector architecture is implemented and validated.

Status:
- source ready: YES
- storage isolated: YES
- receptor isolated: YES
- CURRENT detached: YES
- tests PASS: YES
- activation enabled: NO
- formal collection started: NO
