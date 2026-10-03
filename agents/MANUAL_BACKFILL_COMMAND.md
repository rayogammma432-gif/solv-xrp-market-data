# Comando manual — Agente de Investigación

## Comando corto

`EJECUTA BACKFILL`

## Significado

Procesa hasta 20 capturas pendientes de SOLV/XRP, de la más antigua a la más reciente, siguiendo íntegramente `agents/RESEARCH_BACKFILL_AGENT_V2.md` y usando los masters autorizados `SOLV_V3_4_MASTER.txt` / `XRP_V3_4_MASTER.txt`.

La ejecución es manual. No crear ni activar tareas programadas.

## Comandos opcionales

- `EJECUTA BACKFILL 10` — procesa como máximo 10.
- `EJECUTA BACKFILL SOLV` — solo SOLV.
- `EJECUTA BACKFILL XRP` — solo XRP.
- `ESTADO BACKFILL` — solo reporta pendientes y vínculos; no genera análisis.

Las capturas ya vinculadas no se reanalizan en el backfill normal. Cualquier comparación V3.3 vs V3.4 sobre la misma captura debe usar un protocolo REPLAY/PAIRED separado.