# Historical Feature Contract V1 — XRP Challenger

## Estado

**PRE-OUTCOME FEATURE FREEZE**

Versión:
- `FEATURES_V1`

Input obligatorio:
- `HIST_NORM_V1`

Activo objetivo:
- XRPUSDT

Contexto externo:
- BTCUSDT

Este contrato se define antes de explorar outcomes o rentabilidad. Su función es convertir la capa normalizada en variables observables en tiempo histórico sin incorporar reglas de estrategia.

## Prohibiciones

Durante construcción y QA de FEATURES_V1 no se puede leer:
- ANALYSES
- SIGNALS
- PERFORMANCE
- ALERT_FORWARD
- ALERT_MFE_MAE
- decisiones de agentes CURRENT
- forward returns
- MFE / MAE
- resultados de trades

No se seleccionan features por su rendimiento futuro en esta etapa.

## Grids de decisión

### SCALP_1M
Una fila por cada cierre XRPUSDT de 1 minuto.

`decision_time = contract_1m.available_at_ms`

### PRIMARY_15M
Una fila por cada cierre XRPUSDT de 15 minutos reconstruido.

`decision_time = contract_resampled(15m).available_at_ms`

Las filas de BTC nunca crean decisiones. BTC solo aporta contexto con información disponible en o antes del decision_time de XRP.

## Regla temporal general

Una feature solo puede usar inputs cuyo `available_at <= decision_time`.

No se usa nearest futuro.

No se rellenan gaps con observaciones futuras.

Cuando el input requerido no existe o excede su tolerancia de staleness, la feature es NA.

## Convenciones matemáticas

### Retornos
Para close actual `C_t` y close de n barras previas `C_(t-n)`:

`ret_n = C_t / C_(t-n) - 1`

Se calculan:
- ret_1
- ret_3
- ret_12

### EMA 20 / 50 / 200
EMA estándar:

`EMA_t = alpha * C_t + (1-alpha) * EMA_(t-1)`

`alpha = 2/(N+1)`

Seed:
- SMA de los primeros N closes.

No se emite EMA antes de completar N barras.

### RSI14
Wilder RSI.

Cambios:
`delta_t = C_t - C_(t-1)`

Seed:
- promedio simple de gains/losses de los primeros 14 deltas.

Actualización posterior:
- Wilder smoothing con periodo 14.

Si avg_loss=0 y avg_gain>0, RSI=100.
Si ambos son 0, RSI=50.

### ATR14
True Range:

`TR_t = max(H_t-L_t, abs(H_t-C_(t-1)), abs(L_t-C_(t-1)))`

Para la primera barra disponible se usa `H-L`.

Seed ATR:
- SMA de los primeros 14 TR.

Después:
- Wilder smoothing periodo 14.

### ATR %
`atr_pct = ATR14 / close`

### Distancia a EMA en ATR
`dist_emaN_atr = (close - EMA_N) / ATR14`

Para N:
- 20
- 50
- 200

### Relative Volume 20
El denominador usa exclusivamente las **20 barras anteriores**, excluyendo la barra actual:

`rel_volume20 = volume_t / mean(volume_(t-20:t-1))`

Si el denominador <= 0, NA.

### Relative Trades 20
Igual criterio:

`rel_trades20 = trades_t / mean(trades_(t-20:t-1))`

### Taker Buy Ratio
`taker_buy_ratio = taker_buy_base / volume`

Si volume <= 0, NA.

### Taker Imbalance
`taker_imbalance = 2 * taker_buy_ratio - 1`

Rango esperado aproximado:
- [-1, +1]

### Donchian previo 20
Se utilizan las 20 barras anteriores, excluyendo la actual:

`prev20_high = max(high_(t-20:t-1))`
`prev20_low  = min(low_(t-20:t-1))`

Features:
- `dist_prev20_high_atr = (close-prev20_high)/ATR14`
- `dist_prev20_low_atr = (close-prev20_low)/ATR14`

No se crea todavía una regla LONG/SHORT a partir de estas distancias.

### UTC Session VWAP
Se calcula desde 00:00 UTC hasta la última vela 1m cerrada incluida en la decisión.

Precio por minuto:
`typical = (high+low+close)/3`

`session_vwap = sum(typical*volume)/sum(volume)`

Se reinicia a 00:00 UTC.

Feature:
- `dist_vwap_atr = (close-session_vwap)/ATR14`

Para PRIMARY_15M, el VWAP se toma al cierre del último 1m contenido en la barra 15m.

## Features de precio por grid

Para XRP y para BTC se calcula, en el timeframe del grid:
- ret_1
- ret_3
- ret_12
- EMA20 / EMA50 / EMA200
- RSI14
- ATR14
- atr_pct
- dist_ema20_atr
- dist_ema50_atr
- dist_ema200_atr
- rel_volume20
- rel_trades20
- taker_buy_ratio
- taker_imbalance
- dist_prev20_high_atr
- dist_prev20_low_atr
- session_vwap
- dist_vwap_atr

Para BTC, las columnas se almacenan con prefijo `btc_`.

## Derivados XRP

### Funding
Fuente:
- último funding con `available_at <= decision_time`.

Staleness máximo:
- 12 horas.

Features:
- `funding_rate`
- `funding_age_min`

Si no existe un evento dentro de 12h:
- NA.

### Mark / Index / Premium
Fuente:
- último 1m auxiliar cerrado con `available_at <= decision_time`.

Staleness máximo:
- 2 minutos.

Features:
- `mark_close`
- `index_close`
- `premium_close`
- `mark_index_basis = mark_close/index_close - 1`

Si mark o index no cumple tolerancia:
- basis = NA.

### Metrics
Fuente:
- última fila con `available_at <= decision_time`.

Staleness máximo:
- 10 minutos.

Features directas:
- sum_open_interest
- sum_open_interest_value
- count_toptrader_long_short_ratio
- sum_toptrader_long_short_ratio
- count_long_short_ratio
- sum_taker_long_short_vol_ratio
- metrics_age_min

Cambios de OI:
- oi_chg_5m
- oi_chg_15m
- oi_chg_60m

Para `oi_chg_N`:
- la fila actual debe ser válida;
- debe existir exactamente una observación source_timestamp-N;
- ambas deben tener OI > 0;
- `oi_chg_N = OI_t/OI_(t-N)-1`.

No se salta sobre un gap para fabricar una variación.

## Contexto de derivados BTC

Se incluye:
- btc_funding_rate
- btc_funding_age_min
- btc_sum_open_interest
- btc_oi_chg_15m
- btc_oi_chg_60m
- btc_metrics_age_min

Mismas reglas de disponibilidad y staleness.

## Missingness

NA es un estado válido.

No se:
- interpola;
- forward-fill sin límite;
- reemplaza NA por 0;
- sustituye un input faltante por un futuro.

Los experimentos posteriores deberán reportar cobertura por feature.

## Lineage obligatorio por fila

Cada fila de features almacena:
- feature_set_version
- normalization_version
- decision_grid
- XRP bar open_time
- decision_time
- BTC bar available_at usado
- XRP metrics available_at usado
- BTC metrics available_at usado
- XRP funding available_at usado
- BTC funding available_at usado
- XRP auxiliary available_at usado

Toda lineage timestamp debe cumplir:
`lineage_available_at <= decision_time`.

## Warm-up

Warm-up mínimo por indicador:
- ret_1: 1 barra previa
- ret_3: 3
- ret_12: 12
- RSI14: 14 deltas
- ATR14: 14 TR
- EMA20: 20 barras
- EMA50: 50
- EMA200: 200
- rel_volume20: 20 barras previas
- rel_trades20: 20
- Donchian previo 20: 20
- session VWAP: desde inicio del día UTC

No se usa una EMA “parcial” antes de su seed.

## Features discretas diferidas

No forman parte de FEATURES_V1:
- sweep
- reclaim
- lose
- retest
- breakout confirmado
- pullback setup
- LONG / SHORT score

Estas requieren un contrato objetivo separado y no se definirán observando outcomes.

## QA requerido para aprobar FEATURES_V1

1. Una fila por decisión XRP, sin duplicados.
2. decision_time estrictamente creciente por grid.
3. Ningún lineage timestamp > decision_time.
4. Metrics respeta +5m de HIST_NORM_V1.
5. BTC context nunca usa una barra futura.
6. EMA200 no aparece antes de 200 barras.
7. RVOL/Donchian no aparecen antes de 20 barras previas.
8. No existen +/-inf.
9. Valores no nulos de taker_buy_ratio dentro de tolerancia [0,1].
10. No se leen outcomes.
11. El builder produce el mismo hash al repetir sobre el mismo input SQLite.

## Gate

Después de aprobar el smoke test de FEATURES_V1, el paso siguiente será:

**Baseline descriptivo sin estrategia.**

Ese baseline podrá medir distribución, cobertura, correlaciones contemporáneas y estabilidad temporal de las features, pero todavía no escoger reglas por forward outcome.
