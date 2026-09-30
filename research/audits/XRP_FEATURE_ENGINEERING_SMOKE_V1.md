# XRP Feature Engineering Smoke V1 — Approved

## Estado

**PASS**

Fecha: 2026-09-30 UTC.

Feature set:
- `FEATURES_V1`

Input:
- `HIST_NORM_V1`

Run:
- `36768854695`

Artifact:
- `11123172426`

Feature contract:
- `research/HISTORICAL_FEATURE_CONTRACT_V1.md`

Builder:
- `research/historical_feature_builder_v1.py`

Workflow:
- `.github/workflows/xrp-feature-engineering-smoke-v1.yml`

## Propósito

Validar que FEATURES_V1 puede reconstruirse de forma determinista sobre la capa normalizada, respetando disponibilidad histórica y sin consultar outcomes ni decisiones de los agentes CURRENT.

## Mes de control

`2023-01`

La prueba reconstruyó HIST_NORM_V1 desde las fuentes oficiales y luego ejecutó el builder FEATURES_V1 dos veces de forma independiente sobre el mismo input.

## Filas de decisión

Total:
- **47,616**

Desglose:
- SCALP_1M: **44,640**
- PRIMARY_15M: **2,976**

No se usaron alertas CURRENT para definir el universo de decisiones.

## Features incluidas

### XRP price / flow
Por grid:
- close
- ret_1 / ret_3 / ret_12
- EMA20 / EMA50 / EMA200
- RSI14
- ATR14
- ATR %
- distancia EMA20/50/200 en ATR
- relative volume 20
- relative trades 20
- taker buy ratio
- taker imbalance
- distancia al high/low previo de 20 barras en ATR
- UTC session VWAP
- distancia a VWAP en ATR

### BTC context
Mismo set continuo de precio/flow bajo el timeframe de cada grid, unido exclusivamente por barra histórica disponible.

### XRP derivatives
- funding rate + age
- OI / OI value
- OI change 5m / 15m / 60m
- top-trader count ratio
- top-trader position ratio
- global long/short ratio
- taker long/short volume ratio
- metrics age
- mark close
- index close
- premium close
- mark/index basis

### BTC derivatives context
- funding rate + age
- OI
- OI change 15m / 60m
- metrics age

## Reglas temporales

- XRP decision_time proviene del cierre disponible de la barra del grid.
- BTC bar usada debe tener `available_at <= decision_time`.
- metrics solo se usa después de `create_time + 5m`.
- funding solo si `available_at <= decision_time`, staleness <= 12h.
- metrics staleness <= 10m.
- mark/index/premium staleness <= 2m.
- OI changes requieren timestamp exacto N minutos atrás; no saltan gaps.
- NA permanece NA.
- no nearest-future joins.

## QA

Resultados:

- future-lineage violations: **0**
- duplicate decision rows: **0**
- ordering violations: **0**
- warm-up violations: **0**
- non-finite numeric values: **0**
- taker_buy_ratio fuera de [0,1]: **0**

Warm-up validado:
- EMA200 no aparece antes de 200 barras.
- RVOL20 no aparece antes de 20 barras previas.
- Donchian previo 20 no aparece antes de 20 barras previas.

## Determinismo

Las dos ejecuciones independientes produjeron el mismo archivo byte-a-byte.

SHA-256:
`81602105ee25407c0c3c22d1fc9cd7a20a49f88788798b6aa62334a304aeb11d`

`cmp`:
- PASS

Esto demuestra reproducibilidad del builder para el input controlado.

## Exclusiones verificadas

No se leyeron:
- forward returns
- MFE
- MAE
- ANALYSES
- SIGNALS
- PERFORMANCE
- decisiones CURRENT
- ALERT_FORWARD
- ALERT_MFE_MAE

La salida no contiene:
- LONG/SHORT decision
- score
- entry
- stop
- TP
- trade outcome

## Decisión

**Gate FEATURES_V1 aprobado.**

El siguiente paso permitido por `HISTORICAL_RESEARCH_PROTOCOL_V1` es:

**Baseline descriptivo sin estrategia.**

Ese baseline debe estudiar cobertura, distribución, missingness, estabilidad temporal y dependencia entre features sin usar resultados futuros para seleccionar reglas.
