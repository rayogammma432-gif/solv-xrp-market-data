# SOLV/XRP Market Data — Fase 1

Prueba inicial de conectividad **GitHub Actions → Binance Futures**.

Esta fase:
- NO escribe en Google Sheets.
- NO usa secretos.
- NO modifica Apps Script.
- NO sustituye todavía Windows.
- Solo se ejecuta manualmente mediante `workflow_dispatch`.

## Resultado esperado

En GitHub:

1. Abre **Actions**.
2. Selecciona **Fase 1 - Probar Binance**.
3. Pulsa **Run workflow**.
4. Abre el job `test-binance`.
5. Revisa el paso **Probar endpoints de Binance Futures**.

La prueba correcta termina en verde y muestra:

```json
"all_ok": true
```

Se verifican XRPUSDT, SOLVUSDT y BTCUSDT, incluyendo velas 15m/1h/4h y los endpoints de Open Interest que necesitamos.
