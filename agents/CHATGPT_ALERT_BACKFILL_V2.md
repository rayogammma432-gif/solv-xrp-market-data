# ChatGPT Alert Backfill V2

> **ESTADO ACTUAL: MANUAL_ONLY / V3.4 RULES**
> La ejecución vigente se rige por `agents/RESEARCH_BACKFILL_AGENT_V2.md` y se inicia manualmente desde el proyecto `backfill`.

## Objetivo

Convertir capturas históricas de `ALERT_RESEARCH` en análisis estructurados, reproducibles y sin look-ahead, usando la lógica técnica V3.4 vigente sin crear operaciones retrospectivas.

## Reglas autorizadas

- SOLV: `agents/SOLV_V3_4_MASTER.txt`
- XRP: `agents/XRP_V3_4_MASTER.txt`
- Protocolo: `agents/RESEARCH_BACKFILL_AGENT_V2.md`

No seleccionar masters por número de versión. Solo estos paths están autorizados hasta migración explícita.

## Fuente histórica

Dentro de BACKFILL, la evidencia de decisión es exclusivamente la fila histórica de `ALERT_RESEARCH` y su `Context JSON`.
No se consulta MARKET/LIVE_STATE actual para decidir qué habría hecho el agente en ese instante.
No se permite usar información posterior antes de persistir el análisis.

Esta excepción de fuente/sync es exclusiva de BACKFILL. Los agentes Current mantienen sus reglas LIVE intactas.

## Seguridad

- No crear `SIGNALS`.
- No ejecutar/modificar/cancelar órdenes.
- No convertir un ACTIVE contrafactual en trade real.
- No reanalizar Alert ID ya vinculado en backfill normal.
- No sobrescribir historia V1/V3.3.
- Para comparar V3.3 vs V3.4 sobre la misma captura se requiere un REPLAY/PAIRED separado.

## Trazabilidad

Cada análisis nuevo guarda:
- `Backfill Agent Version = RESEARCH_BACKFILL_AGENT_V2`
- Rule File exacto
- Rule Commit SHA
- Backfill Agent Commit SHA

Las revisiones se leen de GitHub al inicio de cada corrida manual.

## Deduplicación

Se conserva la llave `Alert ID`, con respaldo por Last 1m Close y ventana temporal según el protocolo V2.

## Performance

Solo después de persistir análisis + vínculo pueden completarse resultados posteriores. La decisión histórica nunca se reescribe usando lo ocurrido después.