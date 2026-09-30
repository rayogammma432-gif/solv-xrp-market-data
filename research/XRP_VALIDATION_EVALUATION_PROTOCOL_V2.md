# XRP Validation Evaluation Protocol V2

## Estado

**FROZEN BEFORE VALIDATION OUTCOMES**

Inputs:
- `XRP_HYPOTHESES_V2`
- `FEATURES_V1`
- `OUTCOMES_V1`

Validation:
- 2024-01-01 00:00 UTC → 2025-12-31 before 20:00 UTC

2026 historical holdout:
- remains sealed

## Boundary purge

To ensure no validation outcome touches 2026:

`decision_time + 240m < 2026-01-01 00:00 UTC`

Operational last eligible decision:
- strictly before 2025-12-31 20:00 UTC.

## Fixed hypotheses

Validation contains exactly three fixed hypotheses:
1. XRP-V2-H1-PRIMARY-MOMENTUM-EXHAUSTION
2. XRP-V2-H2-PRIMARY-OI-MODERATOR
3. XRP-V2-H3-SCALP-TAKER-FLOW-EXHAUSTION

No threshold search is allowed.

## Directional transformation

For direction d ∈ {+1,-1}:
- signed_forward_h = d * forward_return_h
- LONG MFE_h = raw_up_excursion_h
- LONG MAE_h = -raw_down_excursion_h
- SHORT MFE_h = -raw_down_excursion_h
- SHORT MAE_h = raw_up_excursion_h

## UTC-day block bootstrap

Resampling unit:
- UTC calendar day.

Replicates:
- 2,000 exactly.

Directional hypotheses:
- replicate effect = total signed-return sum across sampled day blocks / total eligible rows.

Comparative OI hypothesis:
- replicate effect = mean signed return expansion - mean signed return contraction.

If a comparative replicate has an empty group, redraw.

Deterministic seed:
- SHA-256-derived from registry SHA, hypothesis ID and `XRP_VALIDATION_BOOTSTRAP_V2`.

## Confidence interval and p-value

CI:
- percentile bootstrap 95%.

p-value:
- one-sided bootstrap-normal using bootstrap SD.

If bootstrap SD = 0:
- p=0 when observed effect > 0;
- p=1 otherwise.

## Holm correction

Apply Holm step-down across all three hypothesis-level one-sided p-values with computable effects.

No hypothesis is removed from the multiplicity family for poor sample or poor effect.

## Quarter stability

Validation has 8 calendar quarters.

Directional hypotheses:
- informative quarter requires >=100 eligible rows.

OI comparative:
- informative quarter requires >=50 expansion and >=50 contraction rows.

Pass:
- >=4 informative quarters;
- median primary effect across informative quarters > 0.

## Sample minimums

Exactly as sealed in XRP_HYPOTHESES_V2.

## Effect floor

Validation requires:

`observed_effect >= validation_effect_floor`

where validation_effect_floor was sealed as the maximum of:
- economic floor;
- 50% of discovery reference effect.

No floor may be lowered after opening validation.

## Validation pass

A hypothesis is `VALIDATION_PASS` only if all are true:
1. sample minimum pass;
2. observed effect > 0;
3. CI95 lower > 0;
4. Holm-adjusted p < 0.05;
5. economic floor pass;
6. validation-effect-floor pass;
7. quarter-stability pass.

## Secondary diagnostics

For directional hypotheses only:
- report preregistered secondary horizons and MFE/MAE;
- secondary metrics never determine pass/fail.

## Reproducibility

Workflow must retain:
- V2 registry SHA;
- evaluator code commit;
- per-part feature/outcome hashes;
- full result JSON;
- validation result for all 3 hypotheses;
- explicit confirmation that 2026 was not opened.

Raw feature/outcome CSVs are temporary and are removed before artifact upload.

## Next gate

If one or more hypotheses pass:
- freeze challenger specification before opening 2026 holdout.

If none pass:
- keep 2026 sealed;
- V2 ends without validated challenger.
