# Comando manual — Agente de Investigación

## Comando corto

`EJECUTA BACKFILL`

## Significado

Procesa hasta 20 capturas pendientes de SOLV/XRP, de la más antigua a la más reciente, siguiendo íntegramente `agents/RESEARCH_BACKFILL_AGENT_V1.md`.

La ejecución es manual. No crear ni activar tareas programadas.

## Comandos opcionales

- `EJECUTA BACKFILL 10` — procesa como máximo 10.
- `EJECUTA BACKFILL SOLV` — solo SOLV.
- `EJECUTA BACKFILL XRP` — solo XRP.
- `ESTADO BACKFILL` — solo reporta pendientes y vínculos; no genera análisis.
