# XRP Historical Descriptive Baseline V1 — Approved

## Estado

**PASS**

Fecha: 2026-09-30 UTC.

Baseline:
- `XRP_DESCRIPTIVE_BASELINE_V1`

Inputs:
- `HIST_NORM_V1`
- `FEATURES_V1`

Discovery period:
- 2020-02-01 00:00 UTC
- 2023-12-31 23:59 UTC

GitHub Actions run:
- `36776410982`

Final artifact:
- `11126785741`

Workflow:
- `.github/workflows/xrp-descriptive-baseline-v1.yml`

Scripts:
- `research/historical_normalizer_window_v1.py`
- `research/historical_descriptive_baseline_part_v1.py`
- `research/historical_descriptive_baseline_aggregate_v1.py`

## Experimental boundary

This baseline did **not** use:
- forward returns
- MFE / MAE
- trade outcomes
- ANALYSES
- SIGNALS
- PERFORMANCE
- CURRENT-agent decisions
- ALERT_FORWARD
- ALERT_MFE_MAE

No strategy rule, LONG/SHORT score, entry, stop or TP was tested.

## Continuous-window construction

The discovery period was partitioned by year to keep computation reproducible and bounded.

Warm-up:
- 2020 statistics begin 2020-02 after January warm-up.
- 2021 includes 2020-12 as warm-up.
- 2022 includes 2021-12 as warm-up.
- 2023 includes 2022-12 as warm-up.

Warm-up rows are excluded from the target-year statistics.

This prevents EMA/RSI/ATR and other rolling features from resetting at calendar-year boundaries.

## Decision population

| Grid | Rows |
|---|---:|
| SCALP_1M | 2,059,200 |
| PRIMARY_15M | 137,280 |

The decision universe is the objective historical grid, not CURRENT alerts.

## Coverage summary

### SCALP_1M

| Feature | Discovery coverage |
|---|---:|
| XRP EMA200 | 100.00% |
| XRP RSI14 | 100.00% |
| XRP ATR % | 100.00% |
| XRP Relative Volume 20 | ~100.00% |
| XRP Funding | 100.00% |
| XRP Open Interest | 53.22% |
| XRP OI change 15m | 53.18% |
| XRP Top-Trader Count L/S | 30.91% |
| BTC Open Interest | 85.02% |
| BTC OI change 15m | 84.93% |

PRIMARY_15M has essentially the same availability profile.

## Coverage by year

### XRP Open Interest

| Year | Coverage |
|---|---:|
| 2020 | 0.00% |
| 2021 | 8.49% |
| 2022 | 100.00% |
| 2023 | 100.00% |

This matches the audited XRP metrics archive start in December 2021.

### XRP OI change 15m

| Year | Coverage |
|---|---:|
| 2020 | 0.00% |
| 2021 | 8.48% |
| 2022 | 99.88% |
| 2023 | 99.97% |

### XRP Top-Trader Count Long/Short Ratio

| Year | Coverage |
|---|---:|
| 2020 | 0.00% |
| 2021 | 8.11% |
| 2022 | 13.01% |
| 2023 | 99.98% |

This feature therefore cannot be treated as a uniform full-discovery feature.

### BTC Open Interest

| Year | Coverage |
|---|---:|
| 2020 | 36.39% |
| 2021 | 99.70% |
| 2022 | 100.00% |
| 2023 | 100.00% |

This matches the audited BTC metrics start in September 2020.

## Descriptive scale examples

### SCALP_1M

- XRP RSI14 mean: 50.2357
- XRP RSI14 SD: 10.7906
- XRP ATR % mean: 0.00178701
- XRP funding mean: 0.000178753
- XRP funding observed range: -0.005025 to 0.00412417
- XRP OI change 15m mean: 0.0000151272
- XRP OI change 15m observed range: -0.164495 to 0.407213

### PRIMARY_15M

- XRP RSI14 mean: 50.1533
- XRP RSI14 SD: 10.7307
- XRP ATR % mean: 0.00738279
- XRP funding mean: 0.000178793

These values are descriptive only; none is interpreted as predictive.

## Contemporaneous redundancy

Strongest observed relationships among the core feature subset:

### SCALP_1M

- XRP RSI14 vs XRP distance-to-EMA50/ATR: `r = 0.9494`
- XRP RSI14 vs BTC RSI14: `r = 0.6702`
- XRP ATR% vs BTC ATR%: `r = 0.6612`
- XRP ret_12 vs BTC ret_12: `r = 0.6246`
- XRP ret_1 vs BTC ret_1: `r = 0.6007`
- XRP OI change 15m vs XRP OI change 60m: `r = 0.5661`

### PRIMARY_15M

- XRP RSI14 vs XRP distance-to-EMA50/ATR: `r = 0.9457`
- XRP distance-to-EMA50/ATR vs distance-to-VWAP/ATR: `r = 0.8344`
- XRP RSI14 vs distance-to-VWAP/ATR: `r = 0.8258`
- XRP RSI14 vs BTC RSI14: `r = 0.7034`
- XRP ATR% vs BTC ATR%: `r = 0.6475`
- XRP ret_1 vs BTC ret_1: `r = 0.6208`

## Methodological implications

1. Features with materially incomplete history must not be required by hypotheses intended to cover the full 2020-2023 discovery period.
2. OI-based hypotheses must declare a later eligible start date.
3. Top-trader-ratio hypotheses require a still narrower valid-history subset because coverage is sparse before 2023.
4. Highly correlated features must not be interpreted as independent confirmations merely because they have different names.
5. BTC context is empirically contemporaneously related to XRP, but this baseline makes no claim that BTC variables predict XRP outcomes.
6. Missingness itself is not converted into a trading signal in V1.

## Decision

**Descriptive baseline gate approved.**

The next permitted stage under `HISTORICAL_RESEARCH_PROTOCOL_V1` is:

**preregistered hypotheses.**

Before any forward outcome is opened, each hypothesis must define:
- hypothesis ID;
- grid;
- eligible historical period;
- exact feature subset;
- exact direction/relationship being tested;
- thresholds or threshold-search space fixed in advance;
- minimum sample requirement;
- evaluation metrics;
- multiple-testing family;
- pass/fail criteria;
- discovery vs validation handling.

No hypothesis may be created by first inspecting which threshold produced the best future return.
