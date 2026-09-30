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

Se permite crear un nuevo periodo prospectivo independiente:

- forward_start = `2026-10-01T06:00:00Z`

Ese periodo:
- no es parte del holdout histórico;
- solo puede usar datos que se vuelvan disponibles después de forward_start;
- puede alimentar shadow research V3;
- no convierte enero-agosto 2026 en datos de entrenamiento.

## Consecuencia metodológica

Si V3 se adapta después de observar datos forward posteriores a 2026-10-01T06:00:00Z:
- esos datos dejan de ser confirmatorios para la siguiente versión;
- el holdout histórico 2026 continúa sin tocar hasta un gate explícito.

## Estado actual

- Discovery V1: complete
- Validation V2: complete
- Validated challenger: none
- 2026 historical holdout: LOCKED
- V3.1 mode: FORWARD-ONLY

## Amendment pre-launch — V3.1

Antes de observar resultados forward, el inicio se movió de `2026-10-01T00:00:00Z` a `2026-10-01T06:00:00Z` para permitir deployment y QA de captura. Las horas 00:00–05:59 UTC quedan fuera de la población V3.1 y no se recuperan retrospectivamente como eventos.

El histórico 2026-01-01 → 2026-08-31 permanece LOCKED sin cambios.
