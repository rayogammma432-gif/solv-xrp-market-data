# XRP Forward Evaluation Contract V3.2

## Status

**FROZEN BEFORE FORMAL V3.2 FORWARD COLLECTION**

Protocol:
- `XRP_FORWARD_V3_2`

Forward start:
- `2026-10-02T12:00:00Z`

Formal common family gate:
- `2027-03-31T12:00:00Z`

Informational A checkpoint:
- `2026-12-31T12:00:00Z`

This contract resolves the evaluation details that must not be chosen after forward outcomes are visible. It does not change candidate thresholds, directions, horizons, economic floors, or the three-hypothesis family.

## Eligible primary rows

For each candidate:
- protocol version must equal `XRP_FORWARD_V3_2`;
- decision time must be at or after the frozen forward start;
- the primary outcome must be mature by the evaluation cutoff:
  `decision_time + primary_horizon + 5m grace <= evaluation_cutoff`;
- primary outcome must be `COMPLETE` for numeric effect estimation;
- Event ID must be unique.

Secondary horizons remain descriptive and can never replace a failed or unavailable primary result.

## Missing primary outcomes

An eligible primary outcome recorded as `INCOMPLETE` is never silently removed to support a PASS claim.

If at least one eligible primary outcome for a candidate is `INCOMPLETE`:
- compute and report descriptive complete-case statistics;
- formal candidate status is `DATA_QUALITY_BLOCKED`;
- do not label the candidate `FORWARD_PASS_RESEARCH`.

This is deliberately fail-closed against selective missingness.

## Candidate A

`XRP-FWD-V3-A-TAKER-EXHAUSTION`

Primary effect:
- mean direction-signed 15m forward return.

Sample gates use COMPLETE primary outcomes:
- >= 90 calendar days elapsed;
- >= 12,000 total;
- >= 3,000 LONG;
- >= 3,000 SHORT;
- >= 75 unique UTC decision days.

Effect floor:
- >= 0.00010.

Temporal stability:
- compute one primary effect for each informative calendar UTC month;
- informative month = at least one COMPLETE primary event;
- median monthly primary effect must be > 0.

## Candidate B

`XRP-FWD-V3-B-OI-MODERATOR`

Primary effect:
- mean `sign(ret_12) * forward_return_60m` in EXPANSION
- minus mean `sign(ret_12) * forward_return_60m` in CONTRACTION.

Sample gates use COMPLETE primary outcomes:
- >= 180 calendar days elapsed;
- >= 600 EXPANSION;
- >= 600 CONTRACTION;
- >= 150 unique UTC decision days.

Effect floor:
- >= 0.00040.

Temporal stability:
- compute the same expansion-minus-contraction effect by calendar UTC quarter;
- a quarter is informative only when both groups are present;
- median informative-quarter effect must be > 0.

B remains a moderator result and is not converted into an entry rule by this evaluation.

## Candidate C

`XRP-FWD-V3-C-MOMENTUM-EXHAUSTION`

Primary effect:
- mean direction-signed 60m forward return.

Sample gates use COMPLETE primary outcomes:
- >= 180 calendar days elapsed;
- >= 1,200 total;
- >= 250 LONG;
- >= 250 SHORT;
- >= 150 unique UTC decision days.

Effect floor:
- >= 0.00043.

Temporal stability:
- compute one primary effect for each informative calendar UTC quarter;
- informative quarter = at least one COMPLETE primary event;
- median quarterly primary effect must be > 0.

## Bootstrap

Unit:
- UTC decision day.

Replicates:
- 2,000.

For each replicate:
1. take the observed eligible UTC decision days for the candidate;
2. sample that same number of days with replacement;
3. include all eligible primary rows belonging to each sampled day;
4. recompute the candidate's primary effect.

The random seed is deterministic:
- derive it from SHA-256 of `protocol_version|candidate_id|formal_family_gate_utc`;
- use the resulting fixed seed for every reproduction of the formal report.

CI:
- percentile 95%;
- lower bound = 2.5th percentile;
- upper bound = 97.5th percentile.

One-sided p-value:
- `(1 + number of bootstrap primary effects <= 0) / (2000 + 1)`.

## Multiplicity

Family:
- A;
- B;
- C.

Method:
- Holm across all three one-sided primary p-values.

A candidate whose primary effect is non-computable receives p = 1.0 for family correction.

Formal significance requires:
- Holm-adjusted p < 0.05.

No candidate is removed from the family because its result is unfavorable or unavailable.

## Formal PASS

`FORWARD_PASS_RESEARCH` requires all of:
1. candidate-specific calendar/sample/day minimums;
2. candidate-specific effect floor;
3. primary CI95 lower > 0;
4. Holm-adjusted one-sided p < 0.05;
5. preregistered temporal stability above;
6. zero eligible primary `INCOMPLETE` outcomes;
7. no unresolved provenance failure.

Otherwise the result is either:
- `FORWARD_FAIL`, when the scientific gate is evaluable and fails; or
- `DATA_QUALITY_BLOCKED`, when missing primary outcomes or provenance prevent a clean confirmatory decision.

## 90-day checkpoint

The A checkpoint on `2026-12-31T12:00:00Z` is informational only.

It cannot:
- promote A;
- alter thresholds;
- alter horizons;
- alter floors;
- alter the bootstrap;
- alter temporal-stability rules;
- remove adverse observations.

## Execution boundary

A statistical PASS is not trading approval.

Any PASS proceeds to:
- `research/XRP_EXECUTION_ECONOMICS_GATE_V1.md`;
- then shadow execution under frozen execution assumptions before any operational use.

## Immutability

After the V3.2 formal start, any change to this evaluation contract creates a new forward protocol/version and a future start. The V3.2 sample is not reused as confirmatory evidence for the changed rule.
