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

### Phase A — preparation before the cutover

1. Pull the exact validated `main` SHA on Motorola/Termux and require a clean tracked worktree.
2. Keep the current collector running during preparation; do **not** stop it hours before T0.
3. Confirm the operational sheet still contains zero `XRP_V3.4` rows in ANALYSES Rule Version and SIGNALS Rule Version.
4. Prepare the current `apps-script/XRP_Receptor_Incremental.gs` in the EXISTING XRP Apps Script project, but do not create any V3.4 analysis before T0.
5. Keep the existing `SHARED_SECRET` and `/exec` URL unless intentionally rotating them.

### Phase B — brief receptor cutover, completed by the readiness cutoff

Complete this phase before:
- `2026-10-03T23:30:00Z`
- `2026-10-03 17:30:00 America/Guatemala`

6. Stop the collector only for the short receptor deployment window.
7. Replace Code.gs with the current `apps-script/XRP_Receptor_Incremental.gs`.
8. Deploy a new version of the EXISTING Web App deployment so the `/exec` URL remains stable.
9. Verify the GET health contract exactly.
10. Verify the machine-readable activation freeze still equals `2026-10-04T00:00:00Z`.
11. Restart the collector after receptor health passes; V3.3 remains the active agent rule until T0.
12. Require one successful normal XRP market-data/bootstrap or incremental cycle before the cutoff.

If any Phase B check fails or Phase B is not complete by 17:30 Guatemala:
- keep/restore V3.3;
- do not start V3.4 at 18:00;
- freeze a new future T0.

### Phase C — exact activation at T0

At:
- `2026-10-04T00:00:00Z`
- `2026-10-03 18:00:00 America/Guatemala`

13. Switch the agent rule to `agents/XRP_V3_4_MASTER.txt`.
14. Do not relabel any earlier V3.3 row.
15. Require the first post-T0 V3.4 analysis to persist `BF=XRP_V3.4` and populate the V3.4 fields.
16. Confirm no V3.4 ANALYSES or SIGNALS row has a timestamp earlier than T0.
17. If any rule/schema/time-boundary check fails, stop V3.4 use and restore the archived V3.3 rule/receptor state before generating further analyses.

## Scientific boundary

All observations before `V3.4_ACTIVATION_UTC` remain V3.3.
All V3.4 performance claims begin after T0.
Primary metric: realized expectancy in R.
