# XRP V3.4 — Pre-Activation / In-Place Migration

Date: 2026-10-03
Status: ACTIVATION SCHEDULE FROZEN / NOT YET ACTIVATED

Frozen activation:
- `V3.4_ACTIVATION_UTC = 2026-10-04T00:00:00Z`
- Guatemala: `2026-10-03 18:00:00 America/Guatemala`

Readiness cutoff:
- `2026-10-03T23:30:00Z`
- Guatemala: `2026-10-03 17:30:00 America/Guatemala`
- minimum margin: 30 minutes

Machine-readable freeze:
- `research/experiments/XRP_V3_4_ACTIVATION_FREEZE_V1.json`

If deployment/readiness is not fully verified by the cutoff, do not activate late and do not backfill. Freeze a new future activation timestamp instead.

## Goal

Retire V3.3 from the active XRP path and reuse the existing production infrastructure for V3.4.

Active runtime after activation:
- rule: `agents/XRP_V3_4_MASTER.txt`
- receptor: `apps-script/XRP_Receptor_Incremental.gs`
- same Apps Script Web App deployment
- same XRP_Market_Data spreadsheet
- same Termux collector/scheduler
- same `config.json` XRP endpoint and shared secret unless intentionally rotated

## V3.3 preservation

V3.3 is not active after migration.

Frozen recovery/audit sources:
- branch: `archive/xrp-v3.3-final`
- commit: `eec7aa40512771701182fea54d98d4d8dadd423c`
- archive rule: `archive/xrp-v3.3/agents/XRP_V3_3_MASTER.txt`
- archive receptor: `archive/xrp-v3.3/apps-script/XRP_Receptor_Incremental.gs`

The old active file `agents/XRP_V3_3_MASTER.txt` is removed from the normal runtime tree.

## Active receptor migration

The validated V3.4 receptor replaces the contents of:
`apps-script/XRP_Receptor_Incremental.gs`

The provisional duplicate:
`apps-script/XRP_Receptor_V3_4.gs`
is removed.

This intentionally keeps the operational Apps Script filename and deployment path stable.

## Sheet schema

SIGNALS remains backward compatible and is extended A:AQ:
- AM Thesis ID
- AN Rule Version
- AO Direction Score
- AP Execution Score
- AQ Execution Gate

ANALYSES remains backward compatible and is extended A:DY:
- DK:DY V3.4 direction/execution/audit fields.

No historical rows are rewritten.

## Health contract

Before activation, the deployed receptor must answer GET with:
- ok=true
- mode=HEALTH
- receptorVersion=XRP_RECEPTOR_V3_4_V1
- ruleVersion=XRP_V3.4
- schemaVersion=XRP_V3_4_SCHEMA_DY_AQ_V1
- signalCols=43
- analysisCols=129
- spreadsheetId=1ag0yaE0hcDoG8uED4qejfHGlD2OuXZxvUPYZRUzjqG0

## Activation procedure

1. Merge the V3.4 migration PR.
2. Pull exact main SHA on Motorola/Termux.
3. Stop collector.
4. In the EXISTING XRP Apps Script project, replace Code.gs with current `apps-script/XRP_Receptor_Incremental.gs`.
5. Keep the existing `SHARED_SECRET` unless intentionally rotating it.
6. Deploy a new version of the EXISTING Web App deployment so the /exec URL remains stable.
7. Verify GET health contract.
8. Verify the machine-readable freeze still equals `2026-10-04T00:00:00Z` and that the readiness cutoff has not passed.
9. At the scheduled T0, switch the agent rule to `agents/XRP_V3_4_MASTER.txt`.
10. Start collector.
11. Require one successful XRP bootstrap/incremental cycle.
12. Confirm new ANALYSES rows use BF=XRP_V3.4 (without the space; literal expected value is XRP_V3.4) and populate V3.4 fields.
13. Confirm no V3.4 row has Analysis UTC earlier than `2026-10-04T00:00:00Z`.
14. If any identity/schema/time-boundary check fails, restore the archived V3.3 receptor/rule and redeploy the previous Apps Script version.

## Scientific boundary

All observations before `V3.4_ACTIVATION_UTC` remain V3.3.
All V3.4 performance claims begin after T0.
Primary metric: realized expectancy in R.
