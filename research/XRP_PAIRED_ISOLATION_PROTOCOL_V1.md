# XRP Paired Benchmark — Isolation Protocol V1

## Estado

**PRELAUNCH PROCESS FROZEN**

## Objetivo

Preservar independencia real entre CURRENT y CHALLENGER para cada Pair ID.

## Tres contextos

### Contexto A — CURRENT

Usa exclusivamente:
- agents/XRP_PAIRED_CURRENT_RUNNER_V1.md
- rule CURRENT congelado
- PAIRED_CAPTURES
- PAIRED_SNAPSHOT_BARS
- PAIRED_CURRENT para deduplicación

No puede leer:
- PAIRED_CHALLENGER
- PAIRED_OUTCOMES
- ALERT_FORWARD
- ALERT_MFE_MAE
- resultados comparativos

### Contexto B — CHALLENGER

Usa exclusivamente:
- agents/XRP_PAIRED_CHALLENGER_RUNNER_V1.md
- Challenger congelado
- PAIRED_CAPTURES
- PAIRED_SNAPSHOT_BARS
- PAIRED_CHALLENGER para deduplicación

No puede leer:
- PAIRED_CURRENT
- PAIRED_OUTCOMES
- ALERT_FORWARD
- ALERT_MFE_MAE
- resultados comparativos

### Contexto C — Evaluación

Solo se usa después de que A y B hayan persistido COMPLETE.

Puede leer:
- ambas decisiones;
- PAIRED_OUTCOMES;
- registry/protocolos;
- modelo de costes.

No genera ni modifica decisiones de A/B.

## Batch manifest

Antes de ejecutar cualquiera de los brazos:
1. seleccionar Pair IDs por criterio temporal/Eligibility predefinido;
2. congelar la lista del batch;
3. registrar Batch ID en PAIRED_AUDIT.

No seleccionar o retirar Pair IDs por desempeño.

## Model matching

Para cada Pair ID:
- mismo Model ID en A y B;
- mismo Run Mode en A y B.

Ambos campos se escriben en la decisión.

Si no coinciden:
- provenance FAIL;
- el Pair ID no puede contribuir a un veredicto formal hasta una ejecución válida bajo el proceso preregistrado.

## Orden

Puede ejecutarse:
- CURRENT primero;
- CHALLENGER primero;
- o en paralelo.

El orden no tiene significado estadístico porque los contextos son aislados.

## Materialización de outcomes

PAIRED_OUTCOMES se construye únicamente cuando:
- CURRENT Status = COMPLETE;
- CHALLENGER Status = COMPLETE.

Por diseño, un brazo no necesita ni debe esperar el outcome para decidir.

## Contaminación

Si un contexto A/B lee información prohibida antes de persistir:
- registrar CONTAMINATED_CONTEXT en PAIRED_AUDIT;
- no ocultar el incidente;
- no reutilizar esa decisión como COMPLETE formal.

Una repetición solo es válida desde un contexto nuevo que no haya recibido la información prohibida y debe quedar auditada.

## Modelo cambia durante el benchmark

Se permite continuar V1 solamente cuando:
- para cada Pair ID ambos brazos usan el mismo modelo/configuración;
- Model ID y Run Mode se registran;
- el informe final muestra estratos por Model ID.

Si se cambia deliberadamente la metodología de prompting/runner:
- crear una nueva versión del benchmark.

## Human leakage

No copiar al contexto opuesto:
- respuesta del otro agente;
- resumen comparativo;
- resultado futuro;
- “quién va ganando”.

Los prompts de A/B deben limitarse a ejecutar su runner sobre Pair IDs congelados.

## Auditoría

Cada batch registra:
- Batch ID
- Pair IDs
- Model ID
- Run Mode
- runner commits
- fecha de inicio/fin
- incidentes de contaminación

## Gate

Este protocolo define el proceso permitido. La conformidad real de cada batch se confirma mediante PAIRED_AUDIT antes de evaluación formal.
