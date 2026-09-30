# XRP + BTC Derivatives Data Audit V1 — Final

## Estado

**PASS_WITH_NORMALIZATION_CONSTRAINTS**

Fecha: 2026-09-30 UTC.

Este documento cierra la auditoría de disponibilidad/calidad de la segunda capa histórica para XRPUSDT y BTCUSDT antes de feature engineering.

No se ha optimizado ninguna estrategia.

## Fuentes oficiales

Binance Public Data — USD-M Futures:
- fundingRate
- markPriceKlines
- indexPriceKlines
- premiumIndexKlines
- daily metrics

Todos los controles de contenido utilizados verificaron el ZIP contra su `.CHECKSUM` oficial.

## Cobertura mensual

Entre 2020-01 y 2026-08:

| Familia | XRPUSDT | BTCUSDT |
|---|---:|---:|
| fundingRate | 80/80 meses | 80/80 meses |
| markPriceKlines 1m | 80/80 | 80/80 |
| indexPriceKlines 1m | 80/80 | 80/80 |
| premiumIndexKlines 1m | 80/80 | 80/80 |

La familia oficial encontrada es `premiumIndexKlines`; `premiumPriceKlines` no contiene los objetos buscados.

## Funding

Muestras verificadas:
- 2020-01
- 2023-01
- 2026-08

Checksums: PASS.

XRP empieza en enero 2020 después del inicio del contrato.
BTC tiene cobertura desde 2020-01.

La columna fuente es:
- `calc_time`
- `funding_interval_hours`
- `last_funding_rate`

Los timestamps recientes pueden contener offsets de pocos milisegundos respecto de la hora exacta. Se preservará el timestamp original y se normalizará únicamente para joins bajo reglas explícitas.

## Mark / Index / Premium

Las tres familias tienen todos los archivos mensuales esperados.

En la muestra 2020-01 aparece un hueco común:
- último minuto antes del hueco: 2020-01-19 13:08 UTC
- siguiente minuto: 2020-01-19 13:38 UTC
- salto: 30 minutos

Se observa en mark/index/premium y en ambos símbolos donde aplica. Los archivos pasan checksum.

Política:
- no interpolar;
- no usar observaciones futuras para llenar el hueco;
- marcar intervalos afectados como unavailable;
- el 1m contract kline previamente auditado sigue siendo la fuente canónica de precio negociado.

## Metrics — columnas

`metrics` contiene:
- create_time
- symbol
- sum_open_interest
- sum_open_interest_value
- count_toptrader_long_short_ratio
- sum_toptrader_long_short_ratio
- count_long_short_ratio
- sum_taker_long_short_vol_ratio

Cadencia nominal:
- 5 minutos.

### XRPUSDT metrics

Cobertura de archivos:
- 2021-12-01 → 2026-08-31
- 1,735 archivos diarios
- 0 días completos ausentes dentro del rango

Auditoría global:
- filas: 499,539
- timestamps únicos: 499,539
- slots 5m faltantes: 141
- timestamps duplicados: 0
- archivos con orden interno no monotónico: 111
- filas off-grid: 0
- bad timestamps: 0
- checksum/download failures: 0

Mayor gap:
- 2024-02-16 13:35 → 23:55 UTC
- 125 slots de 5m ausentes = 625 minutos

Otros gaps reproducidos:
- 2023-09-12 08:40 → 08:50 UTC: 3 slots
- 2025-08-29 06:20 → 06:30 UTC: 3 slots

Valores vacíos:
- count_toptrader_long_short_ratio: 91,930
- sum_toptrader_long_short_ratio: 91,893
- count_long_short_ratio: 5,790
- sum_taker_long_short_vol_ratio: 36,965

Valores cero:
- sum_open_interest: 196
- sum_open_interest_value: 206
- sum_taker_long_short_vol_ratio: 1

### BTCUSDT metrics

Cobertura de archivos:
- 2020-09-01 → 2026-08-31
- 2,191 archivos diarios
- 0 días completos ausentes dentro del rango

Auditoría global:
- filas: 705,629
- timestamps únicos: 630,374
- slots 5m faltantes: 634
- timestamps duplicados: 75,255
- extra rows por duplicación: 75,255
- extra rows duplicadas idénticas: 75,255
- timestamps con duplicados conflictivos: 0
- archivos con orden interno no monotónico: 370
- filas off-grid: 0
- bad timestamps: 0
- checksum/download failures: 0

Los duplicados comprobados son idénticos en valores, por lo que pueden colapsarse determinísticamente a una observación por timestamp sin elegir entre valores contradictorios.

Mayor gap:
- 2024-02-16 13:35 → 23:55 UTC
- 125 slots = 625 minutos

Hay además gaps relevantes en 2020-2021 y otros periodos.

Valores vacíos:
- count_toptrader_long_short_ratio: 92,227
- sum_toptrader_long_short_ratio: 92,193
- count_long_short_ratio: 5,797
- sum_taker_long_short_vol_ratio: 37,290

Valores cero:
- sum_open_interest: 473
- sum_open_interest_value: 485
- sum_taker_long_short_vol_ratio: 2

## Problema de semántica create_time

Binance public-data tiene una incidencia documentada en 2026 sobre cambio de etiquetado de `create_time` de end-of-period a start-of-period.

Para evitar look-ahead independientemente de cuál convención aplique:

**una observación metrics con create_time=t no será elegible para features hasta t+5m.**

Esta regla se aplica a toda la serie histórica V1, incluso donde resulte conservadora.

No se intenta “corregir” retrospectivamente el timestamp basándose en el resultado del mercado.

## Política canónica de normalización metrics

1. Parsear `create_time` como UTC.
2. Ordenar por timestamp; nunca confiar en el orden físico del CSV.
3. Duplicados con timestamp y valores idénticos:
   - conservar una sola fila;
   - registrar `dedup_identical=true`.
4. Duplicados conflictivos:
   - no escoger arbitrariamente;
   - marcar timestamp inválido para metrics.
5. Gaps:
   - mantener NA;
   - no interpolar;
   - no backward-fill desde futuro.
6. Campos vacíos:
   - NA.
7. OI/OI value igual a 0 durante mercado activo:
   - tratar como dato sospechoso;
   - no calcular variaciones porcentuales atravesando ese punto;
   - mantener flag `source_zero=true`.
8. Disponibilidad de feature:
   - `available_at = create_time + 5m`.
9. Join con decisiones:
   - as-of backward usando `available_at <= decision_time`.
10. Si no existe dato válido anterior bajo una tolerancia definida:
   - feature = NA;
   - nunca sustituir por observación futura.

## Ventanas reales para investigación

### XRP

2020-02 → 2021-11:
- precio/volumen 1m
- BTC context de precio
- funding
- mark/index/premium
- **sin XRP metrics/OI históricos oficiales**

2021-12 → 2026-08:
- anterior +
- OI
- OI value
- ratios de traders
- taker long/short ratio
- sujeto a gaps/NA y política de disponibilidad +5m

Por tanto, cualquier hipótesis cuyo requisito sea OI/ratios XRP tendrá discovery efectivo desde **2021-12-01**, no desde 2020.

### BTC context

Metrics disponible desde 2020-09-01, sujeto a deduplicación/gaps.

Antes de esa fecha, BTC puede aportar contexto de precio/funding pero no metrics históricos de esta fuente.

## Clasificación por familia

| Familia | Estado V1 | Uso |
|---|---|---|
| Contract 1m klines | PASS_WITH_OFFICIAL_DAILY_RECOVERY | Canonical price/volume |
| Funding | PASS_COVERAGE | Feature permitida |
| Mark price | PASS_WITH_GAPS | Feature opcional con NA |
| Index price | PASS_WITH_GAPS | Feature opcional con NA |
| Premium index | PASS_WITH_GAPS | Feature opcional con NA |
| XRP metrics | PASS_WITH_GAPS | Desde 2021-12, +5m availability |
| BTC metrics | PASS_WITH_DEDUP_AND_GAPS | Desde 2020-09, +5m availability |

## Scripts reproducibles

- `research/historical_derivatives_audit_v2.py`
- `research/historical_metrics_semantic_audit.py`
- `research/historical_full_metrics_audit.py`

Runs:
- Derivatives inventory/sample V2: `36766032278`
- Metrics semantic audit: `36766373351`
- Full metrics audit: `36766570950`

## Decisión

La capa histórica es apta para continuar a **normalización + feature engineering**, con las restricciones anteriores.

No se permite iniciar búsqueda de estrategia usando metrics sin aplicar primero esta política.
