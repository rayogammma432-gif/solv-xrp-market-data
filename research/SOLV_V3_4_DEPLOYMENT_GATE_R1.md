# SOLV V3.4 R1 — Deployment Gate

## Purpose

Operational gate for `SOLV_FORWARD_V3_4_R1`. This gate changes provenance/security mechanics only; it does not change the frozen SOLV V3.4 trading hypotheses.

Formal start: `2026-10-05T06:00:00Z`  
Readiness cutoff: `2026-10-05T05:30:00Z`

## Required identities

- rule: `SOLV_V3.4`
- master blob: `0ff59cd17cc6f3d59d02e8d6de651fcfd1559b6c`
- receptor: `SOLV_RECEPTOR_V3_4_V2`
- receptor blob: `8b31939253e1aa22ec1340520c8ef2f7460bb157`
- schema: `SOLV_V3_4_SCHEMA_EC_AQ_V1`
- collector blob: `fafad1bc1315cae19e08df1bc257fa6f8172aa62`
- analysis tracker blob: `1d950a9af9d9729d8c12fb6f316ecd37d7fda4cd`
- signal tracker blob: `f4117f5cf38adcccc20132e3139196cd8ae9d1ff`
- spreadsheet ID: `1H6oLPDHQKX3zpKVvWS_FhE3lUNnNtE0uEwLSIFZYPY8`

## Fresh-start sequence

1. Merge the validated hardening PR.
2. On Motorola, pull with `git pull --ff-only` and require a clean tracked worktree.
3. Verify the frozen files match the identities above.
4. Verify the deployed Apps Script receptor still matches the frozen receptor identity. Because this normative amendment does not modify the receptor blob, a new Apps Script deployment is not required if V2 is already deployed and passes health + negative probe.
5. GET the deployed endpoint and require:
   - receptorVersion = `SOLV_RECEPTOR_V3_4_V2`;
   - ruleVersion = `SOLV_V3.4`;
   - schemaVersion = `SOLV_V3_4_SCHEMA_EC_AQ_V1`;
   - spreadsheetId = expected SOLV spreadsheet;
   - signalCols = 43;
   - analysisCols = 133.
6. Run/confirm CI, including allowlist security and thesis-expiry tests from the merged source.
7. Restart the normal collector so the amended analysis tracker is loaded.
8. Confirm MARKET and LIVE_STATE update and SOLV/BTC 1m/5m/15m/1H/4H/1D continue advancing.
9. Confirm the live sheet schema remains SIGNALS A:AQ and ANALYSES A:EC.
10. Verify the Motorola blob identities for master and analysis tracker match this gate.
11. Record the first post-start analysis as R1 only if it occurs at/after the formal start.

## Receptor negative-test contract

Generic `payload.sheets` must reject:
- SIGNALS;
- ANALYSES;
- USER_TRADES;
- PERFORMANCE;
- BACKFILL_QUEUE;
- BACKFILL_EPISODES;
- arbitrary unknown sheet names.

Bootstrap must also reject ALERT_RESEARCH/ALERT_FORWARD/ALERT_MFE_MAE; those are incremental-only.

Rows on allowed generic market/research ingestion tabs must contain exactly 11 columns.

## Fail-closed cases

Do not classify data as R1 if:
- readiness is incomplete at cutoff;
- deployed receptor is still V1 or another identity;
- source/worktree identity cannot be verified;
- sheet schema differs;
- market feed is stale/unsynchronized;
- the receiver accepts a forbidden generic sheet;
- the start has already passed before readiness is proven.

If any condition fails, preserve all data already present but mark the launch abandoned and freeze a new future start. Never backfill the missing interval.

## Prelaunch smoke

`SOLV-20261003T231611Z-AN` is operational smoke only and is excluded from confirmatory R1 evidence.

## Scientific boundary

Passing this gate authorizes prospective evidence collection under the existing SOLV V3.4 policy. It does not validate profitability, promote LONG, change production TP, or increase risk.


## Normative-lock revalidation

Before R1 can return to PRELAUNCH_READY after the 2026-10-04 master audit:
- master must contain explicit PRIMARY and SCALP BASE_PASS rules;
- R1 SCALP risk must be fixed at 0.10%;
- analysis tracker must enforce Thesis Expires UTC as the pre-entry fill deadline;
- a post-expiry first touch must classify as `NO_FILL_EXPIRED`;
- a fill before expiry must remain eligible for TP/STOP tracking after expiry;
- CI tests must cover both expiry cases.
