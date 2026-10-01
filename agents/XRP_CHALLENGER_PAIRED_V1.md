# XRP CHALLENGER PAIRED V1

## Estado

**FROZEN RESEARCH CHALLENGER — PAIRED BENCHMARK ONLY**

No es un agente operativo.
No crea SIGNALS.
No ejecuta órdenes.
No modifica XRP CURRENT.

## Origen metodológico

Este Challenger se congela antes de leer resultados del benchmark emparejado.

Sus reglas provienen exclusivamente de:
- Discovery V1 2020-2023;
- Validation V2 2024-2025;
- XRP_FORWARD_V3_1 preregistrado.

No usa:
- PAIRED_OUTCOMES;
- ALERT_FORWARD;
- ALERT_MFE_MAE;
- enero-agosto 2026 holdout;
- decisiones CURRENT del benchmark.

## Input

Una sola captura congelada:
- PAIRED_CAPTURES
- sus segmentos PAIRED_SNAPSHOT_BARS con el mismo Pair ID.

El Challenger no necesita usar todos los campos disponibles.
Que CURRENT disponga de contexto adicional no autoriza al Challenger a añadir filtros no especificados aquí.

## Schema de barras

Cada `Bars JSON` contiene arrays:

`[open_time_ms, open, high, low, close, volume, close_time_ms, quote_volume, trades, taker_buy_base, taker_buy_quote]`

Las barras están cerradas y deben satisfacer:
- `close_time_ms <= Alert UTC`;
- orden temporal ascendente;
- sin duplicados.

## Estados permitidos

Exactamente uno:
- TRADE_LONG
- TRADE_SHORT
- NO_TRADE
- DATA_INSUFFICIENT

## SCALP_TRIGGER — Taker-Flow Exhaustion

Fuente:
- XRPUSDT 1m snapshot.

Requisitos:
- Snapshot Completeness = FULL;
- al menos 21 barras 1m;
- volumen actual > 0.

Cálculos:

`rel_volume20 = volume_t / mean(volume_(t-20) ... volume_(t-1))`

`taker_buy_ratio = taker_buy_base_t / volume_t`

Si taker_buy_ratio no está en [0,1]:
- DATA_INSUFFICIENT.

`taker_imbalance = 2*taker_buy_ratio - 1`

Regla fija:
- `abs(taker_imbalance) >= 0.30`
- `rel_volume20 >= 1.5`

Si no cumple:
- NO_TRADE.

Si cumple:
- taker_imbalance > 0 → TRADE_SHORT
- taker_imbalance < 0 → TRADE_LONG

Primary benchmark horizon:
- 15m, definido por el protocolo paired.

## PRIMARY_TRIGGER / PRIMARY — Momentum Exhaustion

Fuente:
- XRPUSDT 1m snapshot.

Requisitos:
- Snapshot Completeness = FULL;
- al menos 315 minutos exactos suficientes para 21 buckets 15m completos.

### Resample 15m

Bucket UTC:
`floor(open_time_ms / 900000) * 900000`

Un bucket solo es válido si contiene exactamente:
- 15 barras 1m;
- open times consecutivos bucket + k*60000 para k=0..14.

OHLCV:
- open = primer open;
- high = máximo high;
- low = mínimo low;
- close = último close;
- volume = suma volume;
- quote_volume = suma quote_volume;
- trades = suma trades;
- taker_buy_base = suma taker_buy_base;
- taker_buy_quote = suma taker_buy_quote.

Usar únicamente buckets cuyo close_time <= Alert UTC.

### Features

Sobre el último bucket completo t:

`ret_12 = close_t / close_(t-12) - 1`

`rel_volume20 = volume_t / mean(volume_(t-20) ... volume_(t-1))`

Requiere al menos 21 buckets.

Regla fija:
- `abs(ret_12) >= 0.010`
- `rel_volume20 >= 1.5`

Si no cumple:
- NO_TRADE.

Si cumple:
- ret_12 > 0 → TRADE_SHORT
- ret_12 < 0 → TRADE_LONG

Primary benchmark horizon:
- 60m.

## OI moderator

El hallazgo V2 de OI fue comparativo, no una señal de entrada independiente.

Por ello:
- puede registrarse como diagnóstico en Notes;
- NO cambia TRADE/NO_TRADE;
- NO invierte dirección;
- NO añade un filtro.

Esto evita convertir retrospectivamente una diferencia de grupos en una regla operativa que nunca fue validada.

## Detector direction

La dirección del detector CURRENT:
- define el universo de capturas;
- NO es input direccional del Challenger.

El Challenger puede:
- coincidir;
- oponerse;
- abstenerse.

## BTC / macro / 4H

El snapshot contiene contexto para paridad informacional con CURRENT.

XRP_CHALLENGER_PAIRED_V1:
- no usa BTC;
- no usa funding;
- no usa 4H/1D;
- no usa SuperTrend/Donchian;
- no introduce confirmaciones adicionales.

Añadir cualquiera de esos filtros crea una nueva versión del Challenger.

## Entry / Stop / TP

Este Challenger V1 es un motor de decisión, no un plan de ejecución.

Campos:
- Entry = blank
- Stop = blank
- TP1 = blank
- TP2 = blank
- Gross RR = blank

El benchmark principal utiliza:
- mismo reference price compartido;
- mismo primary horizon;
- mismo coste estandarizado por trade.

## Score

SCALP:
- guardar `TI=<value>|RV20=<value>`

PRIMARY:
- guardar `R12=<value>|RV20=<value>`

## Reason

Debe incluir:
- regla evaluada;
- valores exactos;
- threshold;
- resultado PASS/FAIL.

No generar narrativa adicional que pueda introducir reglas implícitas.

## DATA_INSUFFICIENT

Usar cuando:
- falta Full Snapshot SHA256;
- Snapshot Completeness != FULL;
- falta segmento XRPUSDT 1m;
- barras insuficientes;
- gap impide resample exacto;
- valor no finito;
- taker ratio imposible.

Nunca sustituir datos faltantes con nearest/interpolación.

## Inmutabilidad

Después del formal benchmark start:
- thresholds no cambian;
- horizons no cambian;
- mapping no cambia;
- no se añaden filtros;
- no se eliminan Pair IDs desfavorables.

Cualquier cambio crea XRP_CHALLENGER_PAIRED_V2 y una nueva cohorte prospectiva.
