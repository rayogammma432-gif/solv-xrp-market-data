# XRP Forward Research Protocol V3

## Estado

**FROZEN BEFORE FORWARD START**

Versión:
- `XRP_FORWARD_V3`

Forward start:
- `2026-10-01T00:00:00Z`

Historical 2026 holdout:
- LOCKED / not readable

## Objetivo

Evaluar prospectivamente tres relaciones que sobrevivieron parcialmente el proceso histórico sin convertirlas prematuramente en una estrategia.

Este protocolo es:
- shadow research;
- no SIGNALS;
- no orders;
- no trades;
- no TP/SL operationalization;
- no modification of CURRENT XRP agent.

## Candidate FWD-V3-A — SCALP Taker-Flow Exhaustion

Origen:
- V2-H3.

Grid:
- SCALP_1M

Features:
- xrp_taker_imbalance
- xrp_rel_volume20

Regla fija:
- abs(taker_imbalance) >= 0.30
- rel_volume20 >= 1.5

Dirección conceptual:
- imbalance > 0 → SHORT
- imbalance < 0 → LONG

Primary horizon:
- 15m

Secondary:
- 5m
- 30m
- MFE/MAE 15m

Razón:
- fue estadísticamente significativo y estable en validation, pero su efecto medio (~0.666 bp) quedó debajo del piso económico de 1 bp.

Forward gate:
- mínimo 90 días calendario;
- >= 12,000 eventos;
- >= 3,000 por lado;
- >= 75 días con eventos;
- mean signed 15m >= 0.00010;
- UTC-day block-bootstrap CI95 lower > 0;
- mediana mensual > 0;
- no se cambia threshold durante la ventana.

Resultado posible:
- FORWARD_PASS_RESEARCH
- FORWARD_FAIL

Un PASS no autoriza trading automático; solo permite pasar a diseño de ejecución/costes.

## Candidate FWD-V3-B — PRIMARY OI Momentum Moderator

Origen:
- V2-H2.

Grid:
- PRIMARY_15M

Features:
- xrp_ret_12
- xrp_oi_chg_15m

Regla fija:
- abs(ret_12) >= 0.005
- expansion: oi_chg_15m >= 0.005
- contraction: oi_chg_15m <= -0.005

Dirección base:
- sign(ret_12)

Primary effect:
- mean signed 60m expansion minus contraction.

Razón:
- reprodujo signo, magnitud económica y estabilidad en validation, pero CI por bloques diarios cruzó cero.

Forward gate:
- mínimo 180 días calendario;
- >= 600 expansion;
- >= 600 contraction;
- >= 150 días elegibles;
- effect >= 0.00040;
- UTC-day block-bootstrap CI95 lower > 0;
- mediana trimestral > 0.

Resultado:
- contexto/moderador validado prospectivamente;
- no se interpreta automáticamente como señal de entrada.

## Candidate FWD-V3-C — PRIMARY Momentum Exhaustion

Origen:
- V2-H1.

Grid:
- PRIMARY_15M

Features:
- xrp_ret_12
- xrp_rel_volume20

Regla fija:
- abs(ret_12) >= 0.010
- rel_volume20 >= 1.5

Dirección:
- ret_12 > 0 → SHORT
- ret_12 < 0 → LONG

Primary horizon:
- 60m

Secondary:
- 15m
- 240m
- MFE/MAE 60m

Forward gate:
- mínimo 180 días calendario;
- >= 1,200 eventos;
- >= 250 por lado;
- >= 150 días elegibles;
- mean signed 60m >= 0.00043;
- UTC-day block-bootstrap CI95 lower > 0;
- mediana trimestral > 0.

## Registro por evento

Cada candidate event debe conservar:
- candidate_id
- protocol_version
- decision_grid
- decision_time
- XRP bar open_time
- direction conceptual
- reference_price
- feature values exactos usados
- feature available_at lineage
- rule matched
- source normalization/feature version

Outcome se añade solo después del horizonte:
- forward return
- raw up/down excursion
- completeness
- outcome timestamp

No se reescribe el feature snapshot después de conocer outcome.

## Inmutabilidad

Desde 2026-10-01:
- no se cambian thresholds;
- no se cambian horizons;
- no se cambian floors;
- no se eliminan eventos malos;
- no se añade un filtro porque mejore resultados.

Cualquier cambio crea `XRP_FORWARD_V4` y empieza una nueva ventana desde cero.

## Separación CURRENT vs V3

CURRENT XRP agent:
- continúa operativo bajo sus reglas propias.

XRP_FORWARD_V3:
- observa de forma independiente;
- no usa decisión CURRENT como input;
- no altera señales CURRENT;
- puede compararse con CURRENT solo después de cerrar una ventana forward preregistrada.

## Gate siguiente

No hay un nuevo gate histórico inmediato.

El siguiente resultado científico válido aparece únicamente cuando se acumule la muestra forward mínima.

Hasta entonces:
- 2026 historical holdout permanece LOCKED;
- no existe challenger validado.
