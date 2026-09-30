# ChatGPT Alert Backfill V1

> **ESTADO ACTUAL: MANUAL_ONLY**  
> La automatización horaria fue desactivada. Este documento conserva la lógica base, pero la ejecución vigente se rige por `agents/RESEARCH_BACKFILL_AGENT_V1.md` y debe iniciarse manualmente desde el proyecto de investigación. No crear ni reactivar una tarea horaria.

## Objetivo

Convertir cada captura de `ALERT_RESEARCH` de SOLV y XRP en un análisis estructurado de ChatGPT sin duplicar análisis existentes y sin introducir look-ahead bias.

## Fuentes

- SOLV: `SOLV_Market_Data`
- XRP: `XRP_Market_Data`
- Capturas: `ALERT_RESEARCH`
- Análisis: `ANALYSES`
- Vínculos: `ANALYSIS_ALERT_LINKS`
- Reglas: `agents/SOLV_V3_3_MASTER.txt` y `agents/XRP_V3_3_MASTER.txt`

## Llave de deduplicación

La llave primaria del evento es `Alert ID`.

Antes de crear un análisis:
1. Si `Alert ID` ya existe en `ANALYSIS_ALERT_LINKS`, no analizar de nuevo.
2. Buscar análisis existente cuyo `Last 1m Close` coincida exactamente con `Context JSON[data.last_close_1m]` y cuya hora esté a <= 15 minutos de `Alert UTC`.
3. Si no existe coincidencia exacta, aceptar una única coincidencia de `Analysis UTC` dentro de +/-90 segundos.
4. Si existe más de un candidato ambiguo, no crear un duplicado: registrar/revisar como ambiguo.

Un mismo `Analysis ID` puede enlazarse a más de un `Alert ID` cuando varias alertas pertenecen al mismo evento analítico.

## Backfill

Si no existe análisis previo:
- Analizar exclusivamente los datos presentes en la fila de `ALERT_RESEARCH`, especialmente `Context JSON`.
- No leer `ALERT_FORWARD`, `ALERT_MFE_MAE`, resultados posteriores ni velas futuras antes de guardar el razonamiento.
- Guardar en `ANALYSES` con `Origin = CHATGPT_BACKFILL`.
- Usar `Analysis UTC = Alert UTC` para que el tracker de performance mida desde el evento histórico.
- Mantener `ANALYSES` como investigación. Un backfill nunca crea retrospectivamente una operación ni una señal.
- Registrar el vínculo en `ANALYSIS_ALERT_LINKS` con `Link Type = NEW_BACKFILL`.

Después de guardar el análisis, los procesos de performance pueden completar AF:AR usando datos posteriores.

## Análisis en tiempo real

Los análisis existentes con `Origin = CHATGPT_ANALIZA` se preservan. Los de `MANUAL_ANALIZA` también se preservan y pueden servir como análisis existente cuando coinciden inequívocamente con una captura.

## Estados de vínculo

- `EXISTING_LINKED`: captura enlazada a un análisis ya existente.
- `BACKFILL_ANALYZED`: ChatGPT creó un análisis histórico nuevo.
- `AMBIGUOUS_REVIEW`: hay varios candidatos y no se generó duplicado.
- `ERROR_RETRY`: fallo transitorio; puede reintentarse sin duplicar porque la llave es `Alert ID`.

## Seguridad de investigación

No ejecutar, modificar ni cancelar órdenes. No crear `SIGNALS` desde backfill. No convertir retrospectivamente `CONDICIONAL`, `NO_OPERAR` o estudios SHADOW en trades.
