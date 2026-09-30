# XRP Historical Descriptive Baseline Contract V1

## Estado

**PRE-OUTCOME BASELINE FREEZE**

Input:
- HIST_NORM_V1
- FEATURES_V1

Periodo de warm-up:
- 2020-01-06 → 2020-01-31

Periodo descriptivo:
- 2020-02-01 → 2023-12-31

Objetivo:
describir la distribución, disponibilidad y estabilidad temporal de FEATURES_V1 antes de formular hipótesis predictivas.

## Prohibiciones

Este baseline no puede leer ni calcular:
- forward returns;
- MFE;
- MAE;
- trade outcomes;
- ANALYSES;
- SIGNALS;
- PERFORMANCE;
- ALERT_FORWARD;
- ALERT_MFE_MAE;
- decisiones CURRENT;
- win rate;
- expectancy;
- profit factor.

No se pueden elegir thresholds LONG/SHORT a partir de este baseline.

## Estadísticas obligatorias

Por grid SCALP_1M y PRIMARY_15M:

### Cobertura
Para cada feature:
- total rows;
- non-null rows;
- missing rows;
- coverage %.

### Distribución
Para cada feature numérica:
- mean;
- standard deviation;
- min;
- max;
- p01;
- p05;
- p25;
- p50;
- p75;
- p95;
- p99.

Mean/std/min/max son exactos.
Percentiles pueden usar muestra sistemática determinista documentada para limitar memoria.

### Estabilidad anual
Para cada año 2020, 2021, 2022, 2023 y cada grid:
- rows;
- coverage;
- mean;
- standard deviation

para un conjunto de features núcleo preregistrado:
- xrp_ret_1
- xrp_atr_pct
- xrp_rsi14
- xrp_rel_volume20
- xrp_taker_imbalance
- xrp_funding_rate
- xrp_sum_open_interest
- xrp_oi_chg_15m
- btc_ret_1
- btc_atr_pct
- btc_oi_chg_15m

### Correlaciones contemporáneas
Pearson pairwise-complete, sin lags futuros, entre:
- xrp_ret_1
- btc_ret_1
- xrp_atr_pct
- btc_atr_pct
- xrp_taker_imbalance
- xrp_rel_volume20
- xrp_funding_rate
- xrp_oi_chg_15m
- btc_oi_chg_15m

Estas correlaciones describen co-movimiento contemporáneo. No son evidencia predictiva.

## Cohortes de cobertura

### Price/flow cohort
2020-02-01 → 2023-12-31.

### BTC metrics cohort
Disponible solo desde 2020-09-01.

### XRP metrics cohort
Disponible solo desde 2021-12-01.

Las filas anteriores a cobertura real permanecen NA y cuentan como missing; no se rellenan.

## Missingness

NA se conserva como NA.

No:
- interpolar;
- sustituir por cero;
- usar futura observación;
- descartar silenciosamente periodos con missingness.

El baseline debe mostrar explícitamente el cambio de cobertura cuando comienzan metrics.

## Percentiles

Para mantener el proceso reproducible:
- PRIMARY_15M: usar todas las observaciones no nulas.
- SCALP_1M: usar una muestra sistemática determinista de una fila de cada 10 dentro de cada grid después del filtro temporal.

No se usa random sampling.

## Gate

El baseline V1 queda aprobado si:
1. procesa todo el discovery sin leer outcomes;
2. no contiene features futuras;
3. reproduce conteos esperados de los grids;
4. reporta cobertura completa;
5. no contiene +/-inf;
6. genera el mismo resumen byte-a-byte en dos ejecuciones sobre el mismo FEATURES_V1.

Después de aprobar el baseline, el siguiente paso permitido es:
**preregistro de hipótesis**, todavía sin abrir el historical holdout.
