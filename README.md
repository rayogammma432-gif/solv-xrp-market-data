# SOLV / XRP Market Data & Research

Repositorio operativo para captura de mercado, análisis de agentes, tracking, backfill y experimentos prospectivos de SOLV/XRP.

## Estado autoritativo

La matriz viva de estado está en:

- `research/XRP_SYSTEM_STATUS.md`

No usar este README como sustituto de los protocolos congelados de cada experimento.

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
