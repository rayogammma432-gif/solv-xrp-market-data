# XRP Forward V3.1 Capture Protocol V1

## Estado

**READY FOR DEPLOYMENT — PRE-FORWARD**

Forward start:
- `2026-10-01T06:00:00Z`

Historical holdout:
- 2026-01-01 → 2026-08-31
- **LOCKED**

## Data flow

`Binance official REST → ForwardV3Tracker → XRP receptor → Google Sheets`

V3.1 does not use CURRENT-agent decisions and does not write:
- SIGNALS
- ANALYSES
- USER_TRADES
- orders

## Catch-up

The tracker independently retrieves XRPUSDT 1m klines using `startTime/endTime` and paginates in bounded windows.

It evaluates every decision after the last evaluated timestamp in chronological order.

This fixes the V3 pre-launch weakness where multiple recovered bars could be reduced to only the latest bar.

## PRIMARY parity

PRIMARY_15M is reconstructed from 15 exact, consecutive 1m bars aligned to UTC.

It does not use the native Binance 15m kline as the V3.1 feature source.

Resampling semantics match HIST_NORM_V1:
- aligned 15m bucket;
- first open;
- max high;
- min low;
- last close;
- sum volume;
- sum quote volume;
- sum trades;
- sum taker-buy base/quote;
- incomplete bucket excluded.

## OI availability

Live OI uses Binance `openInterestHist` period=5m with explicit `startTime/endTime`.

A source timestamp t is usable only at t+5m.

`oi_chg_15m` requires the exact source timestamp t-15m.

No future nearest and no interpolation.

If provider retention prevents recovery:
- Candidate B is not fabricated;
- OI failure is recorded in health.

## Persistent tables

### FORWARD_V3_EVENTS
29 columns:
- 27 collector fields;
- Receptor Version;
- Receptor Write UTC.

Collector provenance includes:
- protocol/registry;
- feature/live-equivalence version;
- collector version;
- collector Git SHA;
- canonical payload SHA256.

### FORWARD_V3_OUTCOMES
21 columns:
- 19 collector fields;
- Receptor Version;
- Receptor Write UTC.

### FORWARD_V3_HEALTH
23 columns, one finalized row per UTC hour:
- expected/evaluated/missing 1m;
- expected/evaluated/missing 15m;
- OI checks/failures;
- event counts A/B/C;
- pending events;
- incomplete outcomes;
- last evaluated 1m/15m;
- code provenance.

Health hour finalization waits 10 minutes after the hour.

## State recovery

During XRP bootstrap, Termux requests `forwardV3Recovery`.

The receptor returns:
- recent V3.1 event rows;
- recent Outcome IDs;
- latest health row.

Termux reconstructs pending horizons and last evaluated decision timestamps.

Therefore `forward_v3_state.json` is a cache/durable retry layer, not the only recovery source.

## Outcome semantics

For horizon h:
- target = decision_time + h exactly;
- exact 1m bars required;
- decision bar excluded;
- no nearest;
- no interpolation.

A temporarily missing minute receives 5 minutes grace.

If still missing:
- Completeness=INCOMPLETE;
- return/up/down remain blank.

## Tests

GitHub Actions:
- `.github/workflows/xrp-forward-v3-1-capture-smoke.yml`

Successful gate must demonstrate:
- pre-start blocking;
- multi-bar catch-up;
- pagination beyond 1,500 minutes;
- historical/live 15m resample parity;
- feature parity for ret_12, rel_volume20 and taker imbalance;
- remote recovery;
- health missing-bar detection;
- Python syntax;
- Apps Script syntax.

## Deployment boundary

GitHub changes alone do not update the Motorola or deploy Apps Script.

Before `2026-10-01T06:00:00Z`:
1. Motorola: pull repository.
2. Restart collector from the pulled tree.
3. Update XRP Apps Script source to current `apps-script/XRP_Receptor_Incremental.gs`.
4. Redeploy web app preserving endpoint permissions and SHARED_SECRET.
5. Confirm receptor response version `XRP_RECEPTOR_FORWARD_V3_1_V1`.
6. Confirm FORWARD_V3_EVENTS / OUTCOMES / HEALTH headers.
7. Run dry/smoke checks.
8. Do not backfill 00:00–05:59 UTC as V3.1 events.

If deployment is not verified before the frozen start, the protocol must be versioned again before using a later start.
