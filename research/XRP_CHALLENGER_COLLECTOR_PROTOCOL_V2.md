# XRP Challenger Independent Collector Protocol V2

## Status

**PRELAUNCH — CLEAN RELAUNCH FOR XRP_FORWARD_V3_2**

Formal start:
- 2026-10-02T12:00:00Z
- 2026-10-02 06:00:00 Guatemala (UTC-06:00)

V1/V3.1 disposition:
- deployment attempt aborted;
- no V1/V3.1 rows are accepted as prospective evidence;
- V2 never reuses V1 activation/runtime/state/PID files.

## Research semantics

V2 preserves the V3.1 hypotheses unchanged and implements:
- upstream protocol: XRP_FORWARD_V3_2
- upstream registry SHA256: 94babcf11323827e1ec7e77cc4c64977c5a656794cef0b1e2c2056c0cc2f34f9
- A/C directional research candidates
- B OI moderator research-only
- no trading, orders, SIGNALS or Telegram trade alerts.

## Process isolation

CURRENT:
`Binance → market_collector.py → operational receptor → XRP_Market_Data`

CHALLENGER V2:
`Binance → xrp_challenger_collector_v2.py → dedicated receptor → XRP_Challenger_Research`

The V2 collector:
- does not import market_collector.py;
- owns its own state, runtime marker, heartbeat, PID and logs;
- uses a dedicated URL and secret distinct from CURRENT.

## Versioned local artifacts

- activation: termux/challenger_v2_activation.json
- runtime: termux/challenger_v2_runtime.json
- state: termux/challenger_v2_forward_state.json
- heartbeat: termux/challenger_v2_heartbeat.json
- PID: termux/challenger_v2_collector.pid
- logs: termux/logs/challenger_v2_*.log

V1 artifacts cannot satisfy any V2 guard.

## Activation invariants

A valid V2 activation requires:
- enabled=true;
- protocol XRP_FORWARD_V3_2;
- exact V3.2 registry SHA;
- formal start 2026-10-02T12:00:00Z;
- exact deployed collector Git HEAD;
- receptor XRP_RECEPTOR_CHALLENGER_V2_R1;
- dedicated spreadsheet ID;
- deployment verification strictly before formal start.

A post-start process is authorized only by a valid V2 runtime marker whose:
- first_boot_utc is before formal start;
- activation_sha256 matches the activation exactly.

Local state existence never substitutes for the runtime marker.

## Preflight and receptor semantics

Preflight:
- validates activation;
- verifies tracked source content is clean;
- ignores Android/Termux executable-bit-only noise;
- probes the receptor without mutating tracker state;
- verifies receptor version and spreadsheet identity.

On live startup:
1. validate activation;
2. probe receptor identity;
3. create runtime marker pre-start;
4. reconcile remote recovery;
5. write heartbeat;
6. enter the cycle loop.

The runtime marker is therefore not created before the receptor has been successfully verified.

## Deployment gate

`termux/challenger_deployment_gate_v2.py`:
- requires >=30 minutes lead;
- validates URL/secret isolation;
- rejects placeholders;
- probes receptor;
- validates the activation object;
- writes the V2 activation only after all checks pass;
- reuses an existing valid activation idempotently;
- never silently overwrites an invalid activation;
- refuses ambiguous V2 runtime/state artifacts without an activation.

## Start/status/stop

Use only:
- `bash termux/start_challenger_collector_v2.sh`
- `bash termux/status_challenger_collector_v2.sh`
- `bash termux/stop_challenger_collector_v2.sh`

The scripts do not need executable bits.

Start performs a foreground preflight before backgrounding.
Status reads V2 PID + V2 heartbeat + V2 logs only.
Historical V1 log lines cannot be mistaken for current health.

## Storage

Dedicated spreadsheet:
- XRP_Challenger_Research
- ID: 14mVe2XXcsVBCojZSbp6A7qQKO2RFpovLtKntOYFDwvA

Tabs:
- CHALLENGER_CANDIDATES
- CHALLENGER_OUTCOMES
- CHALLENGER_HEALTH
- CHALLENGER_AUDIT

Expected receptor:
- XRP_RECEPTOR_CHALLENGER_V2_R1
- Script Property: CHALLENGER_SHARED_SECRET

## Holdout

2026-01-01 through 2026-08-31 remains LOCKED.
