# XRP Hypothesis Preregistration V1 — Approved

## Estado

**PASS / SEALED BEFORE OUTCOMES**

Fecha: 2026-09-30 UTC.

Registry version:
- `XRP_HYPOTHESES_V1`

Human-readable:
- `research/XRP_PREREGISTERED_HYPOTHESES_V1.md`

Machine-readable:
- `research/experiments/XRP_HYPOTHESIS_REGISTRY_V1.jsonl`

Validator:
- `research/validate_xrp_hypothesis_registry_v1.py`

Seal workflow:
- `.github/workflows/seal-xrp-hypothesis-registry-v1.yml`

GitHub Actions run:
- `36778663201`

Seal artifact:
- `11126352331`

Registry SHA-256:
- `54c0694bed4539300dd919f93349b8b33ddc7e5d9d5982efce08270ccba93479`

## Hypotheses sealed

1. `XRP-H1-PRIMARY-MOMENTUM`
2. `XRP-H2-PRIMARY-EXTENSION-REVERSION`
3. `XRP-H3-PRIMARY-OI-CONFIRMATION`
4. `XRP-H4-PRIMARY-OI-MODERATOR`
5. `XRP-H5-PRIMARY-BTC-ALIGNMENT`
6. `XRP-H6-FUNDING-EXTREME-REVERSION`
7. `XRP-H7-SCALP-TAKER-FLOW`

## Statistical controls sealed

- fixed discovery periods per hypothesis;
- fixed threshold search grids;
- fixed primary horizon per hypothesis;
- minimum sample requirements;
- economic effect floors;
- UTC-day block bootstrap;
- Holm correction within each threshold family;
- maximum one selected configuration per hypothesis;
- validation without retuning;
- Holm correction across hypotheses reaching validation.

## Data-coverage constraints sealed

- OI hypotheses start 2022-01-01.
- top-trader ratios are excluded from V1.
- funding hypothesis samples one PRIMARY observation per unique funding event.
- RSI and EMA50-distance are not used as double confirmation because of high contemporaneous redundancy.

## Immutability

After this seal, discovery outcomes may be opened.

The registry V1 must not be modified in response to results. Any change creates `XRP_HYPOTHESES_V2`.

## Next gate

The next permitted stage is:

**Outcome Engine V1 + anti-look-ahead QA**

Only after that engine passes may discovery results be calculated.
