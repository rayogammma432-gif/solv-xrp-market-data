# XRP + BTC Normalization Smoke Test V1 — Approved

## Estado

**PASS**

Fecha: 2026-09-30 UTC.

Run de GitHub Actions:
- `36767611054`

Normalización:
- `HIST_NORM_V1`

Mes controlado:
- `2023-01`

Normalizador:
- `research/historical_normalizer_v1.py`

Workflow:
- `.github/workflows/xrp-btc-normalization-smoke-v1.yml`

## Propósito

Validar que los archivos oficiales auditados pueden convertirse en una capa normalizada reproducible, con procedencia por fila, resampling determinista y disponibilidad temporal anti-look-ahead antes de construir features.

No se leyeron outcomes, ANALYSES, SIGNALS, decisiones CURRENT, ALERT_FORWARD ni ALERT_MFE_MAE.

## Conteos

| Symbol | Contract 1m | Funding | Metrics | Mark 1m | Index 1m | Premium 1m | 5m | 15m | 1h | 4h | 1d |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| XRPUSDT | 44,640 | 93 | 8,928 | 44,640 | 44,640 | 44,640 | 8,928 | 2,976 | 744 | 186 | 31 |
| BTCUSDT | 44,640 | 93 | 8,928 | 44,640 | 44,640 | 44,640 | 8,928 | 2,976 | 744 | 186 | 31 |

Los conteos de timeframes reconstruidos coinciden exactamente con un enero completo de 31 días.

## Metrics

### XRPUSDT
- raw: 8,928
- normalized: 8,928
- identical duplicates removed: 0
- conflicting duplicates excluded: 0

### BTCUSDT
- raw: 8,928
- normalized: 8,928
- identical duplicates removed: 0
- conflicting duplicates excluded: 0

## Invariantes anti-look-ahead

Todos PASS:

- `contract_available_after_close`
- `resampled_available_after_close`
- `metrics_plus_5m`
- `funding_not_future_shifted`
- `metrics_unique`
- `contract_unique`

Reglas relevantes:
- contract 1m: disponible solo después del cierre;
- higher TF: disponible solo después del cierre completo;
- metrics: `available_at = create_time + 5m`;
- funding: `available_at = calc_time`;
- no nearest-future joins;
- no interpolación de gaps.

## Artefacto de validación

El run produjo una SQLite normalizada temporal.

SHA-256 de la SQLite:
`e24467253838fc3a52ba8c11b6cc9c5202a2dfde57a3d2bacfc127f463b8192c`

Artifact ID:
`11122345983`

El artifact no es la ubicación permanente del dataset histórico. Sirve para demostrar que el esquema y normalización V1 se materializan correctamente.

## Schema

Tablas V1:
- `source_files`
- `contract_1m`
- `contract_resampled`
- `aux_kline_1m`
- `funding`
- `metrics`
- `normalization_events`

Procedencia mínima conservada:
- source file
- source SHA-256
- source timestamp
- available_at
- source granularity
- recovery flag
- duplicate flag
- missing-field flag
- source-zero flag
- normalization version

## Decisión

**Gate de normalización aprobado.**

El siguiente paso permitido es construir **Feature Engineering V1** sobre `HIST_NORM_V1`.

Todavía no está permitido optimizar una estrategia. Primero deben definirse fórmulas deterministas de features, timestamps de disponibilidad, warm-up y QA de features.
