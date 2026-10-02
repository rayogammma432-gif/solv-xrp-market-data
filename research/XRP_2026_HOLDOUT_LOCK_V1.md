# XRP 2026 Historical Holdout Lock V1

## Estado

**LOCKED / DO NOT OPEN**

Fecha de lock:
- 2026-09-30 UTC

Activo:
- XRPUSDT

Holdout histórico protegido:
- 2026-01-01 00:00 UTC → 2026-08-31 23:59 UTC

## Propósito

Preservar un bloque histórico completamente no utilizado después de:
- Discovery V1 sobre 2020-2023;
- Validation V2 sobre 2024-2025.

Este holdout NO se usa para:
- generar hipótesis;
- ajustar thresholds;
- escoger features;
- elegir horizontes;
- estimar costes;
- comparar configuraciones;
- depurar reglas;
- seleccionar un challenger.

## Regla

Ningún experimento adaptativo V3 puede leer outcomes, forward returns, MFE/MAE o resultados derivados de decision rows cuyo decision_time esté dentro del holdout histórico 2026.

Tampoco se permite usar indirectamente:
- tablas/resúmenes construidos a partir de esos outcomes;
- charts;
- estadísticas agregadas;
- resultados de un workflow previo que haya evaluado hipótesis V3 sobre ese rango.

## Excepción

Abrir este holdout requiere un gate separado y explícito después de que exista una especificación challenger completamente congelada.

Mientras V3 sea forward-only:
- el holdout permanece intacto.

## Forward data permitido

La única cohorte prospectiva confirmatoria activa es V3.2:

- protocol = `XRP_FORWARD_V3_2`
- forward_start = `2026-10-02T12:00:00Z`

Ese periodo:
- no es parte del holdout histórico;
- solo puede usar decisiones en o después del forward_start congelado;
- puede alimentar shadow research V3.2 bajo sus reglas preregistradas;
- no convierte enero-agosto 2026 en datos de entrenamiento;
- no incorpora la ventana abortada V3.1 como evidencia prospectiva.

## Consecuencia metodológica

Si V3.2 se adapta después de observar datos forward posteriores a 2026-10-02T12:00:00Z:
- esos datos dejan de ser confirmatorios para la siguiente versión;
- el holdout histórico 2026 continúa sin tocar hasta un gate explícito.

## Estado actual

- Discovery V1: complete
- Validation V2: complete
- Validated challenger: none
- 2026 historical holdout: LOCKED
- V3.1: ABORTED PRELAUNCH / NO VALID FORMAL COLLECTION
- V3.2: FROZEN FORWARD-ONLY / NOT YET ACTIVATED

## Amendment pre-launch — V3.1

Antes de observar resultados forward, el inicio se movió de `2026-10-01T00:00:00Z` a `2026-10-01T06:00:00Z` para permitir deployment y QA de captura. Las horas 00:00–05:59 UTC quedan fuera de la población V3.1 y no se recuperan retrospectivamente como eventos.

El histórico 2026-01-01 → 2026-08-31 permanece LOCKED sin cambios.


## Amendment pre-launch — V3.2

El intento V3.1 no alcanzó activation/runtime-ready válido antes de su start y fue clasificado como **ABORTED PRELAUNCH / NO VALID FORMAL COLLECTION**. No existen filas V3.1 aceptadas en CHALLENGER_CANDIDATES, CHALLENGER_OUTCOMES o CHALLENGER_HEALTH.

Antes de observar resultados V3.2, el relanzamiento se congeló para:

- `2026-10-02T12:00:00Z`
- `2026-10-02 06:00:00 America/Guatemala`

Las reglas científicas permanecen sin cambios respecto de V3.1. Las modificaciones V3.2 son de captura, deployment, runtime, provenance y evaluación preregistrada.

El histórico 2026-01-01 → 2026-08-31 continúa **LOCKED / DO NOT OPEN**.
