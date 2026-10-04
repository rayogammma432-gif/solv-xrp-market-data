# SOLV V3.4 — Forward Validation Protocol

## Purpose

SOLV V3.4 is a conservative execution-quality revision derived from the historical audit completed on 2026-10-03. It does not claim that SOLV has a validated profitable strategy. Its purpose is to collect clean prospective evidence while preventing the historical failure modes from being promoted to live SIGNALS.

## Locked findings before activation

The audit found:
- 5 historical ACTIVE/SIGNALS, all closed LOSS, total -5R.
- Independent 1m audit after archive coverage: 43 evaluable plans, 11 TP1 / 32 STOP, -12.25R, expectancy about -0.285R.
- Direction split: SHORT 28 plans, 11 TP1 / 17 STOP, +2.75R; LONG 15 plans, 0 TP1 / 15 STOP, -15R.
- A 1R shadow target materially improved the historical SHORT profile, but this is hypothesis-generation only and must not replace the production TP from backfill evidence.

These findings are frozen as pre-V3.4 evidence and must not be recomputed to retroactively promote V3.4.

## V3.4 hypotheses

H1 — LONG_SHADOW:
LONG is research-only until prospective evidence demonstrates an acceptable edge. LONG cannot create ACTIVE/SIGNAL or nonzero risk in V3.4.

H2 — SHORT_EXPERIMENTAL:
SHORT may remain operational only behind the normal motor requirements plus a hard execution gate: trigger, anti-chase, valid geometry, required retest/acceptance after direct breakouts, no major structural contradiction, valid/nonexpired thesis, and no duplicate exposure.

H3 — TP1_1R shadow:
For every valid Entry/Stop plan, calculate a parallel 1R target. This variant is shadow-only and must be evaluated chronologically from closed 1m candles. It never changes the production TP1/TP2 or live risk.

H4 — Thesis lifecycle:
Repeated ANALYSES of the same setup are one correlated thesis, not independent observations. Every plan uses a stable Thesis ID and a pre-entry expiry. Re-entry requires a new structural anchor plus a new closed trigger after expiry/invalidation/closure.

## Prospective-only evaluation

Activation data is prospective. Backfill remains research-only and cannot create SIGNALS.

Evaluate at least 50–100 prospective setups before any permanent promotion, with results separated by:
- LONG vs SHORT
- PRIMARY vs SCALP
- market regime/context
- unique Thesis ID
- live production TP vs shadow 1R

Do not count repeated ANALYSES sharing one Thesis ID as separate setups.

## Primary metrics

For each unique thesis:
- fill/no-fill
- first barrier: TP1 vs STOP, chronologically from 1m
- realized R for the audited plan
- minutes to fill
- minutes in trade
- production outcome
- shadow 1R first barrier and R
- execution blocker
- direction and motor

Ambiguous same-1m-bar outcomes remain AMBIGUOUS and do not receive invented order.

## Promotion rules

LONG remains shadow until a separate prospective review explicitly promotes it. No automatic promotion from score, TradingView, backfill, or a short winning streak.

The shadow 1R variant cannot replace production TP solely because it performed better historically. Promotion requires prospective evidence with adequate sample size and execution-cost review.

SHORT_EXPERIMENTAL may continue while data is collected, but risk must remain at the existing limits and may be reduced/disabled if the prospective sample shows persistent negative expectancy or operational defects.

## Versioning

Rule: `SOLV_V3.4`
Shadow TP variant: `SOLV_TP1_1R_R1`
Schema: `SOLV_V3_4_SCHEMA_EC_AQ_V1`
Receptor: `SOLV_RECEPTOR_V3_4_V2`

V3.3 remains preserved for rollback/audit. Do not overwrite historical V3.3 rows.


## R1 launch contract

The current confirmatory launch is frozen separately as `SOLV_FORWARD_V3_4_R1` in:
- `research/SOLV_FORWARD_V3_4_R1_PREREGISTRATION.md`
- `research/SOLV_V3_4_DEPLOYMENT_GATE_R1.md`

Formal R1 start is `2026-10-05T06:00:00Z` with readiness cutoff `2026-10-05T05:30:00Z`.

All BACKFILL rows and all observations before the formal start are excluded from confirmatory R1 evidence. The live analysis `SOLV-20261003T231611Z-AN` is classified as PRELAUNCH_SMOKE only.

If readiness is not complete before the cutoff, R1 is abandoned and must not be reconstructed or backfilled. A new future start must be preregistered.
