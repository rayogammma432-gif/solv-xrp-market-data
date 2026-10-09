# XRP Multiagent Lab V1 — runbook de activación
Estado: INSTALADO (Sheets+GitHub) / NO ACTIVADO (identidades y runner)
Fecha: 2026-10-09

## Módulos
- CURRENT XRP_V3.6 queda en GitHub `main`, manifiesto `agents/XRP_MASTER_MANIFEST.json` y Sheet `XRP_Market_Data`, sin cambios.
- Laboratorio rama `lab/xrp-multiagent-v1`, su propio manifiesto en `agents/XRP_MULTIAGENT_LAB_MANIFEST_V1.json`.
- Agente A: `agents/XRP_AGENT_A_BOOTSTRAP_V1.md` + `agents/XRP_AGENT_A_MASTER_V1.md`, destino `XRP_AGENT_A_LAB`.
- Agente B: `agents/XRP_AGENT_B_BOOTSTRAP_V1.md` + `agents/XRP_AGENT_B_MASTER_V1.md`, destino `XRP_AGENT_B_LAB`.
- Evaluador: `XRP_MULTIAGENT_COMPARISON` sin permisos de producir señales.
- Ninguna de las reglas experimentales es trading validado; el único motor de salida produce SHADOW_LONG, SHADOW_SHORT, NO_TRADE o DATA_INSUFFICIENT.

## Material creado
Source READ ONLY: https://docs.google.com/spreadsheets/d/1ag0yaE0hcDoG8uED4qejfHGlD2OuXZxvUPYZRUzjqG0/edit
A: https://docs.google.com/spreadsheets/d/1e9NLM4TZLl5eZgrMdQ6eg4TRNfuKXXcqEv8gJO86lcs/edit
B: https://docs.google.com/spreadsheets/d/15egzvPYgLwdGtEMYfsiLDRZRWsRSbw-KTNQf3KUnUPU/edit
Comparación: https://docs.google.com/spreadsheets/d/1VJDdlItLry7EWKndsWLvzuwhD362In3g0KBcOJbDKrg/edit

## Provisionar (no automatizado)
1. Crear identidad CAPTURE, A_WRITER, B_WRITER, EVALUATOR distintas. Usar cuentas/servicios con alcance mínimo, credenciales guardadas fuera de GitHub. No copiar credenciales de producción ni otorgar acceso a órdenes.
2. CAPTURE: solo lector en XRP_Market_Data; no edición. A_WRITER: editor exclusivamente en el Sheet A. B_WRITER: editor exclusivamente en B. EVALUATOR: lector A/B y editor en comparación, sin edición de CURRENT. No basta compartir un OAuth de dueño de todos los documentos.
3. Validar las listas de permisos con metadatos del propietario y comprobar que cada writer NO puede leer ni modificar el origen por ausencia de acceso; no hacer escrituras de prueba en producción. Testear write y read-back solo contra archivos LAB.
4. Clonar rama `lab/xrp-multiagent-v1`, instalar dependencias `google-api-python-client google-auth` en entorno aislado (sin secretos de Binance/trading).
5. Configurar `XRP_LAB_SOURCE_CREDS` apuntando a JSON CAPTURE y `XRP_LAB_A_CREDS`, `XRP_LAB_B_CREDS` apuntando a credenciales separadas de escritores, todas locales. Marcar `XRP_LAB_IAM_APPROVED=YES` solamente al superar revisión de permisos.
6. Ejecutar en el mismo ciclo:
   ```bash
   python lab/xrp_multiagent_v1.py capture --out /secure/xlab-snapshot.json
   python lab/xrp_multiagent_v1.py run --agent A --snapshot /secure/xlab-snapshot.json
   python lab/xrp_multiagent_v1.py run --agent B --snapshot /secure/xlab-snapshot.json
   ```
   Nunca modificar el archivo de captura entre ejecuciones. Ejecutar A/B con procesos y credenciales distintas; para evaluaciones ciegas no compartir salidas entre contextos.
7. Verificar en ambos Google Sheets RUNS/DECISIONS/AUDIT; debe haber 1 run_id por agente y snapshot; confirmar READ-BACK y hash. Evaluador lee los brazos solamente después de COMPLETE, mantiene PAIR_RUNS/METRICS separados.
8. Antes de programación recurrente, añadir un lock distribuido/single-writer y pruebas de fallos parciales/reintentos. No se ha instalado scheduler; ausencia de scheduler es intencional.
9. Para agentes nativos ChatGPT, crear DOS Projects separados (no es una operación que este conector pueda realizar), pegar solo el bootstrap correspondiente en sus Project Instructions. No agregar archivos master completos ni reutilizar el Project principal.

## No hacer
- No fusionar esta rama en main sin revisión explícita.
- No ejecutar órdenes, no publicar señales operativas ni escribir en el receptor.
- No rellenar OUTCOMES con datos de futuros a la hora de decidir.
- No presentar las señales shadow como PnL, rentabilidad o superioridad.
- No iniciar un disparador horario sin credenciales aisladas, mutex y evidencia de dry run.

## Entrega y límites comprobables
Creación de 3 Sheets nativos, esquema de pestañas y prueba de AUDIT LAB_INITIALIZED verificadas.
Masters, bootstraps y protocolo en GitHub branch; principal main no se edita.
Pendiente: IAM independiente, pruebas negativas, smoke run SAME SNAPSHOT y creación de Projects ChatGPT si se desean agentes con conversaciones persistentes.
