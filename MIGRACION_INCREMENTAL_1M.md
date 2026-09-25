# Migración a actualización incremental cada minuto

Orden seguro:

1. En Termux:
   `cd ~/solv-xrp-market-data/termux && ./stop_collector.sh`
2. Actualiza cada Apps Script con su archivo de `apps-script/`.
3. En cada proyecto Apps Script abre **Project Settings > Script properties** y crea:
   - Property: `SHARED_SECRET`
   - Value: el mismo secreto que ya está en el `config.json` del Motorola para ese activo.
4. Guarda y actualiza el deployment Web App existente creando una nueva versión. No cambies la URL /exec.
5. En Termux:
   `cd ~/solv-xrp-market-data && git pull`
6. Regresa:
   `cd ~/solv-xrp-market-data/termux`
7. Prueba sin escribir:
   `python market_collector.py --dry-run`
8. Bootstrap real:
   `python market_collector.py`
9. Verifica en ambas hojas:
   - nueva pestaña asset_1M con ~500 velas
   - BTC_1M con ~500 velas
   - LIVE_STATE poblada
   - OI_1M poblada
   - 15m/1H/4H ahora con ~500 velas
   - MARKET Estado = OK
10. Arranca servicio:
    `./start_collector.sh`
11. Comprueba:
    `./status_collector.sh`

Después, cada minuto se escribe solo el delta. El bootstrap completo ocurre al arrancar/reiniciar el scheduler.
