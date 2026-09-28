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
El Motorola puede detectar candidatos preliminares sin consumir ejecuciones de ChatGPT:

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
