# XRP + BTC 1m Historical Data Audit V1 — Final

## Estado

**PASS_WITH_OFFICIAL_DAILY_RECOVERY**

Fecha de auditoría: 2026-09-30 UTC.

Esta auditoría valida la capa canónica de klines 1m para investigación histórica de XRPUSDT con BTCUSDT como contexto. No valida todavía OI, funding, ratios, mark/index/premium ni aggTrades.

## Fuente

Binance Public Data — USD-M Futures.

Fuente primaria:
- archivos mensuales 1m
- checksum oficial `.CHECKSUM`

Recuperación permitida:
- únicamente archivos diarios oficiales Binance con checksum válido cuando el archivo mensual presenta un hueco demostrado.

No se usa:
- interpolación;
- forward fill de precio;
- datos de terceros;
- datos de los agentes CURRENT.

## Auditor reproducible

Código:
- `research/historical_data_audit.py`
- `research/historical_full_1m_audit.py`
- `research/historical_gap_recovery.py`

Workflows:
- `.github/workflows/historical-data-audit.yml`
- `.github/workflows/historical-full-1m-audit.yml`
- `.github/workflows/xrp-gap-recovery-audit.yml`

Runs principales:
- muestra/resampling: GitHub Actions run `36761998521`
- auditoría completa 1m: GitHub Actions run `36762316438`
- recuperación XRP 2022: GitHub Actions run `36763005844`

## Inventario mensual

Se comprobaron 80 meses por símbolo, desde 2020-01 hasta 2026-08.

| Símbolo | Meses comprobados | Archivos mensuales disponibles | Archivos mensuales ausentes |
|---|---:|---:|---:|
| XRPUSDT | 80 | 80 | 0 |
| BTCUSDT | 80 | 80 | 0 |

## Auditoría completa BTCUSDT 1m

Rango:
- 2020-01-01 00:00 UTC
- 2026-08-31 23:59 UTC

Resultados:
- filas: 3,506,400
- checksum failures: 0
- download errors: 0
- internal gaps: 0
- cross-month gaps: 0
- duplicates: 0
- off-grid timestamps: 0
- bad OHLC: 0
- bad volume: 0
- unexpected row-count months: 0

**Resultado BTC: PASS**

## Auditoría completa XRPUSDT 1m — capa mensual

Primer registro:
- 2020-01-06 08:21 UTC

Último registro:
- 2026-08-31 23:59 UTC

Filas mensuales originales:
- 3,491,499

Checks de integridad:
- checksum failures: 0
- download errors: 0
- internal gaps dentro de archivos: 0
- duplicates: 0
- off-grid timestamps: 0
- bad OHLC: 0
- bad volume: 0

Se detectaron dos discontinuidades entre archivos mensuales:

### Gap XRP-2022-02

El archivo mensual termina:
- 2022-02-25 23:59 UTC

Faltan:
- 2022-02-26
- 2022-02-27
- 2022-02-28

Minutos ausentes del archivo mensual:
- 4,320

### Gap XRP-2022-04

El archivo mensual comienza:
- 2022-04-03 00:00 UTC

Faltan:
- 2022-04-01
- 2022-04-02

Minutos ausentes del archivo mensual:
- 2,880

Total ausente en los ZIP mensuales:
- 7,200 minutos

Los ZIP mensuales afectados pasan sus checksums oficiales. Por tanto, el hueco forma parte del contenido publicado del archivo mensual y no es corrupción de descarga local.

## Recuperación con archivos diarios oficiales

Se comprobaron los cinco ZIP diarios correspondientes:

| Fecha | Disponible | Checksum | Filas | Duplicados | Gaps |
|---|---|---|---:|---:|---:|
| 2022-02-26 | YES | PASS | 1,440 | 0 | 0 |
| 2022-02-27 | YES | PASS | 1,440 | 0 | 0 |
| 2022-02-28 | YES | PASS | 1,440 | 0 | 0 |
| 2022-04-01 | YES | PASS | 1,440 | 0 | 0 |
| 2022-04-02 | YES | PASS | 1,440 | 0 | 0 |

**Resultado de recuperación: RECOVERABLE_FROM_DAILY**

Política canónica V1:
- usar mensual como fuente normal;
- para estos 7,200 minutos usar exclusivamente los archivos diarios oficiales verificados;
- registrar en el manifest normalizado que esas filas tienen `source_granularity=daily_recovery`;
- conservar checksum y nombre del archivo fuente;
- nunca ocultar la sustitución.

Filas XRP canónicas después de la recuperación:
- 3,498,699

Esto coincide exactamente con una rejilla continua de 1 minuto desde 2020-01-06 08:21 UTC hasta 2026-08-31 23:59 UTC.

## Validación de resampling

Muestras controladas:
- 2020-02
- 2026-08

Comparación del 1m reconstruido contra klines nativos Binance 5m / 15m / 1h / 4h.

BTCUSDT:
- todos los timeframes comparados: PASS en ambas muestras.

XRPUSDT:
- 2026-08: todos PASS.
- 2020-02: 15m / 1h / 4h PASS.
- 2020-02 5m: una discrepancia puntual.

Discrepancia:
- bucket: 2020-02-25 22:05 UTC
- open reconstruido desde el primer 1m: 0.2562
- open del archivo nativo 5m: 0.2561
- no hubo diferencias reportadas en high/low/close/volume para ese bucket.

Política:
- el dataset canónico usa 1m;
- los timeframes superiores se reconstruyen desde 1m;
- el 5m nativo funciona como control, no como fuente primaria;
- esta anomalía queda registrada y no se corrige usando hindsight.

## Resultado final

### BTC
**PASS**

### XRP
**PASS_WITH_OFFICIAL_DAILY_RECOVERY**

La capa 1m de XRP/BTC es apta para avanzar a feature engineering después de aplicar la recuperación oficial documentada.

Antes de construir estrategia falta auditar por separado:
- funding;
- mark price;
- index price;
- premium index;
- OI / historical metrics;
- ratios de posicionamiento.

No se ha explorado ninguna estrategia ni outcome en esta auditoría.
