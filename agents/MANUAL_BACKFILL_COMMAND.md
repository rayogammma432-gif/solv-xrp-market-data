# Comando manual — Agente de Investigación

## Comando corto

`EJECUTA BACKFILL`

## Significado

Sincroniza `BACKFILL_FILTER_R1` y procesa hasta 20 capturas `PRIORITY` pendientes de SOLV/XRP, de la más antigua a la más reciente, siguiendo `agents/RESEARCH_BACKFILL_AGENT_V2.md` y los masters V3.4 autorizados.

La ejecución es manual. No crear ni activar tareas programadas.

## Comandos opcionales

- `EJECUTA BACKFILL 10` — procesa como máximo 10.
- `EJECUTA BACKFILL SOLV` — solo SOLV.
- `EJECUTA BACKFILL XRP` — solo XRP dentro de PRIORITY.
- `EJECUTA BACKFILL DEFERRED 20` — procesa correlacionados diferidos, sin borrar su clasificación original.
- `EJECUTA BACKFILL ALL 20` — procesa PRIORITY+DEFERRED manteniendo hard dedup.
- `ESTADO BACKFILL` — sincroniza/lee queue+episodes y reporta; no genera análisis.

Las capturas ya vinculadas no se reanalizan en el backfill normal. Cualquier comparación V3.3 vs V3.4 sobre la misma captura debe usar un protocolo REPLAY/PAIRED separado.