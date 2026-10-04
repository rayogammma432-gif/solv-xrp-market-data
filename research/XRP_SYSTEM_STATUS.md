# XRP System Status

Generated from the 2026-10-04 audit and subsequent normative migrations. This file records operational state; frozen experiment protocols remain authoritative for scientific rules.

| Subsystem | State | Authoritative identity | Notes |
|---|---|---|---|
| XRP CURRENT | ACTIVE_NORMATIVE | XRP_V3.6 | Descriptor entrypoint + immutable V3.5 base + V3.6 Mark-aware anti-chase override; SIGNALS A:AQ; ANALYSES A:DY |
| XRP runtime receptor/schema | COMPATIBLE_REUSE | XRP_RECEPTOR_V3_4_V1 / XRP_V3_4_SCHEMA_DY_AQ_V1 | V3.6 is a rule-only normative upgrade; no Sheet schema migration required |
| XRP analysis tracker | RUNTIME_COMPATIBLE | expiry-aware tracker | Tracker logic is unchanged by V3.6; thesis expiry continues to derive from canonical Thesis ID |
| XRP V3.6 regression guard | MANUAL_GUARD | termux/test_xrp_v36_normative.py | Deterministic truth-table and blob checks committed; automatic Actions hook must be reattached before the next normative change |
| V3.5 | HISTORICAL | agents/XRP_V3_5_MASTER.txt | Never relabel prior rows or signals as V3.6; also serves as immutable base of the V3.6 composite authority |
| V3.4 | HISTORICAL | agents/XRP_V3_4_MASTER.txt | Never relabel prior rows or signals |
| V3.3 | HISTORICAL | archive/xrp-v3.3-final | Never restore as active path without explicit migration |
| Backfill | ACTIVE_MANUAL | RESEARCH_BACKFILL_AGENT_V2 + BACKFILL_FILTER_R1 | Manual only; no SIGNAL/trade creation |
| Challenger V3.1 | ABORTED | no valid prospective evidence | Historical audit only |
| Challenger V3.2 | ABORTED | no prospective evidence | Historical audit only |
| Challenger V3.2 R1 | ABORTED | XRP_FORWARD_V3_2_R1 | Missed 2026-10-04T00:00:00Z start; no backfill allowed |
| Challenger V3.2 R2 | PRELAUNCH_FROZEN | XRP_FORWARD_V3_2_R2 | Start 2026-10-05T00:00:00Z; device/receptor readiness remains governed by its frozen protocol |
| Paired Benchmark V1 | PRELAUNCH | frozen V3.3 CURRENT baseline | Do not silently substitute a later CURRENT |
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

## XRP V3.5 normative migration

The 2026-10-04 master audit found execution-contract ambiguities in XRP_V3.4: ACTIVE could still be reached with anti-chase or execution-context failures under the 4/5 score rule; state/blocker precedence was not deterministic; risk selection and daily halt semantics were underspecified; Thesis ID canonicalization was incomplete; and pre-entry thesis expiry was not frozen for chronological audit.

XRP_V3.5 was activated prospectively and produced live provenance as V3.5. It is not rewritten by V3.6.

V3.5 introduced:
- all-five execution hard gate;
- deterministic state/blocker precedence;
- fixed risk semantics;
- canonical Thesis ID and expiry;
- chronological execution audit;
- GitHub manifest/bootstrap architecture.

## XRP V3.6 Mark-aware anti-chase migration

A live V3.5 smoke test, `XRP-20261004T230928Z-ANALIZA`, exposed a remaining normative mismatch. The plan had Entry `1.5045`, SETUP_ANCHOR `1.5031`, Mark `1.5185`, ATR15m `0.004942`, Direction Score `6/6`, Execution Score `4/5`, Gate `WAIT`, blocker `WAIT_RETEST`.

The operational decision was sensible, but V3.5's canonical anti-chase formula only measured `ABS(Entry-SETUP_ANCHOR)/ATR15m ≈ 0.28`, which passed. The actual Mark was approximately `2.83 ATR` beyond the candidate Entry. The row remains V3.5 and is not relabeled.

V3.6 is prospective and defines:
- `entryAnchorDist = ABS(Entry-SETUP_ANCHOR)/ATR15m`;
- LONG `markEntryExtension = MAX(0,(MarkPrice-Entry)/ATR15m)`;
- SHORT `markEntryExtension = MAX(0,(Entry-MarkPrice)/ATR15m)`;
- E2 PASS only when both distances are <=0.50 and `RR_real>=1.5`;
- otherwise `WAIT_RETEST` unless a higher-precedence rule applies;
- TradingView remains context only and cannot determine E2.

V3.6 intentionally reuses the V3.4 receptor/schema and the V3.5 expiry-aware tracker. No Sheet schema or Apps Script migration is required.

Authoritative descriptor-composite:
- manifest: `agents/XRP_MASTER_MANIFEST.json`;
- bootstrap: `agents/XRP_PROJECT_BOOTSTRAP.txt`;
- descriptor/master entrypoint: `agents/XRP_V3_6_MASTER.txt`;
- BASE: `agents/XRP_V3_5_MASTER.txt`;
- OVERRIDE: `agents/XRP_V3_6_OVERRIDE.txt`;
- tracker: `termux/analysis_tracker.py`.

Performance reporting must stratify V3.4, V3.5 and V3.6.

## Project-instructions loader architecture

ChatGPT Project instructions for XRP should contain only `agents/XRP_PROJECT_BOOTSTRAP.txt`.

The bootstrap resolves the manifest and status directly from GitHub. For V3.6 the manifest declares `master_mode=descriptor_composite`. `master_path` points to `agents/XRP_V3_6_MASTER.txt`, which identifies V3.6 and obligatorily loads/verifies the full immutable V3.5 BASE plus the V3.6 OVERRIDE. This preserves compatibility with Project Bootstrap V1: even an older loader that only follows `master_path` reaches the complete V3.6 authority.

The versioned regression guard is `termux/test_xrp_v36_normative.py`. It verifies both pinned blobs and the Mark-aware LONG/SHORT truth table. Automatic GitHub Actions attachment is currently pending; until it is reattached, the regression test must be run explicitly before any further normative change.

The BASE remains intentionally larger than 8,000 characters and must never be compacted merely to fit Project instructions. The override is a narrow prospective delta, not a replacement summary of the base.
