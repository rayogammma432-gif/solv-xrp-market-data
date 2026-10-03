# SOLV V3.4 — Activation and Rollback Checklist

## Current safe state

The Google Sheet schema is already prepared:
- SIGNALS: A:AQ (43 columns)
- ANALYSES: A:EC (133 columns)

V3.3 remains compatible with the expanded sheet until the receiver and agent instructions are activated. Historical rows must not be rewritten.

## Activation order

### 1. Pull the repository on Termux

```bash
cd ~/solv-xrp-market-data
git pull --ff-only
```

Confirm the following files exist:
- `agents/SOLV_V3_4_MASTER.txt`
- `research/SOLV_V3_4_FORWARD_PROTOCOL.md`
- updated `termux/analysis_tracker.py`
- updated `apps-script/SOLV_Receptor_Incremental.gs`

### 2. Deploy the SOLV Apps Script receiver

In the existing SOLV Apps Script project:
1. Replace the receiver source with the current repository version of `apps-script/SOLV_Receptor_Incremental.gs`.
2. Save.
3. Do not change `SHARED_SECRET`.
4. Deploy > Manage deployments > Edit > New version > Deploy.
5. Keep the same Web App URL used by `config.json`.

Expected GET health:
- receptorVersion = `SOLV_RECEPTOR_V3_4_V1`
- ruleVersion = `SOLV_V3.4`
- schemaVersion = `SOLV_V3_4_SCHEMA_EC_AQ_V1`
- signalCols = `43`
- analysisCols = `133`
- spreadsheetId = `1H6oLPDHQKX3zpKVvWS_FhE3lUNnNtE0uEwLSIFZYPY8`

Do not continue if any of these values differ.

### 3. Activate the SOLV agent master instructions

Replace the SOLV agent's master/system instructions with the complete contents of:
`agents/SOLV_V3_4_MASTER.txt`

Do not merge snippets into V3.3. Use V3.4 as one authoritative rule file.

Expected behavioral invariants:
- LONG => `CONDICIONAL`, `LONG_SHADOW`, risk 0%, no SIGNAL.
- SHORT => may become ACTIVE only when Execution Gate=PASS.
- A direct breakout without defended retest/acceptance cannot bypass anti-chase.
- An expired or duplicate thesis cannot create SIGNAL.
- TP1 1R is shadow-only and never replaces production TP1/TP2.

### 4. Restart the collector

```bash
cd ~/solv-xrp-market-data
bash termux/stop_collector.sh
bash termux/start_collector.sh
bash termux/status_collector.sh
```

The collector must continue updating both SOLV and XRP.

### 5. First prospective smoke analysis

Run one fresh SOLV analysis after collector/receptor/master activation.

Verify the new ANALYSES row:
- BF = `SOLV_V3.4`
- DK = Live Mode
- DL = Execution Gate
- DM = Plan Direction
- DN = Geometry Valid
- DO = stable Thesis ID when a plan exists
- DP = Thesis Expires UTC
- DQ = Thesis Lifecycle
- DZ = Execution Blocker
- EA = Shadow TP1 1R when geometry exists

Do not manually populate DR:DY or EB:EC. Those are tracker telemetry.

### 6. Tracker verification

After enough closed 1m candles exist for the plan, verify the collector can populate:
- DR Entry Filled UTC
- DS First Barrier
- DT Execution Exit UTC
- DU Realized R
- DV Minutes To Fill
- DW Minutes In Trade
- DX Execution Audit Status
- DY Execution Audit Notes
- EB Shadow TP1 First Barrier
- EC Shadow TP1 Realized R

The tracker must use chronological closed 1m candles; never infer barrier order from MFE/MAE.

## Prospective evidence policy

- No retroactive V3.4 promotion.
- No backfill SIGNALS.
- Count unique Thesis IDs, not repeated ANALYSES.
- Keep LONG and SHORT separated.
- Keep PRIMARY and SCALP separated.
- Review only after approximately 50–100 prospective setups or another explicitly preregistered stopping rule.

## Rollback

If receiver health, sheet writes, or collector behavior fails:

1. Keep the expanded sheet columns; they are backward-compatible.
2. Restore SOLV agent master instructions to `agents/SOLV_V3_3_MASTER.txt`.
3. Restore/deploy the prior Apps Script receiver revision.
4. Restart the collector.
5. Do not delete V3.4 rows already generated; preserve them for audit and mark the activation interval separately.

Never roll back by deleting historical SIGNALS, PERFORMANCE, or ANALYSES.
