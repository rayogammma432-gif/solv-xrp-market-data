# XRP Discovery Results V1 — Final Audit

## Estado

**DISCOVERY COMPLETE — 0/7 PASS**

Fecha: 2026-09-30 UTC.

Discovery run:
- `36782511942`

Final artifact:
- `11129261007`

Run head SHA:
- `8d787c55105cba338a41b012e27ca4468a1300ca`

Registry SHA-256:
- `54c0694bed4539300dd919f93349b8b33ddc7e5d9d5982efce08270ccba93479`

Final discovery JSON SHA-256:
- `6f61495740f4f5fac04f44b1219b869f78bbeae117f920d1f6ea24f3885b379b`

Bootstrap:
- 2,000 UTC-day block replicates per configuration.

Validation 2024-2025:
- **NOT OPENED**

2026 historical holdout:
- **NOT OPENED**

## Boundary

Discovery decisions:
- 2020-02-01 00:00 UTC
- through 2023-12-31 before 20:00 UTC

The final four hours of 2023 were purged so that a 240-minute outcome could not touch 2024 validation data.

## Result summary

| Hypothesis | Result | Best observed preregistered effect* | CI95 lower | Holm p | Selected |
|---|---|---:|---:|---:|---|
| H1 PRIMARY momentum | FAIL | -0.00024370 | -0.00047991 | 1.000000 | NO |
| H2 extension reversion | FAIL | +0.00017348 | -0.00015138 | 0.572471 | NO |
| H3 OI confirmation | FAIL | +0.00033852 | -0.00052293 | 1.000000 | NO |
| H4 OI moderator | FAIL | +0.00124206 | -0.00160645 | 0.767959 | NO |
| H5 BTC alignment | FAIL | -0.00060014 | -0.00149400 | 1.000000 | NO |
| H6 funding extreme reversion | FAIL | -0.00006766 | -0.00533555 | 1.000000 | NO |
| H7 taker-flow continuation | FAIL | -0.00006492 | -0.00008517 | 1.000000 | NO |

\* The displayed failed-hypothesis value is diagnostic only. No failed configuration is selected.

## Gate counts by family

### H1 — PRIMARY Momentum Continuation

- 9/9 configs: sample minimum PASS
- 0/9 positive effect
- 8/9 CI95 entirely below zero
- 0/9 economic floor PASS
- 0/9 quarter stability PASS
- 0/9 Holm PASS

Effect range:
- -0.00155315 → -0.00024370

Conclusion:
- the preregistered continuation direction is rejected in discovery.

### H2 — PRIMARY Extension Mean Reversion

- 4/4 sample PASS
- 3/4 positive effect
- 0/4 CI95 lower > 0
- 0/4 economic floor PASS
- 2/4 quarter stability PASS
- 0/4 Holm PASS

Effect range:
- -0.00002264 → +0.00017348

Conclusion:
- weak/inconclusive mean-reversion effect; no configuration reaches the preregistered economic/statistical gate.

### H3 — PRIMARY OI-Confirmed Momentum

- 9/9 sample PASS
- 6/9 positive effect
- 0/9 CI95 lower > 0
- 2/9 economic floor PASS
- 1/9 quarter stability PASS
- 0/9 Holm PASS

Effect range:
- -0.00009634 → +0.00033852

Conclusion:
- no robust OI-confirmed momentum configuration.

### H4 — PRIMARY OI as Momentum Moderator

- 7/9 sample PASS
- 9/9 positive effect
- 8/9 economic floor PASS
- 7/9 quarter stability PASS
- 1/9 raw CI95 lower > 0
- 0/9 Holm PASS

Closest preregistered config:
- `abs_ret_12=0.005|abs_oi_chg_15m=0.005`
- effect: +0.00082520
- CI95: [+0.00001107, +0.00172175]
- raw one-sided p: 0.0328094
- Holm p: 0.295285
- expansion n: 2,810
- contraction n: 2,937
- unique days: 693
- quarter stability: PASS

Conclusion:
- H4 is the closest family, but it **fails the preregistered multiplicity gate** and therefore cannot advance under V1.

### H5 — PRIMARY BTC Alignment Moderator

- 9/9 sample PASS
- 0/9 positive effect
- 1/9 CI95 entirely below zero
- 0/9 economic floor PASS
- 0/9 quarter stability PASS
- 0/9 Holm PASS

Effect range:
- -0.00075149 → -0.00060014

Conclusion:
- the preregistered claim that BTC alignment improves XRP continuation is rejected.

### H6 — Funding Extreme Mean Reversion

- 0/4 sample minimum PASS
- 0/4 positive effect
- 0/4 economic floor PASS
- 0/4 Holm PASS

Effect range:
- -0.00268090 → -0.00006766

The least negative configuration had:
- 203 events
- only 18 LONG-side events
- 185 SHORT-side events
- 106 unique days

Conclusion:
- insufficient balanced sample plus wrong effect direction.

### H7 — SCALP Taker-Flow Continuation

- 12/12 sample PASS
- 0/12 positive effect
- 12/12 CI95 entirely below zero
- 0/12 economic floor PASS
- 0/12 quarter stability PASS
- 0/12 Holm PASS

Effect range:
- -0.00008366 → -0.00006492

Conclusion:
- taker-flow continuation is rejected consistently across the entire preregistered grid.

## Data-quality event before final rerun

The initial 2023 discovery attempt stopped before outcomes because one official monthly XRP kline had:
- taker_buy_base > total volume.

Timestamp:
- 2023-11-30 12:35 UTC

Official aggTrades reconstruction proved:
- monthly kline volume was wrong;
- corrected volume = 331,858.0;
- taker_buy_ratio = 0.3991541563;
- OHLC, quote volume, trade count and taker fields matched.

The recovery is documented in:
- `research/audits/XRP_2023_KLINE_VOLUME_RECOVERY_V1.md`

All earlier partial discovery outputs were discarded and the complete discovery run was repeated from scratch.

## Decision

**No XRP_HYPOTHESES_V1 configuration advances to validation.**

2024-2025 remains untouched.

2026 remains untouched.

The correct next research stage is:
- post-discovery hypothesis generation for `XRP_HYPOTHESES_V2`,
- explicitly labeled as derived from 2020-2023 discovery,
- followed by preregistration before any 2024-2025 outcome is opened.

V1 thresholds must not be retuned and relabeled as if they had passed.
