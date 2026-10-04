# SOLV / XRP Market Data & Research

Repositorio operativo para captura de mercado, análisis de agentes, tracking, backfill y experimentos prospectivos de SOLV/XRP.

## Estado autoritativo

Las matrices vivas de estado están en:

- `research/XRP_SYSTEM_STATUS.md`
- `research/SOLV_SYSTEM_STATUS.md`

No usar este README como sustituto de los protocolos congelados de cada experimento.

## SOLV CURRENT

Runtime activo:
- bootstrap de instrucciones de proyecto: `agents/SOLV_PROJECT_BOOTSTRAP.txt`
- manifest autoritativo: `agents/SOLV_MASTER_MANIFEST.json`
- regla completa: `agents/SOLV_V3_4_MASTER.txt`
- receptor fuente: `apps-script/SOLV_Receptor_Incremental.gs`
- receptor objetivo: `SOLV_RECEPTOR_V3_4_V2`
- collector: `termux/market_collector.py`
- spreadsheet: `SOLV_Market_Data`
- schema: SIGNALS A:AQ / ANALYSES A:EC

Las instrucciones pegadas en el Project no deben contener una copia compactada del master. Deben usar únicamente el bootstrap corto, que carga manifest + status + master + protocolo desde GitHub y falla cerrado si no puede verificar identidad/versiones. CI comprueba que el bootstrap siga por debajo de 8.000 caracteres y que el blob declarado en el manifest coincida con el master real.

El receptor SOLV endurecido acepta por la ruta genérica `payload.sheets` solo tabs explícitamente permitidas de ingestión. SIGNALS, ANALYSES, USER_TRADES, PERFORMANCE y BACKFILL_* no son destinos válidos de esa ruta.

El forward confirmatorio congelado es `SOLV_FORWARD_V3_4_R1`: start `2026-10-05T06:00:00Z`, cutoff de readiness `2026-10-05T05:30:00Z`. Todo BACKFILL y todo dato pre-start queda fuera de la muestra confirmatoria.

## XRP CURRENT

Runtime activo:

- regla: `agents/XRP_V3_4_MASTER.txt`
- receptor: `apps-script/XRP_Receptor_Incremental.gs`
- collector: `termux/market_collector.py`
- spreadsheet: `XRP_Market_Data`
- schema: SIGNALS A:AQ / ANALYSES A:DY
- V3.3: histórico únicamente, preservado en `archive/xrp-v3.3/` y branch `archive/xrp-v3.3-final`

El receptor CURRENT acepta por la ruta genérica `payload.sheets` solamente tabs explícitamente permitidas de ingestión. SIGNALS, ANALYSES, USER_TRADES, PERFORMANCE y PAIRED_* no son destinos válidos de esa ruta.

## Challenger prospectivo

V3.2 R1 perdió su start formal y está cerrado como:

`ABORTED_PRELAUNCH_NO_PROSPECTIVE_EVIDENCE`

La siguiente congelación es:

- protocolo: `XRP_FORWARD_V3_2_R2`
- start formal: `2026-10-05T00:00:00Z`
- Guatemala: `2026-10-04 18:00:00`
- cutoff mínimo de readiness: `2026-10-04T23:30:00Z`
- storage independiente: `XRP_Challenger_Research`
- gate: `research/XRP_CHALLENGER_DEPLOYMENT_GATE_V4.md`

R2 sigue siendo shadow research: no crea SIGNALS, órdenes ni operaciones.

## Backfill

Backfill es un proceso manual y separado de CURRENT.

Archivos autoritativos:

- `agents/RESEARCH_BACKFILL_AGENT_V2.md`
- `agents/BACKFILL_FILTER_R1.md`
- masters V3.4 del activo

Nunca usar backfill para crear trades retrospectivos ni rellenar evidencia prospectiva perdida.

## Paired benchmark

El benchmark V1 conserva su baseline congelado V3.3 y no debe mutarse para seguir CURRENT. Una comparación formal V3.4 vs Challenger requiere un benchmark/version nuevo.

## Termux

Ver `termux/README.md` para instalación, servicio 24/7, seguridad y lanzamiento Challenger.

## Seguridad

- `termux/config.json` contiene URLs /exec y secretos y está ignorado por Git.
- CURRENT y Challenger usan receptores, storage y secretos separados.
- No subir tokens de Telegram, Shared Secrets, activaciones locales ni runtime state.
- Cambios de reglas o de contratos prospectivos requieren nueva versión y start futuro.
