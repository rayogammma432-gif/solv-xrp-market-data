# Recolector Termux incremental — SOLV/XRP/BTC

Versión 2: actualización cada minuto con escritura incremental.

## Comportamiento
- Al arrancar: bootstrap de 500 velas cerradas para SOLV/XRP/BTC en 1m/5m/15m/1h/4h/1d.
- Cada minuto: nueva vela 1m + MARKET + OI actual + LIVE_STATE.
- En cierres 5m: añade la serie 5m del activo y BTC_5M.
- En cierres 1D: añade la nueva vela diaria del activo y BTC_1D.
- En cierres 15m: añade nueva 15m y actualiza OI_HISTORY.
- En cierres 1H: añade nueva 1H.
- En cierres 4H: añade nueva 4H.
- OI_1M es muestreo local del endpoint de OI actual; no es histórico oficial de Binance a 1m.

## Seguridad
`config.json` contiene URLs /exec y Shared Secrets. Nunca se sube a GitHub.

El receptor XRP CURRENT aplica allowlist a `payload.sheets`:
- bootstrap: únicamente XRP/BTC 1m, 5m, 15m, 1H, 4H y 1D;
- incremental: las mismas series + ALERT_RESEARCH, ALERT_FORWARD y ALERT_MFE_MAE.

La ruta genérica no puede escribir SIGNALS, ANALYSES, USER_TRADES, PERFORMANCE ni PAIRED_*.
CURRENT y Challenger deben usar URLs /exec y secretos distintos.

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


## SIGNALS / PERFORMANCE — SOLV / XRP V3.4

XRP V3.4 reutiliza esta misma infraestructura. V3.3 está retirado del runtime activo y preservado bajo `archive/xrp-v3.3/` + branch `archive/xrp-v3.3-final`.

Para XRP V3.4, el receptor operativo continúa siendo `apps-script/XRP_Receptor_Incremental.gs`; al activar, se actualiza la versión del Web App existente para conservar la misma URL /exec.

Google Sheet incluye:
- `SIGNALS`: una fila por señal ACTIVA emitida por el agente.
- `PERFORMANCE`: KPIs, R acumulado, drawdown, desglose por motor/dirección y gráfico.

El agente debe registrar solo LONG/SHORT ACTIVOS, nunca CONDICIONAL o NO OPERAR.

Columnas SIGNALS A:AQ:
- A:W conserva el contrato histórico de señal/tracking;
- X:AL contiene telemetría pasiva 5/10/15m;
- AM Thesis ID;
- AN Rule Version;
- AO Direction Score;
- AP Execution Score;
- AQ Execution Gate.

Toda señal V3.4 debe escribir AM:AQ.

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

Después de actualizar y desplegar el receptor CURRENT correspondiente:

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


## ANALYSES + ALERTS — RESEARCH

Para no limitar el aprendizaje solo a señales activas:

- `ANALYSES`: registra CADA ejecución de `ANALIZA SOLV AHORA`, incluyendo NO_OPERAR, CONDICIONAL, ACTIVE_LONG, ACTIVE_SHORT y DATA_INSUFFICIENT.
- `ALERTS`: registra automáticamente cada alerta Telegram enviada por el Motorola.
- `SIGNALS`: sigue reservado solo para señales ACTIVAS. No mezclar estas bases.

El Motorola hace shadow tracking de cada fila de ANALYSES desde el Mark Price del análisis y completa:
- retorno forward a 5m, 15m, 30m, 60m y 240m
- MFE/MAE porcentual a 15m, 60m y 240m
- Outcome Status PENDING/PARTIAL/COMPLETE

Estos resultados NO son trades ni performance real. Sirven para investigación de reglas, falsos negativos, filtros demasiado estrictos y patrones posteriores a alertas.

El receptor SOLV devuelve al Motorola hasta 500 análisis no completos para seguimiento. Las alertas Telegram se ponen en cola local y se escriben en ALERTS en el siguiente POST exitoso.


## XRP Challenger V3.2 R2 — lanzamiento prospectivo

R1 perdió su start y está cerrado sin evidencia prospectiva. No se backfillea.

R2 congelado:
- protocolo: `XRP_FORWARD_V3_2_R2`
- start: `2026-10-05T00:00:00Z`
- Guatemala: `2026-10-04 18:00:00`
- cutoff de readiness: `2026-10-04T23:30:00Z` / `17:30 Guatemala`
- runbook: `research/XRP_CHALLENGER_DEPLOYMENT_GATE_V4.md`

Secuencia en Motorola, después de mergear el commit validado y desplegar una nueva versión del Apps Script Challenger:

```sh
cd ~/solv-xrp-market-data
git pull
cd termux

bash stop_challenger_collector.sh
python challenger_deployment_gate.py --reset-local-prelaunch
python challenger_deployment_gate.py
python challenger_deployment_gate.py --write-activation
bash start_challenger_collector.sh
bash status_challenger_collector.sh
```

No continuar si el gate no devuelve `PASS_DEPLOYMENT_GATE` o si start/status no muestran `RUNNING_READY`.
Si no se completa antes del cutoff, R2 también se abandona; nunca se rellena retrospectivamente.
