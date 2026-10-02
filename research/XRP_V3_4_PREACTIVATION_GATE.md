# XRP V3.4 — Pre-Activation Gate

Date: 2026-10-02
Status: SOFTWARE PRE-ACTIVATION PASS / DEPLOYMENT PROBE PENDING

## Tested source

Branch:
- `xrp-v3-4-preactivation-isolated`

CI gate:
- workflow: `XRP V3.4 preactivation gate`
- run: `37043458173`
- tested head SHA: `30ed207c54e65c746472500cb2543d40afd69b0b`
- conclusion: PASS

Tested blobs:
- Rule: `agents/XRP_V3_4_MASTER.txt` = `c90108d168d07ee2db5bf7c341e0860dc6537163`
- V3.4 receptor: `apps-script/XRP_Receptor_V3_4.gs` = `2d6b5c1a8ac09bdb377dac90898d25f2551454ee`
- Analysis tracker: `termux/analysis_tracker.py` = `37bba52f849d60d78f5c9fcd2fd76cfb964810b1`
- Gate workflow = `1cdae06d0f06f44f843db0255d158d578ad690cb`

## Automated gates passed

1. Python compilation:
   - analysis_tracker.py
   - market_collector.py
   - signal_tracker.py
2. Chronological execution audit unit tests:
   - LONG TP1 first
   - SHORT STOP first
   - same-1m ambiguity
   - invalid geometry fail-closed
3. Forward V3.2 tracker regression harness.
4. Apps Script V3.4 receptor JavaScript syntax.
5. V3.4 schema contract:
   - SIGNALS A:AQ / 43 columns
   - ANALYSES A:DY / 129 columns
   - V3.4 health constants
   - chronological execution audit fields
6. Frozen baseline preservation:
   - agents/XRP_V3_3_MASTER.txt unchanged
   - agents/XRP_PAIRED_CURRENT_RUNNER_V1.md unchanged
   - apps-script/XRP_Receptor_Incremental.gs unchanged

## Live Google Sheet schema verified

Spreadsheet: XRP_Market_Data

SIGNALS:
- existing A:AL preserved
- AM Thesis ID
- AN Rule Version
- AO Direction Score
- AP Execution Score
- AQ Execution Gate

ANALYSES:
- existing A:DJ preserved
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

The schema extension is backward-compatible with the current V3.3 receptor because V3.3 continues reading only its historical column ranges.

## Isolation decision

V3.4 MUST NOT modify or redeploy:
- `apps-script/XRP_Receptor_Incremental.gs`

V3.4 MUST use:
- `apps-script/XRP_Receptor_V3_4.gs`
- a separate Apps Script Web App deployment
- a V3.4-specific shared secret

This prevents V3.4 work from invalidating the frozen V3.3 paired-benchmark provenance.

## Deployment health contract

Before switching the operational XRP endpoint, deploy the V3.4 receptor separately and GET its Web App URL.

Required response:
- `ok=true`
- `mode=HEALTH`
- `receptorVersion=XRP_RECEPTOR_V3_4_V1`
- `ruleVersion=XRP_V3.4`
- `schemaVersion=XRP_V3_4_SCHEMA_DY_AQ_V1`
- `signalCols=43`
- `analysisCols=129`
- `spreadsheetId=1ag0yaE0hcDoG8uED4qejfHGlD2OuXZxvUPYZRUzjqG0`

GET/health is read-only and must not mutate Sheets.

## Activation blockers remaining

These are deliberately NOT completed during pre-activation:

1. Merge the final reviewed V3.4 PR.
2. Pull the exact merge SHA on the Motorola/Termux runtime.
3. Deploy `XRP_Receptor_V3_4.gs` as a NEW Apps Script Web App version/project.
4. Set a V3.4-specific `SHARED_SECRET`.
5. Verify the read-only health contract above.
6. Freeze an explicit future `V3.4_ACTIVATION_UTC`.
7. At that timestamp only:
   - switch the XRP Web App URL/secret in runtime config;
   - switch the agent rule to `XRP_V3.4`;
   - record the exact merge SHA, rule blob SHA, receptor deployment/version and activation UTC.
8. Run one post-switch bootstrap/incremental smoke and require:
   - receptor reports V3.4 identity;
   - MARKET/LIVE_STATE update normally;
   - openSignals returns A:AQ fields;
   - pendingAnalyses returns A:DY V3.4 fields;
   - no historical row is relabeled V3.4.
9. If any identity/schema check fails, revert endpoint/rule to V3.3 and do not classify the attempt as a valid V3.4 prospective start.

## Scientific boundary

The historical sample used to design V3.4 is not validation evidence.

V3.4 performance begins only at the frozen activation timestamp. Primary economic metric:
- expectancy in realized R.

Secondary/diagnostic breakdowns:
- win rate;
- fill rate;
- ACTIVE vs non-ACTIVE;
- LONG vs SHORT;
- unique Thesis ID;
- Direction Score / Execution Score;
- execution blocker;
- time to fill / time in trade;
- ambiguous 1m rate.

Any change to thresholds or gate semantics after activation requires a new version rather than silently editing XRP_V3.4.
