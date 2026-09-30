# Historical Research Protocol V1 — XRP / SOLV

## Objetivo

Construir agentes históricos independientes para XRPUSDT y SOLVUSDT usando exclusivamente información de mercado disponible hasta cada instante histórico, y comparar posteriormente esos agentes contra los agentes operativos actuales en un forward test prospectivo.

Este protocolo se define **antes** de descargar, explorar o optimizar la base histórica para reducir look-ahead, leakage y sobreajuste.

## Principio experimental

Se mantienen dos familias separadas:

- **CURRENT**: agentes operativos actuales (por ejemplo XRP_V3.3 y SOLV_V3.3, o sus sucesores).
- **HISTORICAL CHALLENGER**: agentes construidos desde investigación histórica, sin usar las decisiones, resultados o reglas del CURRENT como etiquetas.

Durante el desarrollo del challenger está prohibido usar como input:
- `ANALYSES`
- `SIGNALS`
- `PERFORMANCE`
- `ALERT_FORWARD`
- `ALERT_MFE_MAE`
- decisiones/resultados de los agentes actuales

Los masters CURRENT pueden consultarse únicamente después del freeze del challenger para documentar diferencias conceptuales; no se usan para seleccionar thresholds del challenger.

## Activos

Cada activo se investiga de forma independiente.

### XRP
- Mercado: Binance USDⓈ-M Futures XRPUSDT perpetual.
- Binance anunció XRP/USDT Futures en enero de 2020.
- BTCUSDT se usa como contexto externo.

### SOLV
- Mercado: Binance USDⓈ-M Futures SOLVUSDT perpetual.
- Inicio oficial del contrato: 2025-01-17 12:15 UTC.
- BTCUSDT se usa como contexto externo.
- El periodo inicial de listado se trata como régimen especial y no debe mezclarse sin control con el resto de la muestra.

No entrenar un modelo conjunto XRP+SOLV en V1.

## Fuente primaria

Fuente oficial preferida:
- Binance Public Data / data.binance.vision
- USD-M Futures
- archivos diarios o mensuales con checksum

Los datos base deben conservarse sin modificar y verificarse contra los archivos `.CHECKSUM`.

La documentación oficial de Binance indica que los archivos Futures incluyen klines y aggTrades, y que los klines USD-M contienen OHLCV, quote volume, número de trades y taker-buy volume.

## Capas del dataset

### Tier A — requerido

Para XRPUSDT, SOLVUSDT y BTCUSDT:
- 1m USD-M Futures klines
- open time / close time
- OHLC
- base volume
- quote volume
- number of trades
- taker buy base volume
- taker buy quote volume

Los timeframes 5m, 15m, 1H, 4H y 1D se reconstruyen desde 1m con fronteras UTC deterministas. Los archivos nativos de esos timeframes pueden usarse como control de integridad, no como fuente paralela de features.

### Tier B — incorporar solo después de auditoría de cobertura

- funding rate
- mark price
- index price
- premium index
- historical metrics archive:
  - open interest
  - open interest value
  - top-trader long/short ratios
  - global long/short ratio
  - taker long/short volume ratio

Los endpoints REST de varias métricas de derivados solo conservan aproximadamente los últimos 30 días; por tanto, para historia profunda se debe auditar primero la cobertura del archivo público y no asumir que la API REST puede reconstruir años completos.

### Tier C — opcional

- aggTrades

No se descargan inicialmente si la información de taker flow de klines es suficiente para la primera investigación. Se incorporan únicamente si una hipótesis concreta necesita granularidad intraminuto.

### Excluido en V1

- order-book histórico no verificable de forma uniforme
- fuentes de terceros usadas como sustituto de datos faltantes
- datos derivados de ejecuciones del usuario
- cualquier dato posterior al timestamp de decisión

## Auditoría obligatoria antes de investigación

Para cada activo y fuente:

1. enumerar archivos esperados;
2. verificar checksum;
3. detectar días/meses ausentes;
4. detectar timestamps duplicados;
5. validar monotonía temporal;
6. validar rejilla de 1 minuto;
7. medir porcentaje de cobertura;
8. marcar gaps explícitamente;
9. no interpolar OHLCV, OI, funding ni ratios;
10. excluir o etiquetar intervalos afectados.

El archivo público de Binance ha tenido incidencias documentadas de slots faltantes en métricas de 5 minutos; por ello ningún archivo `metrics` se considera completo sin auditoría.

## Regla temporal / anti-look-ahead

Para una decisión con timestamp `t`:

- solo se usan velas y métricas cuyo periodo haya cerrado en o antes de `t`;
- una vela en formación nunca participa;
- indicadores se calculan únicamente con observaciones disponibles hasta `t`;
- features de un timeframe superior solo cambian cuando ese timeframe cierra;
- joins de funding/OI/metrics usan backward/as-of join, nunca nearest futuro;
- no se hace backfill de un dato faltante usando la siguiente observación conocida.

## Universo de decisiones

El challenger no se entrena únicamente en alertas generadas por el CURRENT.

### PRIMARY research grid
Una observación en cada cierre de vela de 15m.

### SCALP research grid
Una observación en cada cierre de vela de 1m.

Se permite posteriormente crear un generador objetivo de eventos (breakout, reclaim, sweep, pullback, etc.), pero debe definirse solo con precio/volumen histórico y quedar versionado. No puede depender de que el agente CURRENT haya enviado una alerta.

## Features V1

Se pueden investigar, sin asumir de antemano que son predictivas:

- estructura de precio
- returns y momentum
- EMA 20/50/200
- RSI14
- ATR14
- VWAP UTC
- volumen relativo
- número de trades
- taker buy/sell imbalance
- distancia a EMA/nivel expresada en ATR
- breakout / retest
- reclaim / lose
- sweep / rejection
- swing structure
- BTC context
- funding, OI y ratios solo donde la cobertura histórica pase auditoría
- SuperTrend / Donchian-derived features si se reconstruyen determinísticamente

Toda feature nueva debe documentar fórmula, inputs y timestamp de disponibilidad.

## Outcomes

Mantener compatibilidad con la investigación existente:

- forward return 5m
- forward return 15m
- forward return 30m
- forward return 60m
- forward return 240m
- MFE 15m / 60m / 240m
- MAE 15m / 60m / 240m

Para simulaciones de entrada, la ejecución más temprana permitida es la primera observación negociable **posterior** a la decisión. No asumir fill retrospectivo en un precio conocido solo al cierre.

Separar:
- **directional outcome**: qué hizo el mercado después;
- **trade simulation**: entrada/stop/TP/costes bajo reglas ejecutables.

## Particiones temporales bloqueadas

### XRP

- Warm-up / calidad: 2020-01-06 a 2020-01-31
- Discovery: 2020-02-01 a 2023-12-31
- Validation: 2024-01-01 a 2025-12-31
- Historical holdout: 2026-01-01 a 2026-08-31
- Embargo: 2026-09-01 a 2026-09-30
- Forward head-to-head: comienza únicamente después del freeze formal del challenger

### SOLV

- Launch/warm-up: 2025-01-17 12:15 UTC a 2025-02-16 23:59 UTC
- Discovery: 2025-02-17 a 2025-10-31
- Validation: 2025-11-01 a 2026-04-30
- Historical holdout: 2026-05-01 a 2026-08-31
- Embargo: 2026-09-01 a 2026-09-30
- Forward head-to-head: comienza únicamente después del freeze formal del challenger

El historical holdout puede usarse para evaluar el challenger después de congelar reglas, pero **no** se considera una prueba limpia del CURRENT porque el CURRENT fue desarrollado durante parte de 2026.

## Proceso de desarrollo

1. Data audit.
2. Feature reconstruction.
3. Baseline descriptivo sin estrategia.
4. Hipótesis preregistradas.
5. Discovery.
6. Validation.
7. Freeze de reglas y parámetros.
8. Abrir historical holdout.
9. Si el challenger supera los criterios mínimos previamente definidos, crear master:
   - `XRP_HIST_V1_MASTER.txt`
   - `SOLV_HIST_V1_MASTER.txt`
10. Registrar commit SHA de cada master congelado.
11. Iniciar forward head-to-head.

No modificar el historical holdout después de verlo para “arreglar” la estrategia. Si se modifica el challenger tras abrir el holdout, pasa a V2 y necesita un nuevo periodo realmente no visto.

## Control de múltiples pruebas

Cada experimento debe registrar:
- hypothesis_id
- fecha de definición
- activo
- feature/set-up
- parámetros probados
- periodo usado
- resultado completo, incluso si falla

No borrar experimentos negativos.

No seleccionar una regla únicamente porque maximiza un único backtest.

## Inferencia y dependencia temporal

Los eventos cercanos pueden compartir el mismo movimiento y no son observaciones estadísticamente independientes.

Por ello:
- reportar número bruto de eventos;
- reportar eventos/periodos no solapados cuando aplique;
- usar bootstrap por bloques temporales o agrupación por día/semana para intervalos de confianza;
- evitar interpretar miles de velas correlacionadas como miles de trades independientes.

## Métricas de evaluación

Como mínimo:

- coverage / activation rate
- LONG vs SHORT
- PRIMARY vs SCALP
- forward returns por horizonte
- MFE / MAE
- hit rate bajo definición explícita
- expectancy en R para simulaciones ejecutables
- payoff ratio
- max drawdown de la simulación
- profit factor, si la simulación define trades
- duración
- estabilidad por año/mes
- estabilidad por régimen de volatilidad
- estabilidad con BTC favorable / neutral / contrario
- sensibilidad a costes y slippage

No elegir ganador por win rate aislado.

## Criterio para crear un challenger operativo

Antes del freeze se definirán thresholds cuantitativos mínimos. Como regla metodológica:

- debe mostrar señal consistente en discovery y validation;
- no puede depender de una única ventana o dirección;
- la ventaja debe sobrevivir costes razonables;
- debe tener muestra suficiente para estimar incertidumbre;
- no puede degradarse completamente al cambiar de régimen;
- ninguna métrica del historical holdout puede utilizarse para ajustar V1.

## Head-to-head CURRENT vs HISTORICAL

Una vez congelado el challenger:

1. congelar también el commit SHA del CURRENT que participará en esa comparación;
2. cada nueva captura elegible se entrega a ambos motores de forma independiente;
3. ninguno recibe la decisión del otro;
4. ambos reciben exactamente el mismo snapshot disponible en ese instante;
5. guardar resultados en namespaces/tablas separados;
6. evaluar ambos contra los mismos outcomes futuros;
7. no cambiar reglas durante una cohorte activa.

Una alerta/captura puede generar:
- decisión CURRENT
- decisión HISTORICAL
- desacuerdo
- acuerdo

Los acuerdos y desacuerdos se estudian como variables; no se fusionan automáticamente.

## Independencia entre activos

XRP_HIST y SOLV_HIST tienen:
- datasets separados;
- parámetros separados;
- masters separados;
- evaluación separada.

Posteriormente se pueden comparar patrones que generalizan, pero un resultado de XRP no se copia automáticamente a SOLV.

## Versionado

Archivos esperados:

- `research/HISTORICAL_RESEARCH_PROTOCOL_V1.md`
- `research/HISTORICAL_DATA_MANIFEST_V1.md`
- futuros `research/experiments/*.jsonl`
- futuros masters en `agents/`

Toda modificación material al protocolo crea V2; no reescribir silenciosamente V1 una vez iniciada la exploración.
