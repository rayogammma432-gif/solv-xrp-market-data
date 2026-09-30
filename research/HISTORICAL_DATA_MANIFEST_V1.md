# Historical Data Manifest V1 — XRP / SOLV

## Estado

Diseño de fuentes previo a descarga. Ninguna fuente se considera aprobada hasta completar auditoría de cobertura e integridad.

## Fuente oficial

Binance Public Data:
`https://data.binance.vision/`

Documentación:
`https://github.com/binance/binance-public-data`

Contrato de estudio:
- USDⓈ-M Futures perpetual
- XRPUSDT
- SOLVUSDT
- BTCUSDT como contexto

## Fechas de inicio contractuales verificadas

### XRPUSDT
Binance Futures anunció/lanzó XRP/USDT Futures en enero de 2020.

Fecha de arranque de investigación:
- warm-up desde 2020-01-06
- discovery desde 2020-02-01

El primer timestamp real del archivo oficial debe verificarse durante el audit; el manifiesto no fuerza velas inexistentes.

### SOLVUSDT
Inicio oficial Binance USDⓈ-M SOLVUSDT perpetual:
- 2025-01-17 12:15 UTC

Periodo launch/warm-up:
- 2025-01-17 12:15 UTC a 2025-02-16 23:59 UTC

### BTCUSDT
Usar cobertura correspondiente a cada activo y añadir warm-up suficiente para indicadores de largo periodo.

## Dataset mínimo — Phase A

Para cada activo/contexto:

### 1m klines

Ruta conceptual:
`data/futures/um/{daily|monthly}/klines/{SYMBOL}/1m/`

Campos esperados:
1. open_time
2. open
3. high
4. low
5. close
6. volume
7. close_time
8. quote_asset_volume
9. number_of_trades
10. taker_buy_base_asset_volume
11. taker_buy_quote_asset_volume
12. ignore

Uso:
- fuente canónica de precio/volumen
- reconstrucción 5m/15m/1H/4H/1D
- cálculo EMA/RSI/ATR/VWAP
- taker imbalance aproximado desde volumen total y taker-buy

### Validación multi-timeframe

Descargar una muestra de klines nativos 5m/15m/1h/4h/1d y comparar con resampling desde 1m.

Si no coinciden:
- no continuar;
- identificar boundary/timestamp/partial-bar issue.

## Dataset Phase B — sujeto a audit

Auditar disponibilidad histórica y cobertura para:

- fundingRate
- markPriceKlines
- indexPriceKlines
- premiumIndexKlines
- metrics

### Metrics esperadas si existen

- create_time
- symbol
- sum_open_interest
- sum_open_interest_value
- count_toptrader_long_short_ratio
- sum_toptrader_long_short_ratio
- count_long_short_ratio
- sum_taker_long_short_vol_ratio

Cadencia esperada del archivo metrics: normalmente 5 minutos, pero debe verificarse archivo por archivo.

No rellenar slots faltantes.

## Dataset Phase C — solo si agrega información

### aggTrades

Ruta conceptual:
`data/futures/um/{daily|monthly}/aggTrades/{SYMBOL}/`

Campos:
- aggregate trade id
- price
- quantity
- first trade id
- last trade id
- timestamp
- was buyer maker

Solo incorporar si las hipótesis de microestructura requieren información no contenida en los klines 1m.

## Checksums

Por cada archivo descargado:
- descargar ZIP
- descargar `.CHECKSUM`
- verificar SHA-256
- registrar hash y tamaño en manifest local
- conservar archivo raw inmutable

Si Binance reemplaza posteriormente un archivo histórico, la nueva versión debe tener un nuevo registro de versión; no sobrescribir silenciosamente la copia usada por un experimento ya congelado.

## Convención temporal

- timezone: UTC
- timestamp interno: epoch milliseconds + ISO8601 UTC
- barras identificadas por open_time
- una feature de barra solo es utilizable después de close_time
- higher-TF bars se forman con boundaries UTC
- no forward fill de valores de mercado desconocidos salvo que la semántica de la variable sea explícitamente “last known value” y se documente

## Estructura propuesta de almacenamiento

`historical/raw/binance/um/{symbol}/{dataset_type}/...`

`historical/audit/{symbol}/...`

`historical/normalized/{symbol}/...`

`historical/features/{symbol}/...`

`historical/experiments/{symbol}/...`

No subir archivos históricos masivos al repositorio Git si exceden un tamaño razonable. GitHub guarda código, manifests, hashes, schemas y resultados resumidos; los datos masivos deben residir en almacenamiento diseñado para datasets.

## Audit report requerido

Antes de feature engineering, producir para cada símbolo:

- first timestamp
- last timestamp
- expected rows
- actual rows
- missing intervals
- duplicates
- off-grid timestamps
- bad OHLC relationships
- negative/invalid volume
- checksum failures
- files unavailable
- coverage percentage

Resultado:
- PASS
- PASS_WITH_GAPS
- FAIL

No iniciar estrategia para un símbolo con FAIL.

## Orden de ejecución inicial

1. XRPUSDT 1m
2. BTCUSDT 1m para el mismo rango XRP
3. SOLVUSDT 1m
4. BTCUSDT 1m para el mismo rango SOLV
5. validar resampling
6. auditar funding/mark/index/premium
7. auditar metrics
8. decidir si aggTrades aporta valor

Este orden permite tener un baseline sólido sin depender de datasets de derivados cuya cobertura histórica pueda ser irregular.
