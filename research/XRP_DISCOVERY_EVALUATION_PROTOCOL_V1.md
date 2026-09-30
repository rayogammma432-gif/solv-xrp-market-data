# XRP Discovery Evaluation Protocol V1

## Estado

**FROZEN BEFORE DISCOVERY OUTCOMES**

Inputs:
- XRP_HYPOTHESES_V1
- FEATURES_V1
- OUTCOMES_V1

Discovery:
- 2020-02-01 00:00 UTC → 2024-01-01 00:00 UTC

Validation:
- remains sealed

2026 holdout:
- remains sealed

## Boundary purge

To prevent discovery labels from using validation-period prices, all discovery decision rows must satisfy:

`decision_time + 240m < 2024-01-01 00:00 UTC`

Operationally, the final eligible decision time is strictly before:
- 2023-12-31 20:00 UTC.

This applies to every hypothesis, even when its primary horizon is shorter than 240m.

Internal year boundaries are not experimental boundaries. A January buffer from the next discovery year may be used only to complete outcomes for decisions from the previous discovery year.

## Directional transformation

For direction d ∈ {+1,-1}:
- signed_forward_h = d * forward_return_h
- LONG MFE_h = raw_up_excursion_h
- LONG MAE_h = -raw_down_excursion_h
- SHORT MFE_h = -raw_down_excursion_h
- SHORT MAE_h = raw_up_excursion_h

Rows missing a required preregistered feature or primary outcome are ineligible for that configuration.

## UTC-day block bootstrap

Resampling unit:
- UTC calendar day.

Replicates:
- 2,000 exactly.

A bootstrap replicate samples N eligible UTC days with replacement, where N is the number of eligible unique days for that configuration.

Directional hypothesis replicate effect:
- total signed-return sum across sampled day blocks / total eligible rows across sampled blocks.

Comparative hypothesis replicate effect:
- group-A mean signed return minus group-B mean signed return using all rows in sampled day blocks.

Replicates with an empty required comparative group are discarded and redrawn.

Random seed:
- deterministic SHA-256-derived seed from:
  - registry SHA-256;
  - hypothesis ID;
  - canonical config ID;
  - string `XRP_DISCOVERY_BOOTSTRAP_V1`.

## Confidence interval

Primary CI:
- percentile bootstrap 95%;
- lower = 2.5th percentile;
- upper = 97.5th percentile.

A configuration must have:
- raw bootstrap CI lower > 0.

## Multiplicity / Holm

For each configuration, calculate a one-sided bootstrap-normal p-value:

- bootstrap_se = sample SD of the 2,000 block-bootstrap effects;
- z = observed_effect / bootstrap_se;
- p_one_sided = 1 - NormalCDF(z).

If bootstrap_se = 0:
- p=0 if effect>0;
- p=1 otherwise.

Within each hypothesis ID:
- apply Holm step-down adjustment across every preregistered threshold configuration;
- no configuration is removed from the multiplicity family because of an unfavorable result;
- configurations that fail sample minimums remain reported but are marked ineligible; Holm is applied to all configurations with a computable primary effect.

Operational significance pass:
1. percentile CI95 lower > 0; and
2. Holm-adjusted one-sided p < 0.05.

This freezes the phrase “after multiplicity control” before discovery results are opened.

## Quarter stability

A configuration does not pass discovery if its effect is concentrated in a single calendar quarter.

For each calendar quarter, compute the same primary effect using that quarter only.

An **informative quarter** requires:

Directional hypotheses:
- at least max(25, 5% of the preregistered minimum_total) eligible rows;
- where minimum_total is not specified, use 25 rows.

Comparative hypotheses:
- each required group has at least max(15, 5% of the preregistered minimum_each_group).

Quarter-stability pass requires:
1. at least 4 informative quarters; and
2. median primary effect across informative quarters > 0.

No quarter threshold is optimized from outcomes.

## Minimum sample

Exactly as preregistered.

Directional:
- total rows;
- LONG/SHORT rows;
- unique UTC days.

Comparative:
- group A / group B rows;
- unique UTC days.

Funding H6:
- first PRIMARY_15M decision after each unique funding event;
- a funding event may appear only once across the full discovery period.

## Economic floor

Exactly as preregistered and applied to the observed primary effect.

## Configuration pass

A config is `DISCOVERY_PASS` only when all are true:
- sample minimum pass;
- observed effect > 0;
- bootstrap CI lower > 0;
- Holm-adjusted p < 0.05;
- economic floor pass;
- quarter stability pass.

## Selection

Per hypothesis ID:
- select at most one config;
- among DISCOVERY_PASS configs, select the greatest observed primary effect;
- deterministic tie-break: canonical lexicographic config ID.

If none pass:
- hypothesis status = `DISCOVERY_FAIL`.

No threshold is changed.

## Secondary diagnostics

For selected configurations only, report preregistered secondary horizons and MFE/MAE where specified.

Secondary diagnostics:
- do not determine discovery pass;
- do not trigger threshold retuning;
- are descriptive only.

## Reproducibility

The discovery workflow must retain:
- sealed registry SHA;
- evaluator commit SHA;
- per-year partial hashes;
- full result JSON;
- all config results, including failures;
- selected config or explicit DISCOVERY_FAIL.

Raw full feature/outcome CSVs should not be committed to Git.
