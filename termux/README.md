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
