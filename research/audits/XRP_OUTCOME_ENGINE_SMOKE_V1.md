# XRP Outcome Engine Smoke V1 — Approved

## Estado

**PASS**

Fecha: 2026-09-30 UTC.

Outcome engine:
- `OUTCOMES_V1`

Contract:
- `research/HISTORICAL_OUTCOME_CONTRACT_V1.md`

Implementation:
- `research/historical_outcome_engine_v1.py`

Workflow:
- `.github/workflows/xrp-outcome-engine-smoke-v1.yml`

Successful GitHub Actions run:
- `36779599001`

QA artifact:
- `11127387740`

Output SHA-256 from both independent passes:
- `d641fbe0f8351c46bfb7e0d74e89cd89cdbffb380bf7f5b982e9e2fc3cfd1a37`

## Smoke-test boundary

Range:
- 2020-01-06 08:21 UTC
- 2020-02-01 00:00 UTC

This is outside the preregistered discovery period, which starts 2020-02-01.

February 2020 was normalized only as a future buffer so horizons up to 240m near the end of January had exact future bars available.

No hypothesis result was calculated.

## Decision rows processed

Total:
- **39,399**

The outcome engine consumed the decision rows produced by FEATURES_V1 and used XRPUSDT contract 1m as the canonical future-price source.

## Integrity results

- reference-price mismatches: **0**
- duplicate decision keys: **0**
- future target violations: **0**
- non-finite values: **0**
- feature input mutated: **NO**
- exact-target/no-nearest synthetic self-test: **PASS**

## Exact horizon completeness

Forward returns:
- 5m incomplete: **0**
- 15m incomplete: **0**
- 30m incomplete: **0**
- 60m incomplete: **0**
- 240m incomplete: **0**

Excursions:
- 15m incomplete: **0**
- 60m incomplete: **0**
- 240m incomplete: **0**

## Determinism

Pass A SHA-256:
- `d641fbe0f8351c46bfb7e0d74e89cd89cdbffb380bf7f5b982e9e2fc3cfd1a37`

Pass B SHA-256:
- `d641fbe0f8351c46bfb7e0d74e89cd89cdbffb380bf7f5b982e9e2fc3cfd1a37`

Byte comparison:
- **PASS**

## Outcome semantics validated

### Forward returns
For each horizon h:
- target is exactly `decision_time + h`;
- the exact 1m close is required;
- no nearest timestamp fallback;
- no interpolation.

### Excursions
For horizon h:
- window contains only bars with `decision_time < available_at <= decision_time+h`;
- decision bar is excluded;
- exactly h one-minute bars are required;
- otherwise outcome is NA.

The engine stores direction-neutral raw up/down excursion. LONG/SHORT MFE/MAE transformation is deferred to the hypothesis evaluator.

## Discovery remained sealed during QA

The workflow intentionally:
1. used only the warm-up/quality period;
2. did not calculate hypothesis effects;
3. did not report mean forward return;
4. did not report win rate;
5. did not report aggregate MFE/MAE;
6. did not test any registered threshold.

Raw smoke-test outcome CSVs were deleted before artifact upload.

Only QA, hashes and normalization/feature checks were retained.

## Infrastructure fixes discovered by the smoke gate

Two pre-outcome QA issues were found and corrected before any discovery outcome was opened:

1. FEATURES_V1 command-line validation originally rejected a legitimately empty `metrics` table in pre-metrics periods. It now accepts empty metrics where the official archive has not started; features remain NA as specified by the feature contract.
2. The feature QA initially treated BTC EMA200 warm-up as if BTC history began with the first XRP decision row. BTC has valid prehistory before XRP listing, so that row-relative check was removed. Feature formulas were not changed.

Neither fix was based on outcome performance.

## Decision

**OUTCOMES_V1 smoke gate approved.**

The next permitted stage is:

**Open XRP discovery only and evaluate the seven sealed hypotheses in `XRP_HYPOTHESES_V1`.**

Validation 2024-2025 remains sealed.

Historical holdout 2026 remains sealed.
