# XRP Hypothesis Preregistration V2 — Approved

## Estado

**PASS / SEALED BEFORE VALIDATION**

Fecha: 2026-09-30 UTC.

Registry:
- `XRP_HYPOTHESES_V2`

Human-readable:
- `research/XRP_PREREGISTERED_HYPOTHESES_V2.md`

Machine-readable:
- `research/experiments/XRP_HYPOTHESIS_REGISTRY_V2.jsonl`

Seal run:
- `36785094642`

Seal artifact:
- `11129955122`

Registry SHA-256:
- `ab6a355df4699a284ff51ee49ff8e0f944b98e902b87b46384a6957eb9066912`

## V2 hypotheses

1. `XRP-V2-H1-PRIMARY-MOMENTUM-EXHAUSTION`
2. `XRP-V2-H2-PRIMARY-OI-MODERATOR`
3. `XRP-V2-H3-SCALP-TAKER-FLOW-EXHAUSTION`

## Design choices

V2 is explicitly post-discovery.

2020-2023 was used to generate these hypotheses and therefore is not treated as confirmatory evidence for V2.

Each V2 hypothesis has:
- one fixed parameter set;
- no threshold grid;
- fixed validation period;
- fixed primary horizon;
- fixed sample floor;
- fixed economic floor;
- fixed 50% discovery-retention gate;
- fixed quarter-stability gate.

## Excluded V1 families

Not carried into V2:
- extension mean reversion;
- BTC alignment/opposition;
- funding extremes;
- generic OI confirmation.

Reason:
- insufficient stability or sample/economic evidence to justify spending validation multiplicity.

## Validation boundary

Validation:
- 2024-01-01 → 2025-12-31

To protect the 2026 holdout:
- all validation decisions must satisfy `decision_time + 240m < 2026-01-01 00:00 UTC`.

## Multiplicity

Validation contains exactly three preregistered hypotheses.

No within-hypothesis threshold search is allowed.

Holm correction will be applied across the three hypothesis-level p-values.

## Seal validation

Automated seal checks passed:
- exactly 3 expected IDs;
- unique IDs;
- no parameter_grid;
- fixed_parameters present;
- validation dates fixed;
- validation_effect_floor >= economic_floor;
- retention_fraction fixed at 0.5;
- no validation/holdout result fields embedded in registry.

## Decision

**XRP_HYPOTHESES_V2 is sealed.**

The next permitted stage is:
- open validation 2024-2025 only;
- evaluate the three fixed V2 hypotheses;
- keep 2026 historical holdout sealed.
