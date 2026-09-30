# XRP Preregistered Hypotheses V2

## Estado

**PREREGISTERED FROM DISCOVERY V1 — VALIDATION STILL SEALED**

Versión:
- `XRP_HYPOTHESES_V2`

Origen:
- generadas después de `XRP_DISCOVERY_RESULTS_V1`;
- por tanto, 2020-2023 ya no se considera evidencia confirmatoria para V2;
- 2024-2025 permanece sin abrir al momento de este preregistro.

Validation:
- 2024-01-01 00:00 UTC → 2025-12-31 23:59 UTC

Historical holdout:
- 2026-01-01 → 2026-08-31
- permanece sellado.

## Principio V2

V2 no vuelve a buscar thresholds sobre 2020-2023.

Cada hipótesis usa **una única configuración fija** derivada de un patrón V1 suficientemente claro para merecer una prueba externa.

No existe búsqueda dentro de hypothesis ID en validation.

## Regla común de validation

Para evitar tocar el holdout 2026:

`decision_time + 240m < 2026-01-01 00:00 UTC`

Por tanto, el último decision_time elegible es estrictamente anterior a:
- 2025-12-31 20:00 UTC.

Inference:
- UTC-day block bootstrap;
- 2,000 replicaciones;
- percentile CI95;
- one-sided bootstrap-normal p;
- Holm correction entre las hipótesis V2 con efecto computable.

Validation pass requiere:
1. muestra mínima;
2. efecto con signo preregistrado;
3. CI95 lower > 0;
4. Holm p < 0.05;
5. efecto >= economic floor;
6. efecto >= 50% del efecto de referencia observado en discovery V1, salvo que el economic floor sea más exigente;
7. al menos 4 trimestres informativos;
8. mediana del efecto trimestral > 0.

No se retunean parámetros después de ver validation.

---

## V2-H1 — PRIMARY Momentum Exhaustion

ID:
- `XRP-V2-H1-PRIMARY-MOMENTUM-EXHAUSTION`

Grid:
- PRIMARY_15M

Idea:
- el momentum XRP suficientemente fuerte, acompañado de volumen relativo elevado, tiende a revertir durante la siguiente hora en lugar de continuar.

Features:
- `xrp_ret_12`
- `xrp_rel_volume20`

Configuración fija:
- `abs(xrp_ret_12) >= 0.010`
- `xrp_rel_volume20 >= 1.5`

Dirección:
- si `xrp_ret_12 > 0` → SHORT conceptual;
- si `xrp_ret_12 < 0` → LONG conceptual.

Primary outcome:
- signed forward return 60m

Secondary diagnostics:
- 15m
- 240m
- MFE/MAE 60m

Discovery reference, solo para shrinkage gate:
- reversed effect = **0.0008616348922**
- reference sample = 11,688
- unique days = 1,347

Validation minimum:
- >= 1,500 total
- >= 350 por lado
- >= 180 días UTC

Economic floor:
- **0.00030**

50% discovery reference:
- **0.0004308174461**

Validation effect floor real:
- `max(0.00030, 0.0004308174461) = 0.0004308174461`

---

## V2-H2 — PRIMARY OI Momentum Moderator

ID:
- `XRP-V2-H2-PRIMARY-OI-MODERATOR`

Grid:
- PRIMARY_15M

Idea:
- para momentum XRP de magnitud suficiente, la continuación posterior difiere entre expansión y contracción de OI.

Features:
- `xrp_ret_12`
- `xrp_oi_chg_15m`

Configuración fija:
- `abs(xrp_ret_12) >= 0.005`
- grupo A expansion: `xrp_oi_chg_15m >= 0.005`
- grupo B contraction: `xrp_oi_chg_15m <= -0.005`

Dirección base:
- `sign(xrp_ret_12)`

Primary effect:
- mean signed 60m expansion
  menos
- mean signed 60m contraction

Discovery reference:
- effect = **0.0008252021387**
- expansion n = 2,810
- contraction n = 2,937
- unique days = 693
- discovery raw CI95 lower > 0, pero V1 no pasó Holm.

Validation minimum:
- >= 500 expansion
- >= 500 contraction
- >= 180 días UTC

Economic floor:
- **0.00030**

50% discovery reference:
- **0.0004126010693**

Validation effect floor real:
- **0.0004126010693**

Esta hipótesis es comparativa. Incluso si pasa, todavía no define por sí sola una entrada operativa.

---

## V2-H3 — SCALP Taker-Flow Exhaustion

ID:
- `XRP-V2-H3-SCALP-TAKER-FLOW-EXHAUSTION`

Grid:
- SCALP_1M

Idea:
- un imbalance taker fuerte con volumen elevado tiende a revertir, no a continuar, durante los siguientes 15 minutos.

Features:
- `xrp_taker_imbalance`
- `xrp_rel_volume20`

Configuración fija:
- `abs(xrp_taker_imbalance) >= 0.30`
- `xrp_rel_volume20 >= 1.5`

Dirección:
- taker imbalance positivo → SHORT conceptual
- taker imbalance negativo → LONG conceptual

Primary outcome:
- signed forward return 15m

Secondary:
- 5m
- 30m
- MFE/MAE 15m

Discovery reference, invirtiendo la dirección V1:
- effect = **0.0000776411190**
- reference sample = 201,097
- unique days = 1,430

Validation minimum:
- >= 10,000 total
- >= 2,500 por lado
- >= 300 días UTC

Economic floor:
- **0.00010**

50% discovery reference:
- **0.0000388205595**

Validation effect floor real:
- `max(0.00010, 0.0000388205595) = 0.00010`

Esto significa que V2-H3 no puede pasar únicamente por reproducir el pequeño efecto discovery; debe alcanzar al menos 1 bp promedio.

---

## Hipótesis no incluidas en V2

### Extension reversion V1
No entra porque el efecto fue débil, ningún threshold superó el economic floor y ningún CI95 fue positivo.

### BTC alignment V1
No entra pese al signo opuesto consistente porque la estabilidad trimestral fue pobre y el efecto comparative fue muy sensible al régimen.

### Funding V1
No entra por muestra insuficiente y fuerte desbalance LONG/SHORT.

### OI confirmation V1
No entra porque no mostró robustez suficiente después de multiplicidad.

## Multiplicidad V2

Solo hay 3 hipótesis.

No hay threshold search dentro de cada una.

En validation:
- calcular p one-sided por hypothesis;
- aplicar Holm entre las 3;
- ninguna se elimina de la familia por tener mal resultado.

## Quarter stability V2

Validation contiene 8 trimestres.

Directional hypotheses:
- trimestre informativo si >= 100 filas elegibles.

OI comparative:
- trimestre informativo si >= 50 observaciones en cada grupo.

Pass:
- >= 4 trimestres informativos;
- mediana del efecto trimestral > 0.

## Selección después de validation

No se elige “la mejor” si varias pasan.

Cada hypothesis se clasifica independientemente:
- VALIDATION_PASS
- VALIDATION_FAIL

Si al menos una pasa:
1. se documentan sus resultados;
2. se congela una especificación challenger;
3. recién entonces puede abrirse el historical holdout 2026.

Si ninguna pasa:
- 2026 permanece sellado;
- V2 termina sin challenger validado.

## Inmutabilidad

Una vez abierto validation:
- este archivo no se modifica;
- cualquier cambio crea `XRP_HYPOTHESES_V3`;
- no se permite bajar floors, mover thresholds ni cambiar horizonte después de ver 2024-2025.
