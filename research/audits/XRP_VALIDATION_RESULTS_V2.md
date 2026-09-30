# XRP Validation Results V2 — Final Audit

## Estado

**VALIDATION COMPLETE — 0/3 PASS**

Fecha: 2026-09-30 UTC.

Validation run:
- `36785635037`

Final artifact:
- `11130371443`

Run head SHA:
- `02b62524217da155268949ebd950152917dc0146`

Registry SHA-256:
- `ab6a355df4699a284ff51ee49ff8e0f944b98e902b87b46384a6957eb9066912`

Final validation JSON SHA-256:
- `0ecd85c0ca2a69cfc7ea99e75120cc05c7d43c72b272fd7a21f477e818243f62`

Bootstrap:
- 2,000 UTC-day block replicates per hypothesis.

2026 historical holdout:
- **NOT OPENED**

## Boundary

Validation:
- 2024-01-01 00:00 UTC
- through 2025-12-31 before 20:00 UTC

The final four hours of 2025 were purged so that no 240-minute outcome could touch 2026.

## Result summary

| Hypothesis | Status | Effect | CI95 lower | Holm p | Validation effect floor | Sample |
|---|---|---:|---:|---:|---:|---:|
| V2-H1 PRIMARY momentum exhaustion | FAIL | +0.00038718 | -0.00007758 | 0.105332 | 0.00043082 | 5,720 |
| V2-H2 PRIMARY OI moderator | FAIL | +0.00069828 | -0.00028136 | 0.105332 | 0.00041260 | 5,011 |
| V2-H3 SCALP taker-flow exhaustion | FAIL | +0.00006657 | +0.00003509 | 0.0000428709 | 0.00010000 | 93,197 |

## V2-H1 — PRIMARY Momentum Exhaustion

Sample:
- total = 5,720
- LONG = 3,075
- SHORT = 2,645
- unique days = 684
- sample gate: PASS

Effect:
- +0.00038718
- approximately +3.87 bps

Gates:
- effect sign: PASS
- CI95 lower > 0: FAIL
- Holm p < 0.05: FAIL
- economic floor 3 bps: PASS
- validation retention floor 4.308 bps: FAIL
- quarter stability: PASS

Secondary:
- signed 15m mean: +0.00007901
- signed 240m mean: +0.00035337
- MFE 60m mean: 0.00960549
- MAE 60m mean: 0.01113172

Interpretation:
- the exhaustion direction remains positive and temporally stable, but uncertainty is too large and the effect does not retain at least 50% of its discovery reference.

## V2-H2 — PRIMARY OI Momentum Moderator

Sample:
- expansion = 2,423
- contraction = 2,588
- unique days = 652
- sample gate: PASS

Effect:
- +0.00069828
- approximately +6.98 bps difference between expansion and contraction groups

Gates:
- effect sign: PASS
- CI95 lower > 0: FAIL
- Holm p < 0.05: FAIL
- economic floor: PASS
- validation retention floor 4.126 bps: PASS
- quarter stability: PASS

Interpretation:
- the directional relationship replicated in sign, magnitude and temporal stability, but the day-block uncertainty remains too large to establish the preregistered statistical gate.

This remains a potentially useful descriptive moderator, not a validated trading rule.

## V2-H3 — SCALP Taker-Flow Exhaustion

Sample:
- total = 93,197
- LONG = 52,569
- SHORT = 40,628
- unique days = 731
- sample gate: PASS

Effect:
- +0.00006657
- approximately +0.666 bps

Gates:
- effect sign: PASS
- CI95 lower > 0: PASS
- Holm p < 0.05: PASS
- economic floor 1 bp: **FAIL**
- validation retention floor 1 bp: **FAIL**
- quarter stability: PASS

Secondary:
- signed 5m mean: +0.00005423
- signed 30m mean: +0.00007832
- MFE 15m mean: 0.00260569
- MAE 15m mean: 0.00271627

Interpretation:
- this is the strongest statistical replication in V2: the mean-reversion effect is positive, significant after Holm and stable across quarters.
- however, its average effect is below the preregistered minimum economic magnitude.
- therefore it is **not** promoted to a validated challenger.

No post-result lowering of the 1 bp floor is permitted.

## Determinism

Two independent aggregation passes produced identical result files.

SHA-256:
- `0ecd85c0ca2a69cfc7ea99e75120cc05c7d43c72b272fd7a21f477e818243f62`

Determinism gate:
- PASS

## Decision

**No XRP_HYPOTHESES_V2 hypothesis advances to the 2026 historical holdout.**

The 2026 holdout remains sealed.

There is no historically validated XRP challenger at the end of V2.

The next permitted research stage is post-validation diagnosis / V3 experimental design without opening 2026.

Any V3 hypothesis derived from 2020-2025 must be explicitly labeled post-validation. If 2026 is later used to test V3, it cannot simultaneously serve as an untouched final holdout; a genuinely future forward period would then be required for final confirmation.
