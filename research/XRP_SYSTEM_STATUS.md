# XRP System Status

Generated from the 2026-10-04 audit. This file records operational state; frozen experiment protocols remain authoritative for scientific rules.

| Subsystem | State | Authoritative identity | Notes |
|---|---|---|---|
| XRP CURRENT | ACTIVE | XRP_V3.4 | Live market collector/receptor; SIGNALS A:AQ; ANALYSES A:DY |
| V3.3 | HISTORICAL | archive/xrp-v3.3-final | Never restore as active path without explicit migration |
| Backfill | ACTIVE_MANUAL | RESEARCH_BACKFILL_AGENT_V2 + BACKFILL_FILTER_R1 | Manual only; no SIGNAL/trade creation |
| Challenger V3.1 | ABORTED | no valid prospective evidence | Historical audit only |
| Challenger V3.2 | ABORTED | no prospective evidence | Historical audit only |
| Challenger V3.2 R1 | ABORTED | XRP_FORWARD_V3_2_R1 | Missed 2026-10-04T00:00:00Z start; no backfill allowed |
| Challenger V3.2 R2 | PRELAUNCH_FROZEN | XRP_FORWARD_V3_2_R2 | Start 2026-10-05T00:00:00Z; device/receptor readiness must be verified before cutoff |
| Paired Benchmark V1 | PRELAUNCH | frozen V3.3 CURRENT baseline | Do not silently substitute V3.4 |
| Historical derivatives dataset | REVIEW_REQUIRED | audit artifacts | Missing slots/nonmonotonic source files must remain explicit |

## Current R2 launch boundary

Formal start:
- UTC: `2026-10-05T00:00:00Z`
- America/Guatemala: `2026-10-04 18:00:00`

Readiness cutoff:
- UTC: `2026-10-04T23:30:00Z`
- America/Guatemala: `2026-10-04 17:30:00`

Required before activation:
1. Motorola has the validated R2 commit checked out with a clean tracked worktree.
2. Dedicated Challenger Apps Script is updated from `apps-script/XRP_Challenger_Receptor.gs` and a new Web App version is deployed.
3. Challenger URL/secret are present in local `termux/config.json`, distinct from CURRENT.
4. `python termux/challenger_deployment_gate.py --reset-local-prelaunch` succeeds.
5. `python termux/challenger_deployment_gate.py` returns `PASS_DEPLOYMENT_GATE`.
6. `python termux/challenger_deployment_gate.py --write-activation` succeeds before cutoff.
7. `bash termux/start_challenger_collector.sh` returns `RUNNING_READY`.
8. `bash termux/status_challenger_collector.sh` independently reports ready state.

If any item is not complete before cutoff, R2 is abandoned. It is never backfilled.

## CURRENT receptor security boundary

Generic `payload.sheets` writes are restricted by mode.

Bootstrap:
- XRP/BTC 1m, 5m, 15m, 1H, 4H, 1D only.

Incremental:
- the same market tabs;
- ALERT_RESEARCH;
- ALERT_FORWARD;
- ALERT_MFE_MAE.

Operational/research state tabs including SIGNALS, ANALYSES, USER_TRADES, PERFORMANCE and PAIRED_* are not writable through generic `payload.sheets`.

## Audit snapshot before remediation

At the 2026-10-04 audit:
- XRP_Market_Data live feed was synchronized.
- ALERT_RESEARCH: 388 rows.
- ANALYSIS_ALERT_LINKS: 274 links.
- Backfill unlinked: 114.
- BACKFILL_QUEUE: 215 PRIORITY / 28 DEFERRED / 6 EXACT_DUP.
- BACKFILL_EPISODES: 94 FULL_COMPLETE / 84 OPEN.
- V3.4 analyses: 131; 130 from backfill and 1 current analysis.
- All V3.4 analyses were CONDICIONAL at that snapshot.
- Dedicated Challenger candidates/outcomes/health were still header-only.
- Paired capture infrastructure had captures but no arm decisions/outcomes yet.

These are point-in-time counts, not permanent invariants.
