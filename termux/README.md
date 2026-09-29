# Recolector Termux incremental — SOLV/XRP/BTC

Versión 2: actualización cada minuto con escritura incremental.

## Comportamiento
- Al arrancar: bootstrap de 500 velas cerradas para 1m/15m/1h/4h.
- Cada minuto: solo nueva vela 1m + MARKET + OI actual + LIVE_STATE.
- En cierres 15m: añade nueva 15m y actualiza OI_HISTORY.
- En cierres 1H: añade nueva 1H.
- En cierres 4H: añade nueva 4H.
- OI_1M es muestreo local del endpoint de OI actual; no es histórico oficial de Binance a 1m.

## Seguridad
`config.json` contiene URLs /exec y Shared Secrets. Nunca se sube a GitHub.

## Actualizar una instalación existente
```sh
cd ~/solv-xrp-market-data
git pull
cd termux
python -m pip install -r requirements-termux.txt
```

Antes de arrancar la versión 2, despliega primero los nuevos receptores Apps Script incluidos en `apps-script/`.

## Prueba manual
```sh
python market_collector.py --dry-run
```

La ejecución real de `python market_collector.py` hace un bootstrap completo.

## Servicio 24/7
```sh
./stop_collector.sh
./start_collector.sh
./status_collector.sh
```

El scheduler corre alrededor del segundo 10 de cada minuto UTC.

## Inicio automático
Termux:Boot continúa usando:
```
~/.termux/boot/start-market-data.sh
```


## Alertas Telegram 24/7
El Motorola puede detectar candidatos preliminares sin consumir ejecuciones de ChatGPT. La configuración inicial activa solo SOLV; XRP se añade después de optimizar su agente:

- Cierre 1H: si aparece candidato PRIMARY, envía `VIGILAR`.
- Cierre 15m: si el PRIMARY vigilado obtiene trigger, envía alerta para abrir el agente.
- Cierre 15m: también arma un candidato SCALP cuando el contexto preliminar lo permite.
- Cierre 1m: si el scalp vigilado obtiene trigger microestructural, envía alerta.
- El detector es determinista y preliminar; ChatGPT sigue haciendo la validación final de estructura, stop y R:R.

### Configurar Telegram
No pegues el token del bot en GitHub.

Después de `git pull`, dentro de `termux/` ejecuta:

```sh
python configure_telegram.py
```

El script pide el token de forma oculta, identifica tu chat después de que envíes `/start`, guarda `bot_token` y `chat_id` únicamente en `config.json` local y manda un mensaje de prueba.

Después reinicia:

```sh
bash stop_collector.sh
bash start_collector.sh
bash status_collector.sh
```

Estado local de deduplicación: `alert_state.json` (ignorado por Git).


## SIGNALS / PERFORMANCE — SOLV

XRP queda pendiente. Esta fase se activa solo para SOLV.

Google Sheet incluye:
- `SIGNALS`: una fila por señal ACTIVA emitida por el agente.
- `PERFORMANCE`: KPIs, R acumulado, drawdown, desglose por motor/dirección y gráfico.

El agente debe registrar solo LONG/SHORT ACTIVOS, nunca CONDICIONAL o NO OPERAR.

Columnas SIGNALS A:W:
`Signal ID, Signal UTC, Motor, Direction, Setup, Entry, Stop, TP1, TP2, Risk %, Confluences, State, Result, Result R, MFE R, MAE R, Bars elapsed, TP1 hit UTC, Close UTC, Exit Price, Exit Reason, Time Stop Status, Notes`.

Al crear la señal:
- `State=OPEN`
- `Time Stop Status=OK`
- resultados y métricas de salida vacíos.

El receptor SOLV devuelve las señales OPEN al Motorola. El Motorola calcula sobre velas cerradas 1m:
- TP/SL,
- MFE/MAE en R,
- bars elapsed,
- TP1 -> 50% realizado y stop del 50% restante a BE,
- TP2,
- ambigüedad si TP y stop/BE aparecen en la misma vela 1m sin poder demostrar el orden.

### TIME STOP

SCALP_15M_1M:
- 2 velas 15m y MFE < 0.3R -> REVIEW + Telegram.
- 4 velas 15m y MFE < 0.5R -> TIME_STOP.
- 6 velas 15m sin TP1 -> TIME_STOP máximo.

PRIMARY_1H:
- 3 velas 1H y MFE < 0.3R -> REVIEW + Telegram.
- 6 velas 1H y MFE < 0.5R -> TIME_STOP.
- 8 velas 1H sin TP1 -> TIME_STOP máximo.

TIME_STOP es tracking/gestión analítica: el Motorola NO ejecuta ni cierra órdenes reales.

### Activación

Después de actualizar y desplegar el receptor SOLV nuevo:

```sh
cd ~/solv-xrp-market-data
git pull
cd termux
bash stop_collector.sh
bash start_collector.sh
bash status_collector.sh
```


### TELEMETRÍA PASIVA 1M — SCALP

Sin cambiar el TIME STOP activo, el tracker guarda snapshots de cada SCALP en la pestaña SIGNALS a los 5, 10 y 15 minutos completos posteriores a la señal.

Por cada snapshot registra:
- MFE en R
- MAE en R
- RSI14 de 1m
- lado del cierre frente a EMA20 1m: ABOVE / BELOW / AT
- microestructura 1m simplificada: BULL / BEAR / NEUTRAL

Columnas X:AL:
MFE 5m R, MAE 5m R, RSI1m 5m, EMA20 Side 5m, Micro 5m,
MFE 10m R, MAE 10m R, RSI1m 10m, EMA20 Side 10m, Micro 10m,
MFE 15m R, MAE 15m R, RSI1m 15m, EMA20 Side 15m, Micro 15m.

Estos campos son observacionales. No disparan MICRO_REVIEW ni cierran señales. Se usarán después para comparar contrafactualmente si una regla 1m habría mejorado el Result R.
