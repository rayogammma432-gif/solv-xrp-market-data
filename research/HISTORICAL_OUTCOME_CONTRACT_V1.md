# Historical Outcome Contract V1 — XRP

## Estado

**PRE-DISCOVERY OUTCOME ENGINE CONTRACT**

Versión:
- `OUTCOMES_V1`

Inputs permitidos:
- `HIST_NORM_V1`
- decision rows de `FEATURES_V1`

No consume:
- ANALYSES
- SIGNALS
- PERFORMANCE
- agentes CURRENT
- ALERT_FORWARD
- ALERT_MFE_MAE

## Propósito

Calcular outcomes históricos reproducibles para las mismas filas de decisión creadas por FEATURES_V1, sin modificar features ni definir reglas LONG/SHORT.

OUTCOMES_V1 contiene resultados futuros crudos. La dirección conceptual se aplica después, en el evaluador de hipótesis preregistradas.

## Precio de referencia

Para cada decision row:

`reference_price = xrp_close`

Debe coincidir exactamente, dentro de tolerancia numérica, con el close de la vela XRPUSDT 1m cuya:

`available_at_ms == decision_time_ms`

Para PRIMARY_15M, esa vela 1m es el último minuto del bloque 15m.

Si no coincide:
- error de integridad;
- no producir outcome para esa ejecución.

## Forward returns

Horizontes:
- 5m
- 15m
- 30m
- 60m
- 240m

Para horizonte `h`:

`target_available_at = decision_time + h*60_000`

Se exige una vela XRPUSDT 1m con:

`available_at_ms == target_available_at`

Entonces:

`forward_return_h = future_close / reference_price - 1`

Si el timestamp exacto no existe:
- outcome = NA;
- no usar nearest;
- no usar el minuto siguiente;
- no interpolar.

## Excursiones crudas

Horizontes:
- 15m
- 60m
- 240m

Ventana exacta:

`decision_time < bar.available_at <= decision_time + h`

Deben existir exactamente `h` velas consecutivas de 1 minuto.

Si falta una:
- ambas excursiones del horizonte = NA.

### Up excursion

`raw_up_excursion_h = max(high_future_window) / reference_price - 1`

### Down excursion

`raw_down_excursion_h = min(low_future_window) / reference_price - 1`

Normalmente:
- raw_up_excursion >= 0, salvo gaps extremos de mercado;
- raw_down_excursion <= 0, salvo gaps extremos.

El motor no asigna dirección.

## Transformación direccional posterior

Para una hypothesis con `d=+1` LONG:

- signed forward = `forward_return`
- MFE = `raw_up_excursion`
- MAE magnitude = `-raw_down_excursion`

Para `d=-1` SHORT:

- signed forward = `-forward_return`
- MFE = `-raw_down_excursion`
- MAE magnitude = `raw_up_excursion`

Esta transformación pertenece al evaluador de hipótesis, no al outcome engine.

## Regla temporal

Toda fuente utilizada por un outcome debe satisfacer:

`source_available_at > decision_time`

El precio de referencia es la única excepción y debe tener:

`source_available_at == decision_time`

No se permite que una future bar alimente FEATURES_V1.

## Completitud

Cada output row registra:
- outcome_engine_version
- decision_grid
- xrp_bar_open_time_ms
- decision_time_ms
- reference_price
- forward target timestamp por horizonte
- forward_return por horizonte
- raw_up_excursion por horizonte
- raw_down_excursion por horizonte
- completeness flag por horizonte

No se generan fills, stops, TPs ni costes en OUTCOMES_V1.

## Smoke-test boundary

Antes de abrir discovery, el smoke test se ejecuta en:
- 2020-01-06 08:21 UTC → 2020-02-01 00:00 UTC

Este periodo está en warm-up/calidad y fuera del discovery preregistrado que comienza 2020-02-01.

Se normaliza febrero 2020 adicionalmente como future buffer para completar outcomes de hasta 240m cerca del límite de enero.

Los valores de outcome del smoke test no se usan para seleccionar hipótesis ni thresholds.

## QA obligatorio

1. Reference close coincide con contract 1m exacto en decision_time.
2. Forward targets usan timestamp exacto.
3. Ningún target forward <= decision_time.
4. Excursion windows excluyen la decision bar.
5. Excursion window tiene exactamente h barras o produce NA.
6. Ningún nearest/interpolation fallback.
7. FEATURES_V1 input mantiene el mismo SHA antes/después.
8. Dos ejecuciones OUTCOMES_V1 sobre el mismo input son byte-a-byte idénticas.
9. No hay filas duplicadas por grid + decision_time.
10. No hay +/-inf.
11. Self-test sintético confirma que un target faltante produce NA y no toma un vecino.
12. Discovery, validation y holdout permanecen sin evaluar durante este gate.

## Gate

Después de aprobar OUTCOMES_V1 smoke:

**se puede abrir exclusivamente discovery** bajo `XRP_HYPOTHESES_V1`.

Validation y 2026 holdout permanecen sellados.
