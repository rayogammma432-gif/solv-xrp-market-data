# XRP Forward Research Protocol V3.1

## Estado

**FROZEN BEFORE FORWARD START**

Versión:
- `XRP_FORWARD_V3_1`

Supersedes before launch:
- `XRP_FORWARD_V3`

Forward start:
- `2026-10-01T06:00:00Z`

Historical 2026 holdout:
- **LOCKED / NOT READABLE**
- 2026-01-01 00:00 UTC → 2026-08-31 23:59 UTC

## Motivo de V3.1

V3.1 corrige la capa de captura antes de abrir la ventana prospectiva:
- catch-up de todas las velas, no solo la última;
- PRIMARY_15M resampleado desde 1m igual que el histórico;
- recuperación de estado desde Google Sheets;
- auditoría horaria de cobertura;
- provenance de código/payload;
- gate estadístico común con Holm.

No se observaron resultados forward para diseñar estas correcciones.

## Objetivo

Evaluar prospectivamente tres relaciones históricas sin convertirlas prematuramente en estrategia.

Modo:
- shadow research;
- no SIGNALS;
- no orders;
- no trades;
- no TP/SL operacional;
- no cambios al agente XRP CURRENT.

## Candidate A — SCALP Taker-Flow Exhaustion

ID:
- `XRP-FWD-V3-A-TAKER-EXHAUSTION`

Grid:
- SCALP_1M construido de XRPUSDT 1m cerrado.

Features:
- xrp_taker_imbalance
- xrp_rel_volume20

Regla fija:
- abs(taker_imbalance) >= 0.30
- rel_volume20 >= 1.5

Dirección:
- imbalance > 0 → SHORT
- imbalance < 0 → LONG

Primary:
- signed forward 15m

Secondary diagnostics:
- 5m
- 30m
- MFE/MAE 15m

Muestra mínima propia:
- 90 días calendario;
- >=12,000 eventos;
- >=3,000 por lado;
- >=75 días con eventos.

Effect floor:
- mean signed 15m >= 0.00010.

El checkpoint de 90 días es informativo solamente. No existe PASS formal de V3.1 antes del gate común de 180 días.

## Candidate B — PRIMARY OI Momentum Moderator

ID:
- `XRP-FWD-V3-B-OI-MODERATOR`

Grid:
- PRIMARY_15M resampleado exclusivamente desde 15 velas XRPUSDT 1m consecutivas, alineadas a UTC.

Features:
- xrp_ret_12
- xrp_oi_chg_15m

Regla fija:
- abs(ret_12) >= 0.005
- expansion: oi_chg_15m >= 0.005
- contraction: oi_chg_15m <= -0.005

Dirección base:
- sign(ret_12)

Primary effect:
- mean signed 60m expansion - mean signed 60m contraction.

Muestra mínima:
- >=600 expansion;
- >=600 contraction;
- >=150 días elegibles.

Effect floor:
- 0.00040.

## Candidate C — PRIMARY Momentum Exhaustion

ID:
- `XRP-FWD-V3-C-MOMENTUM-EXHAUSTION`

Grid:
- PRIMARY_15M resampleado desde 1m, igual que FEATURES_V1 histórico.

Features:
- xrp_ret_12
- xrp_rel_volume20

Regla fija:
- abs(ret_12) >= 0.010
- rel_volume20 >= 1.5

Dirección:
- ret_12 > 0 → SHORT
- ret_12 < 0 → LONG

Primary:
- signed forward 60m

Secondary:
- 15m
- 240m
- MFE/MAE 60m

Muestra mínima:
- >=1,200 eventos;
- >=250 por lado;
- >=150 días elegibles.

Effect floor:
- 0.00043.

## Paridad histórica/live

Las features usadas por V3.1 deben conservar la misma semántica que FEATURES_V1:

### SCALP_1M
- ret/volume/taker provienen del kline 1m cerrado exacto.

### PRIMARY_15M
- no usa el kline 15m nativo para generar features V3.1;
- agrupa exactamente 15 velas 1m consecutivas;
- bucket UTC:
  `floor(open_time / 900000) * 900000`;
- OHLCV/taker/trades se resamplean igual que `historical_normalizer_v1.resample_contract`.

### ret_12
- `close_t / close_(t-12 bars) - 1`.

### rel_volume20
- volumen actual / promedio de las 20 barras anteriores, excluyendo la actual.

### taker_imbalance
- `2 * taker_buy_base / volume - 1`;
- ratio fuera de [0,1] = dato inválido, fail-closed.

### OI
Historical semantics:
- metric timestamp t available at t+5m.

Live semantics:
- Binance openInterestHist 5m;
- se solicita usando startTime/endTime alrededor del decision_time;
- solamente se acepta una observación cuyo `timestamp + 5m <= decision_time`;
- oi_chg_15m exige el timestamp exacto t-15m;
- no nearest futuro;
- no interpolación.

## Catch-up y cobertura

Cada ciclo V3.1 consulta klines 1m suficientes para:
- warm-up >=360 minutos;
- recuperar todas las decisiones posteriores al último decision_time evaluado.

La API se pagina cuando sea necesario.

Una reconexión debe evaluar cada vela perdida en orden cronológico.

Si OI histórico live ya no puede recuperarse por límites de retención del proveedor:
- Candidate B no se fabrica;
- el health log registra el fallo/cobertura perdida.

## Recovery

Google Sheets es almacenamiento persistente.

Si se pierde el estado local:
1. receptor devuelve eventos V3 recientes;
2. devuelve Outcome IDs ya existentes;
3. devuelve el último health checkpoint;
4. Termux reconstruye eventos pendientes;
5. reanuda desde el último decision_time evaluado.

No se infiere que un evento esté completo si falta su Outcome ID.

## Auditoría de cobertura

`FORWARD_V3_HEALTH` registra por hora UTC finalizada:
- expected/evaluated/missing 1m;
- expected/evaluated/missing 15m;
- OI checks/failures;
- eventos A/B/C;
- pending events;
- outcomes INCOMPLETE;
- last evaluated timestamps;
- collector provenance.

Una hora se finaliza solo después de 10 minutos de gracia.

Gate de datos:
- cualquier hora con missing_1m > 0 o missing_15m > 0 queda marcada para revisión;
- no se oculta una pérdida de cobertura.

## Outcomes

Reference price:
- close exacto de la barra de decisión.

Para horizon h:
- target exacto = decision_time + h;
- se requieren todas las velas 1m exactas de la ventana;
- no nearest;
- no interpolación.

Grace de retraso:
- 5 minutos posteriores al target.

Después:
- si la ventana sigue incompleta, outcome = INCOMPLETE con valores vacíos.

## Provenance

Cada evento/outcome registra:
- protocol version;
- registry SHA256;
- feature/live-equivalence version;
- collector version;
- collector Git SHA;
- canonical payload SHA256;
- receptor version;
- receptor write UTC.

El payload hash se calcula antes de la escritura del receptor.

## Gate estadístico común

No existe selección formal en checkpoints parciales.

Fecha mínima del gate familiar:
- `2027-03-30T06:00:00Z`
- 180 días desde forward_start.

En ese gate:
1. calcular primary effect de A, B y C;
2. UTC-day block bootstrap, 2,000 réplicas;
3. one-sided p por candidato;
4. aplicar Holm entre los 3 primary p-values;
5. exigir CI95 lower > 0;
6. exigir effect floor propio;
7. exigir muestra mínima propia;
8. exigir estabilidad temporal preregistrada.

A puede tener un reporte informativo a 90 días:
- `2026-12-30T06:00:00Z`;
- ese reporte no puede promoverlo ni cambiar parámetros.

Secondary horizons son diagnostics y nunca sustituyen el primary después de ver datos.

## Comparación futura contra CURRENT

No se compararán win rates brutos de poblaciones diferentes.

Una futura comparación debe preregistrarse como:
- paired comparison sobre los mismos timestamps, o
- portfolio comparison con mismo calendario, capital, riesgo, fees, slippage y reglas de ejecución.

## Gate económico posterior

`FORWARD_PASS_RESEARCH` no autoriza trading.

Después de un pass se requiere un gate separado con:
- fees;
- bid/ask spread;
- slippage;
- latency;
- fill probability;
- sizing/risk;
- net expectancy.

## Inmutabilidad

Desde `2026-10-01T06:00:00Z`:
- thresholds no cambian;
- horizons no cambian;
- floors no cambian;
- catch-up no excluye eventos malos;
- filtros nuevos crean V4 y una ventana prospectiva nueva.

## Estado final antes de launch

- Historical 2026 holdout: LOCKED
- V3 original: SUPERSEDED BEFORE START
- V3.1: FROZEN
- forward results observed: NO
- validated challenger: NONE
