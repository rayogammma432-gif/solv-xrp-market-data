# XRP V3.4 — Execution Quality Upgrade

## Status

Prepared as a prospective successor to `XRP_V3.3`.

This change is intentionally versioned instead of editing V3.3 in place. Historical V3.3 analyses, scores, signals, and research remain immutable.

## Why V3.4 exists

A chronological 1-minute audit of completed XRP analysis plans showed that directional correctness and executable trade quality can diverge. A plan can be directionally right but still hit its stop before the expected move develops.

The design sample is diagnostic only. It must not be reused as proof that V3.4 is profitable.

## Changes

1. Split Direction Score from Execution Score.
2. Make plan geometry a hard validation.
3. Promote ATR Stop Stress from shadow telemetry to an execution gate.
4. Require anti-chase/retest discipline when the market is extended.
5. Introduce stable Thesis ID semantics and stronger deduplication.
6. Record plan direction from Entry/Stop/TP geometry.
7. Add chronological execution auditing to ANALYSES.
8. Evaluate expectancy in R as the primary economic metric.
9. Preserve LONG/SHORT stratification and regime labels in performance review.
10. Keep V3.3 frozen for benchmark comparability.
11. Use a separate `apps-script/XRP_Receptor_Incremental.gs`; do not modify the frozen V3.3 receptor.

## New ANALYSES columns

`DK:DY`

- DK Direction Score
- DL Execution Score
- DM Execution Gate
- DN Plan Direction
- DO Geometry Valid
- DP Thesis ID
- DQ Entry Filled UTC
- DR First Barrier
- DS Execution Exit UTC
- DT Realized R
- DU Minutes To Fill
- DV Minutes In Trade
- DW Execution Audit Status
- DX Execution Audit Notes
- DY Execution Blocker

The agent writes DK:DP and DY at analysis time.
The tracker writes DN:DO as deterministic validation and DQ:DX from closed 1m candles.

## Execution audit semantics

The tracker starts from the first full 1m candle after Analysis UTC.

After Entry is touched:
- TP1 first => `First Barrier=TP1`, realized R = TP1 reward/risk.
- Stop first => `First Barrier=STOP`, realized R = -1.
- Both in the same 1m candle => `AMBIGUOUS_*`, no R is invented.
- Entry never touched inside the 240m audit window => `NO_FILL`.
- Filled but no barrier inside the 240m window => `OPEN_240M`.

MFE/MAE remains descriptive and is not used to infer barrier order.

## Prospective validation boundary

V3.4 should begin from an explicit future activation timestamp. Do not relabel old V3.3 rows as V3.4.

Review V3.4 using:
- expectancy in R;
- resolved trade count;
- win rate as secondary;
- LONG and SHORT separately;
- ACTIVE and non-ACTIVE separately;
- unique Thesis ID results;
- fill rate and time-to-fill;
- ambiguous 1m rate;
- execution blockers.

Any parameter changes after activation create a new rule version rather than silently changing V3.4.


## Receptor isolation

V3.4 uses `apps-script/XRP_Receptor_Incremental.gs` as a separate deployment artifact.

The active `apps-script/XRP_Receptor_Incremental.gs` is migrated to V3.4. V3.3 provenance is preserved by immutable Git history plus `archive/xrp-v3.3/` snapshots.

Pre-activation may prepare the new Web App, but the operational XRP endpoint/secret must not switch until the explicit V3.4 activation timestamp.


## SIGNALS provenance and deduplication

The live `SIGNALS` sheet is extended from A:AL to A:AQ:

- AM Thesis ID
- AN Rule Version
- AO Direction Score
- AP Execution Score
- AQ Execution Gate

V3.4 signals must persist these fields at creation time. The V3.4 receptor reads them back for deterministic open-thesis visibility. V3.3 receptor behavior remains unchanged because it still reads only A:AL.


## Read-only deployment probe

`apps-script/XRP_Receptor_Incremental.gs` exposes a GET health response so the new Web App can be deployed and verified without mutating Sheets.

Required pre-activation response:
- `receptorVersion=XRP_RECEPTOR_V3_4_V1`
- `ruleVersion=XRP_V3.4`
- `schemaVersion=XRP_V3_4_SCHEMA_DY_AQ_V1`
- `signalCols=43`
- `analysisCols=129`
- the XRP Market Data spreadsheet ID

The existing Termux XRP endpoint can remain unchanged when the existing Apps Script Web App deployment is updated in place at activation.
