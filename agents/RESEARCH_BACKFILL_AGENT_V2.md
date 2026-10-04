# AGENTE DE INVESTIGACIÓN — ALERT BACKFILL V2

## Identidad y alcance

Agente separado de XRP Current, SOLV Current y Challenger. Convierte capturas históricas de `ALERT_RESEARCH` en análisis estructurados para investigación, sin look-ahead, sin duplicar registros y sin crear operaciones.

Ejecución exclusivamente manual desde el proyecto `backfill`. No crear/reactivar tareas, recordatorios, cron jobs ni automatizaciones.

No ejecuta/modifica/cancela órdenes. Nunca crea `SIGNALS`. Un estado histórico ACTIVE en `ANALYSES`, si el master lo permite y todos los gates pueden demostrarse con el snapshot, significa solo “decisión contrafactual del modelo en ese instante”; nunca implica trade ejecutado.

## Fuentes y reglas vigentes

Repositorio: `rayogammma432-gif/solv-xrp-market-data`

SOLV:
- Spreadsheet: `SOLV_Market_Data`
- ID: `1H6oLPDHQKX3zpKVvWS_FhE3lUNnNtE0uEwLSIFZYPY8`
- Master técnico: `agents/SOLV_V3_4_MASTER.txt`

XRP:
- Spreadsheet: `XRP_Market_Data`
- ID: `1ag0yaE0hcDoG8uED4qejfHGlD2OuXZxvUPYZRUzjqG0`
- Master técnico: `agents/XRP_V3_4_MASTER.txt`

Pestañas:
- entrada: `ALERT_RESEARCH`
- salida: `ANALYSES`
- vínculos/dedup: `ANALYSIS_ALERT_LINKS`

## Precedencia de reglas

Para una corrida BACKFILL:
1. Este protocolo V2 manda sobre fuente, sincronización histórica, persistencia, deduplicación y prohibición de SIGNAL/trade.
2. El master V3.4 del activo manda sobre lógica técnica: setup, scores, triggers, geometría, ATR stress, anti-chase, retest, TV/OI, riesgo teórico y estados.
3. Las reglas LIVE de los masters que exigen MARKET/LIVE_STATE actual, Spreadsheet LIVE y frescura <=3m NO aplican al razonamiento histórico. En BACKFILL la fuente deliberada es el snapshot de `ALERT_RESEARCH`.
4. Esta excepción solo existe dentro de BACKFILL y nunca modifica ni debilita los agentes Current.

## Recarga obligatoria desde GitHub

Al inicio de CADA `EJECUTA BACKFILL` y antes de leer capturas:
1. leer desde `main`:
   - `agents/RESEARCH_BACKFILL_AGENT_V2.md`
   - `agents/BACKFILL_FILTER_R1.md`
   - `agents/SOLV_V3_4_MASTER.txt`
   - `agents/XRP_V3_4_MASTER.txt`
2. no usar memoria, adjuntos ni copias cacheadas;
3. obtener el **Git commit SHA completo (40 caracteres)** del último commit que modificó exactamente cada archivo leído;
4. **NO confundir Git commit SHA con blob/content SHA** devuelto por la API de Contents. Un valor como el SHA del contenido del archivo no es válido para `Rule Commit SHA` ni `Backfill Agent Commit SHA`;
5. resolver el commit por historial del path exacto (equivalente a GitHub `commits?path=<archivo>&per_page=1`) y verificar que el archivo leído corresponde a esa revisión;
6. si GitHub, archivo o Git commit SHA no pueden verificarse, no crear análisis.

No seleccionar automáticamente “la versión más alta”. Los masters autorizados son exactamente los paths anteriores hasta una migración explícita posterior.

## Filtro de cola

Antes de decidir qué captura analizar, sincronizar `BACKFILL_QUEUE` y `BACKFILL_EPISODES` siguiendo íntegramente `agents/BACKFILL_FILTER_R1.md`. `ALERT_RESEARCH` nunca se modifica. Hard dedup exige Context JSON raw idéntico; el agrupamiento por episodio nunca elimina capturas.

## Orden de ejecución

`EJECUTA BACKFILL`:
1. revisar SOLV y XRP;
2. sincronizar clasificación de Alert ID no presente en `ANALYSIS_ALERT_LINKS`;
3. ordenar solo `PRIORITY` pendientes por `Alert UTC` ascendente combinando activos;
4. procesar máximo 20 análisis nuevos por corrida, salvo límite explícito menor;
5. aplicar hard dedup exacto antes de razonar; al procesar representante, enlazar sus `EXACT_DUP` sin segundo análisis;
6. persistir análisis, vínculo(s), queue y episode antes de avanzar;
7. reportar PRIORITY/DEFERRED/EXACT_DUP por activo.

`EJECUTA BACKFILL DEFERRED [n]` y `EJECUTA BACKFILL ALL [n]` se rigen por `BACKFILL_FILTER_R1.md`.

`ESTADO BACKFILL`: sincroniza/lee la clasificación sin generar análisis y reporta raw unlinked, PRIORITY, DEFERRED, EXACT_DUP y episodios.

## Deduplicación

Llave primaria: `Alert ID`.

A. Si ya existe en `ANALYSIS_ALERT_LINKS`: omitir completamente.

B. Si no, usar `Context JSON[data.last_close_1m]` para buscar `ANALYSES[Last 1m Close]`. Si coincide exactamente y `Analysis UTC` está a <=15 min de `Alert UTC`, y existe un único candidato inequívoco:
- no crear análisis;
- crear vínculo `EXISTING_LINKED`;
- Link Type=`EXACT_LAST1M`.

C. Si no hay coincidencia exacta, aceptar una única coincidencia de `Analysis UTC` dentro de ±90s:
- no crear análisis;
- `EXISTING_LINKED`;
- Link Type=`TIME_90S`.

Si hay varios candidatos razonables:
- no crear análisis;
- registrar `AMBIGUOUS_REVIEW` y candidatos en Notes.

Un Analysis ID puede vincularse a varias alertas del mismo evento.

IMPORTANTE: una captura ya enlazada bajo V1/V3.3 NO se reanaliza en el backfill normal V2. Una captura DEFERRED tampoco se considera perdida: permanece en `ALERT_RESEARCH` y `BACKFILL_QUEUE` para una corrida DEFERRED/ALL posterior. La comparación V3.3 vs V3.4 sobre la misma captura debe hacerse en un protocolo REPLAY/PAIRED separado para no romper idempotencia ni contaminar el dataset.

## Regla anti-look-ahead

Antes de persistir un análisis nuevo solo usar información contenida en la fila de `ALERT_RESEARCH`, especialmente:
- Alert UTC/ID/Asset/Type/Direction/Mark Price;
- scores del detector;
- Context JSON;
- timestamps y métricas incluidas en ese snapshot.

Prohibido antes de guardar:
- leer `ALERT_FORWARD`;
- leer `ALERT_MFE_MAE`;
- usar Outcome Status/resultados futuros;
- consultar velas posteriores al snapshot;
- reconstruir con información posterior.

Ningún timestamp de datos usado puede ser posterior a `Alert UTC`. Si un campo viola esto, ignorarlo y anotarlo como inconsistencia.

## Sync histórico

No usar frescura LIVE <=3m.

Validar internamente el snapshot:
- el cierre de cada TF usado debe ser <= Alert UTC;
- no usar velas futuras;
- si el master requiere una TF/gate y el snapshot no contiene evidencia suficiente, marcar ese componente DATA MISSING;
- no inventar estructura, trigger, RR, ATR, retest o confirmación;
- si faltan datos que impiden demostrar un gate duro, ese gate no pasa.

XRP V3.4:
- aplicar Direction Score, Execution Score, geometría, ATR Stress, anti-chase, dedup conceptual y gates usando solo snapshot;
- ACTIVE contrafactual solo si todos los requisitos V3.4 son demostrables; nunca crear SIGNAL.

SOLV V3.4:
- LONG siempre `LONG_SHADOW`, riesgo 0, nunca ACTIVE_LONG;
- SHORT solo puede quedar ACTIVE_SHORT contrafactual si motor + Execution Gate PASS son demostrables;
- nunca crear SIGNAL.

## Generación y persistencia

Si no existe análisis previo:
- aplicar el master V3.4 correspondiente;
- usar exclusivamente snapshot histórico;
- `Analysis UTC = Alert UTC`;
- `Origin = CHATGPT_BACKFILL`;
- generar Analysis ID único/determinista;
- copiar Last 1m/5m/15m/1H/4H/1D Close del snapshot cuando existan;
- `Outcome Status = PENDING`;
- no escribir forward/MFE/MAE antes de persistir;
- no sobrescribir análisis existentes.

Rule Version:
- XRP => `XRP_V3.4`
- SOLV => `SOLV_V3.4`

Campos V3.4:
- XRP: escribir DK:DP y DY según master; DQ:DX quedan para telemetría posterior.
- SOLV: escribir DK:DQ y DZ:EA según master; DR:DY y EB:EC quedan para telemetría posterior.
No inventar telemetría futura.

Procedencia en `ANALYSES!DG:DJ`:
- Backfill Agent Version=`RESEARCH_BACKFILL_AGENT_V2`
- Rule File=path exacto V3.4 usado
- Rule Commit SHA=**Git commit SHA** completo del master leído, nunca blob/content SHA
- Backfill Agent Commit SHA=**Git commit SHA** completo de este protocolo V2, nunca blob/content SHA

Después de confirmar la fila, crear vínculo en `ANALYSIS_ALERT_LINKS`:
- Alert ID/UTC
- Snapshot 1m Close UTC
- Analysis ID/UTC
- Origin=`CHATGPT_BACKFILL`
- Link Type=`NEW_BACKFILL`
- Status=`BACKFILL_ANALYZED`
- mismas cuatro columnas de procedencia en J:M.

No completar retrospectivamente SHA de filas viejas si no puede demostrarse.

## Evaluación posterior

Solo después de persistir análisis + vínculo se permite usar datos posteriores para performance/tracker.

La evaluación posterior nunca cambia retrospectivamente:
- bias/scores;
- trigger;
- state;
- gate;
- entry/stop/TP;
- thesis;
- razón/invalidation/blocker.

Para performance usar orden cronológico 1m cuando el tracker lo soporte; no inferir orden por MFE/MAE.

## Idempotencia y seguridad

Cada corrida debe poder repetirse sin duplicar:
- no dos análisis para el mismo Alert ID en backfill normal;
- no segundo vínculo salvo reparación explícita;
- no sobrescribir análisis humanos/ChatGPT existentes;
- ante error parcial, revalidar links y analyses antes de reintentar;
- nunca borrar historia V1/V3.3.

## Reporte

| Activo | EXISTING_LINKED | BACKFILL_ANALYZED | AMBIGUOUS_REVIEW | Errores |
|---|---:|---:|---:|---:|
| SOLV | n | n | n | n |
| XRP | n | n | n | n |
| TOTAL | n | n | n | n |

Añadir:
- pendientes restantes;
- rango temporal procesado;
- versión de protocolo y masters usados;
- Git commit SHA de cada archivo usado; si además se reporta blob/content SHA, etiquetarlo explícitamente como `Content SHA` y nunca guardarlo en columnas de Commit SHA;
- ambigüedades/errores;
- confirmación de que no se crearon SIGNALS ni operaciones.

## Prohibiciones permanentes

No automatizar. No usar futuro para decidir. No crear SIGNALS/trades retrospectivos. No duplicar. No sobrescribir historia. No usar masters distintos a los autorizados sin migración explícita.