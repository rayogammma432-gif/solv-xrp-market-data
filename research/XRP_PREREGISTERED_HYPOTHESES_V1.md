# XRP Preregistered Hypotheses V1

## Estado

**PREREGISTERED — OUTCOMES STILL SEALED**

Versión:
- `XRP_HYPOTHESES_V1`

Inputs congelados:
- `HIST_NORM_V1`
- `FEATURES_V1`
- `XRP_DESCRIPTIVE_BASELINE_V1`

Discovery general:
- 2020-02-01 00:00 UTC → 2023-12-31 23:59 UTC

Validation bloqueada:
- 2024-01-01 00:00 UTC → 2025-12-31 23:59 UTC

Historical holdout bloqueado:
- 2026-01-01 00:00 UTC → 2026-08-31 23:59 UTC

En el momento de crear este documento **no se han abierto forward returns, MFE, MAE ni resultados de trades para seleccionar estas hipótesis**.

## Reglas estadísticas comunes

### Directional outcome

Para una observación con dirección conceptual `d ∈ {+1,-1}`:

`signed_forward_return_h = d * (close_(t+h) / close_t - 1)`

Esto es un outcome descriptivo de dirección, no un fill negociable.

### Comparative hypotheses

Cuando una hipótesis compara dos grupos, el efecto primario es:

`delta = mean(signed_return_group_A) - mean(signed_return_group_B)`

### Inferencia

- intervalos de confianza mediante block bootstrap por **día UTC**;
- mínimo 2,000 replicaciones;
- no tratar filas adyacentes como observaciones independientes;
- reportar número bruto de filas y número de días únicos;
- intervalos bilaterales salvo que la dirección esté preregistrada; para las hipótesis direccionales aquí registradas se reportará además el CI unilateral coherente con la dirección.

### Multiplicidad

Discovery:
- cada hypothesis ID constituye una familia;
- todas las combinaciones de thresholds declaradas dentro de ese ID se consideran pruebas de la misma familia;
- ajustar p-values dentro de la familia con Holm;
- seleccionar como máximo **una** configuración por hypothesis ID.

Validation:
- probar exactamente la configuración seleccionada en discovery;
- no volver a buscar thresholds;
- aplicar Holm entre los hypothesis IDs que lleguen a validation.

### Criterio general para avanzar de discovery a validation

Una configuración puede avanzar solo si:

1. cumple la muestra mínima;
2. efecto primario tiene el signo preregistrado;
3. lower bound del CI95% block-bootstrap del efecto primario > 0 después del control de multiplicidad;
4. supera el piso económico preregistrado;
5. no depende de un único trimestre calendario;
6. no utiliza filas con features requeridas = NA.

El mejor threshold dentro de una familia se elige por mayor efecto primario **entre configuraciones que pasan los seis criterios**. Si ninguna pasa, la hipótesis se marca `DISCOVERY_FAIL`.

### Validation pass

Una hipótesis pasa validation solo si:

1. misma dirección del efecto;
2. muestra mínima de validation;
3. lower bound CI95% > 0 tras Holm entre hypotheses validadas;
4. efecto medio >= 50% del efecto observado en discovery;
5. mantiene el piso económico absoluto;
6. no se cambia ningún threshold.

Si falla, no se “arregla” con un nuevo threshold bajo V1.

## H1 — PRIMARY Momentum Continuation

ID:
- `XRP-H1-PRIMARY-MOMENTUM`

Grid:
- PRIMARY_15M

Periodo discovery elegible:
- 2020-02-01 → 2023-12-31

Idea:
- un movimiento direccional de 3 horas ya desarrollado en XRP, acompañado por actividad suficiente, tiende a continuar en la misma dirección durante la siguiente hora.

Features exactas:
- `xrp_ret_12`
- `xrp_rel_volume20`

Dirección:
- LONG conceptual si `ret_12 > threshold_ret`
- SHORT conceptual si `ret_12 < -threshold_ret`

Filtros:
- `rel_volume20 >= threshold_rvol`

Threshold grid:
- `threshold_ret ∈ {0.005, 0.010, 0.015}`
- `threshold_rvol ∈ {1.0, 1.5, 2.0}`

Combinaciones:
- 9

Primary outcome:
- signed forward return 60m

Secondary diagnostics:
- 15m, 240m
- MFE/MAE 60m

Minimum sample:
- 2,000 rows total
- >= 500 LONG y >= 500 SHORT
- >= 120 días UTC distintos

Economic floor:
- mean signed 60m >= **0.00030** (3 bps)

No usar:
- RSI como confirmación adicional;
- dist_ema50_atr como confirmación adicional.

Motivo:
- el baseline mostró alta redundancia RSI ↔ dist_ema50_atr.

## H2 — PRIMARY Extension Mean Reversion

ID:
- `XRP-H2-PRIMARY-EXTENSION-REVERSION`

Grid:
- PRIMARY_15M

Periodo discovery:
- 2020-02-01 → 2023-12-31

Idea:
- una extensión grande respecto de VWAP en unidades ATR tiende a revertir parcialmente en la siguiente hora.

Feature exacta:
- `xrp_dist_vwap_atr`

Dirección:
- si `dist_vwap_atr >= threshold`, dirección conceptual SHORT;
- si `dist_vwap_atr <= -threshold`, dirección conceptual LONG.

Threshold grid:
- `threshold ∈ {1.0, 1.5, 2.0, 2.5}`

Combinaciones:
- 4

Primary outcome:
- signed forward return 60m

Secondary:
- 15m, 240m
- MFE/MAE 60m

Minimum sample:
- 2,000 total
- >= 500 por lado
- >= 120 días

Economic floor:
- mean signed 60m >= **0.00030**

No combinar en V1 con RSI o distancia EMA50 por redundancia contemporánea elevada.

## H3 — PRIMARY OI-Confirmed Momentum

ID:
- `XRP-H3-PRIMARY-OI-CONFIRMATION`

Grid:
- PRIMARY_15M

Periodo discovery elegible:
- **2022-01-01 → 2023-12-31**

Reason:
- XRP metrics/OI no tiene cobertura histórica suficiente antes de diciembre de 2021.

Idea:
- un movimiento direccional acompañado por expansión de OI tiende a continuar mejor que un movimiento equivalente sin expansión suficiente de OI.

Features:
- `xrp_ret_12`
- `xrp_oi_chg_15m`

Dirección:
- LONG si ret_12 positivo;
- SHORT si ret_12 negativo.

Threshold grid:
- `abs(ret_12) >= {0.005, 0.010, 0.015}`
- `oi_chg_15m >= {0.0000, 0.0025, 0.0050}`

Combinaciones:
- 9

Primary outcome:
- signed forward return 60m

Secondary:
- 240m
- MFE/MAE 60m

Minimum sample:
- 1,000 total
- >= 250 por lado
- >= 90 días

Economic floor:
- mean signed 60m >= **0.00030**

## H4 — PRIMARY OI as Momentum Moderator

ID:
- `XRP-H4-PRIMARY-OI-MODERATOR`

Grid:
- PRIMARY_15M

Periodo:
- 2022-01-01 → 2023-12-31

Idea:
- para el mismo nivel de momentum XRP, la continuación posterior es mayor cuando OI está expandiéndose que cuando OI está contrayéndose.

Features:
- `xrp_ret_12`
- `xrp_oi_chg_15m`

Momentum eligibility:
- `abs(ret_12) >= threshold_ret`

Threshold grid:
- `threshold_ret ∈ {0.005, 0.010, 0.015}`
- expansión: `oi_chg_15m >= threshold_oi`
- contracción: `oi_chg_15m <= -threshold_oi`
- `threshold_oi ∈ {0.0025, 0.0050, 0.0100}`

Combinaciones:
- 9

Primary comparison:
- mean signed 60m de grupo OI-expansion
  menos
- mean signed 60m de grupo OI-contraction

Minimum sample:
- >= 750 filas por grupo
- >= 90 días con observaciones elegibles

Economic floor:
- delta >= **0.00030** (3 bps)

Esta hipótesis es comparativa; no crea directamente una señal operativa.

## H5 — PRIMARY BTC Alignment Moderator

ID:
- `XRP-H5-PRIMARY-BTC-ALIGNMENT`

Grid:
- PRIMARY_15M

Periodo:
- 2020-02-01 → 2023-12-31

Idea:
- el momentum XRP continúa mejor cuando BTC muestra momentum contemporáneo en la misma dirección que cuando BTC está materialmente en dirección opuesta.

Features:
- `xrp_ret_12`
- `btc_ret_12`

Eligibility:
- `abs(xrp_ret_12) >= threshold_xrp`

Aligned:
- mismo signo XRP/BTC
- `abs(btc_ret_12) >= threshold_btc`

Opposed:
- signo opuesto
- `abs(btc_ret_12) >= threshold_btc`

Threshold grid:
- `threshold_xrp ∈ {0.005, 0.010, 0.015}`
- `threshold_btc ∈ {0.001, 0.0025, 0.005}`

Combinaciones:
- 9

Primary comparison:
- aligned signed forward 60m
  menos
- opposed signed forward 60m

Minimum sample:
- >= 1,000 aligned
- >= 1,000 opposed
- >= 120 días

Economic floor:
- delta >= **0.00030**

No se interpreta correlación contemporánea como causalidad; esta hypothesis prueba solo moderación prospectiva.

## H6 — Funding Extreme Mean Reversion

ID:
- `XRP-H6-FUNDING-EXTREME-REVERSION`

Grid:
- PRIMARY_15M, pero **solo una observación por evento de funding**.

Periodo:
- 2020-02-01 → 2023-12-31

Event sampling:
- usar la primera fila PRIMARY_15M con `decision_time >= funding_available_at` después de cada nuevo funding event;
- un funding event no puede aparecer más de una vez.

Idea:
- funding positivo extremo se asocia con posterior presión bajista;
- funding negativo extremo se asocia con posterior presión alcista.

Feature:
- `xrp_funding_rate`

Dirección:
- funding >= threshold → SHORT conceptual
- funding <= -threshold → LONG conceptual

Threshold grid:
- `threshold ∈ {0.0003, 0.0005, 0.0010, 0.0020}`

Combinaciones:
- 4

Primary outcome:
- signed forward return 240m

Secondary:
- 60m

Minimum sample:
- 250 eventos total
- >= 75 por lado
- >= 120 días

Economic floor:
- mean signed 240m >= **0.00050** (5 bps)

## H7 — SCALP Taker-Flow Continuation

ID:
- `XRP-H7-SCALP-TAKER-FLOW`

Grid:
- SCALP_1M

Periodo:
- 2020-02-01 → 2023-12-31

Idea:
- desequilibrio taker fuerte acompañado por volumen relativo alto tiende a continuar durante los siguientes 15 minutos.

Features:
- `xrp_taker_imbalance`
- `xrp_rel_volume20`

Dirección:
- LONG si taker_imbalance >= threshold_taker
- SHORT si taker_imbalance <= -threshold_taker

Filter:
- rel_volume20 >= threshold_rvol

Threshold grid:
- `threshold_taker ∈ {0.10, 0.20, 0.30, 0.40}`
- `threshold_rvol ∈ {1.0, 1.5, 2.0}`

Combinaciones:
- 12

Primary outcome:
- signed forward return 15m

Secondary:
- 5m, 30m
- MFE/MAE 15m

Minimum sample:
- 10,000 total
- >= 2,500 por lado
- >= 240 días

Economic floor:
- mean signed 15m >= **0.00010** (1 bp)

## Features deliberadamente excluidas de esta preregistration

### Top-trader ratios
No se usan en V1 porque:
- cobertura global es baja;
- 2022 tiene cobertura particularmente irregular;
- utilizarlos ahora produciría un universo temporal distinto y pequeño.

Podrán formar una familia posterior, preregistrada por separado, sin alterar XRP_HYPOTHESES_V1.

### Breakout/retest/sweep/reclaim
No se usan todavía porque requieren un detector de eventos objetivo versionado que aún no ha sido definido.

### RSI + distance-to-EMA50 como doble confirmación
No se permite en V1 debido a la correlación contemporánea ~0.95 observada en baseline.

## Orden de ejecución

1. Sellar este registro.
2. Construir outcome engine reproducible.
3. Verificar anti-look-ahead del outcome engine.
4. Abrir únicamente discovery.
5. Ejecutar todas las configuraciones declaradas, incluidas las que fallen.
6. Guardar resultados completos.
7. Seleccionar máximo una configuración por hypothesis ID.
8. Congelar selección.
9. Abrir validation.
10. No abrir 2026 holdout hasta freeze posterior.

## Regla de inmutabilidad

Después de abrir outcomes de discovery:
- este archivo no se modifica;
- cualquier nueva hipótesis o cambio de thresholds crea `XRP_HYPOTHESES_V2`;
- un resultado negativo permanece registrado.
