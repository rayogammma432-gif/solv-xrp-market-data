# XRP Challenger Independent Collector Protocol V2

## State

**PRELAUNCH — IMPLEMENTED, NOT FORMALLY ACTIVATED**

Purpose:
- independently collect XRP Challenger research candidates;
- implement `XRP_FORWARD_V3_2` exactly;
- keep CURRENT and Challenger capture, state, receptor and storage paths isolated;
- create no SIGNALS, orders or Telegram trade alerts.

Formal prospective start:
- `2026-10-02T12:00:00Z`
- `2026-10-02 06:00:00 America/Guatemala`

Upstream registry SHA256:
- `99c17ecf3c3b376f734dc7469351445c7d6727f96d0cb7d5580ea59b5f9f932a`

## V1 launch incident and V2 corrections

The V1/V3.1 launch attempt is classified as **ABORTED PRELAUNCH / NO VALID FORMAL COLLECTION**.

Root causes corrected in V2:
1. Git cleanliness semantics are identical in gate and collector: only tracked **content** changes invalidate provenance. Untracked/ignored runtime files and chmod-only executable-bit changes are ignored; this avoids Android/Termux file-mode noise while still failing closed on source edits.
2. State is protocol-bound. A state file from another protocol/start fails closed.
3. First boot after the formal start is forbidden unless a valid pre-start runtime marker exists, regardless of whether a state file exists.
4. Runtime marker validation binds activation hash, protocol, registry, formal start, collector version and Git SHA.
5. A PID is not treated as readiness. Startup requires an explicit READY handshake after receptor recovery.
6. Status reports current machine-readable readiness/heartbeat instead of mixing current state with historical log tails.
7. A safe prelaunch reset archives stale activation/runtime/state/PID/ready/heartbeat/Challenger logs without touching local secrets.
8. 1m and 15m cursors stop at the first missing decision instead of skipping over a transient data gap.
9. INCOMPLETE outcomes are reflected in same-cycle health accounting before acknowledgement.
10. Dedicated receptor writes are serialized with a script lock and expose protocol/registry/collector identity for deployment probing.
11. CI is triggered by all relevant code/protocol/receptor changes.

## Separation

CURRENT:
`Binance -> market_collector.py -> operational XRP receptor -> XRP_Market_Data`

Challenger:
`Binance -> xrp_challenger_collector.py -> ForwardV3Tracker -> dedicated Challenger receptor -> XRP_Challenger_Research`

No dependency on `market_collector.py`.

## Local files

Private/ignored:
- `termux/config.json`
- `termux/challenger_activation.json`
- `termux/challenger_runtime.json`
- `termux/challenger_forward_state.json`
- `termux/challenger_ready.json`
- `termux/challenger_heartbeat.json`
- `termux/challenger_collector.pid`
- `termux/prelaunch_archive/`
- Challenger logs

## Readiness contract

The collector build is `XRP_CHALLENGER_COLLECTOR_V2_R2` and the dedicated receptor is `XRP_RECEPTOR_CHALLENGER_V2_R3` with build ID `XRP_CHALLENGER_RECEPTOR_BUILD_20261002_R3`.

The collector is `RUNNING_READY` only after:
- activation validates;
- runtime marker validates/exists;
- dedicated receptor recovery succeeds;
- a ready marker matching PID, activation hash, Git SHA, protocol, registry, collector version, receptor version, receptor build ID and storage ID exists.

A live PID without these invariants is `RUNNING_NOT_READY`. A live process whose fresh heartbeat reports `CYCLE_ERROR` is `RUNNING_DEGRADED`; it is never reported as READY merely because the process remains alive.

## Prelaunch safety window

Deployment verification, reset, and activation require at least **30 minutes** before the frozen start. The margin is fail-closed; it is never relaxed to rescue a late launch.

## Prelaunch reset

Before a new launch, stale V1 artifacts are removed only through:

`python termux/challenger_deployment_gate.py --reset-local-prelaunch`

The command:
- is forbidden inside the final 30-minute safety window;
- refuses while a Challenger process is alive;
- archives stale generated artifacts;
- does not modify `termux/config.json` or its secrets.

Reset and activation writing are intentionally separate commands.

## Deployment gate

After reset:
1. tracked Git worktree must be clean;
2. CURRENT XRP URL and secret must be present so isolation can be proven;
3. Challenger URL and secret must be non-placeholder and different from CURRENT;
4. dedicated receptor must return the expected receptor version, receptor build ID, spreadsheet ID, protocol version, registry SHA and collector version;
5. no stale local launch artifacts may exist;
6. generated activation must pass the collector's validator;
7. activation is written only with `--write-activation`.

## Recovery completeness

Recovery is based on persistent remote completeness, not on a fixed lookback window.

On startup the receptor returns:
- every V3.2 candidate still missing at least one required outcome horizon;
- every V3.2 candidate newer than the latest persisted health checkpoint, even if its outcomes are already complete;
- existing outcome IDs for those returned candidates;
- the latest compatible health checkpoint.

This prevents two failure modes after loss of local state:
- an old pending candidate being forgotten merely because the outage exceeded a time window;
- a recently persisted complete candidate being regenerated with the same Event ID but a different payload hash before the local cursor is reconstructed.

No candidate is discarded from recovery because of age.

## Storage

Dedicated spreadsheet:
- `XRP_Challenger_Research`
- `14mVe2XXcsVBCojZSbp6A7qQKO2RFpovLtKntOYFDwvA`

Tabs:
- CHALLENGER_CANDIDATES
- CHALLENGER_OUTCOMES
- CHALLENGER_HEALTH
- CHALLENGER_AUDIT

V3.1 audit rows remain historical. V3.2 rows are distinguished by protocol version.

## Scientific rules

Candidate A/B/C rules, horizons, directions and floors are unchanged from V3.1 and are defined normatively in:
- `research/XRP_FORWARD_RESEARCH_PROTOCOL_V3_2.md`
- `research/experiments/XRP_FORWARD_REGISTRY_V3_2.jsonl`

## Holdout

The 2026-01-01 through 2026-08-31 historical holdout remains LOCKED.
