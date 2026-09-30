# XRP 2023 Kline Volume Recovery — Audit Record

## Estado

**VERIFIED OFFICIAL-SOURCE RECOVERY**

Fecha: 2026-09-30 UTC.

Timestamp afectado:
- `2023-11-30T12:35:00Z`
- open_time_ms: `1701347700000`

## Problema en el monthly 1m kline

Archivo oficial:
- `XRPUSDT-1m-2023-11.zip`

Fila publicada:
- open: 0.6038
- high: 0.6038
- low: 0.6034
- close: 0.6036
- volume: **91,695.7**
- quote_volume: 200,298.79368
- trades: 470
- taker_buy_base: 132,462.5
- taker_buy_quote: 79,957.28937

La fila es internamente imposible porque:
- `taker_buy_base > volume`
- ratio publicado implícito = **1.4445879142**

El ZIP mensual pasa su checksum oficial, por lo que no es corrupción local.

## Reconstrucción independiente con aggTrades oficial

Fuente:
- `XRPUSDT-aggTrades-2023-11-30.zip`

SHA-256:
- `e5fd4262256cd854b5272b257838d32e5030c886706cb5e38400688d5e53b751`

Run de auditoría:
- `36782037285`

Artifact:
- `11128416200`

Para el minuto exacto se reconstruyeron:
- aggTrade rows: 97
- individual trades: 470
- open: 0.6038
- high: 0.6038
- low: 0.6034
- close: 0.6036
- **volume: 331,858.0**
- quote_volume: 200,298.79368000012
- taker_buy_base: 132,462.5
- taker_buy_quote: 79,957.28937
- taker_buy_ratio: **0.3991541563**

## Comparación

Coinciden entre kline y aggTrades:
- OHLC
- quote volume
- trade count
- taker-buy base
- taker-buy quote

No coincide:
- total base volume

Por lo tanto, el único campo identificado como corrupto es `volume`.

## Regla de normalización

En `HIST_NORM_V1`, exclusivamente para:
- XRPUSDT
- 2023-11-30 12:35 UTC

el normalizador:
1. descarga el aggTrades daily oficial;
2. verifica `.CHECKSUM`;
3. reconstruye el minuto;
4. exige coincidencia de OHLC, quote volume, trades y taker-buy;
5. sustituye únicamente `volume` por el volumen reconstruido;
6. registra `AGGTRADES_VOLUME_RECOVERY` en `normalization_events`;
7. conserva el archivo y SHA de aggTrades en `source_files`.

Si cualquiera de los controles falla:
- la normalización falla;
- no se usa una corrección hard-coded silenciosa.

## Razón metodológica

Esta recuperación se definió por una inconsistencia matemática del dato fuente detectada por QA:
- ocurrió antes de completar discovery;
- no se inspeccionó rendimiento de ninguna hipótesis para decidir la corrección;
- no modifica thresholds, direcciones ni criterios estadísticos.

Los resultados parciales de discovery generados antes de esta corrección se consideran descartados y el discovery debe reejecutarse completamente.
