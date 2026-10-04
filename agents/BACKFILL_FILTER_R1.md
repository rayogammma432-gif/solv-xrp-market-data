# BACKFILL FILTER R1 — SNAPSHOT DEDUP + RESEARCH EPISODES

## Objetivo
Reducir análisis redundantes sin borrar capturas ni alterar evidencia histórica. `ALERT_RESEARCH` es inmutable. Este filtro solo clasifica la cola de investigación.

## Salidas
Cada workbook debe tener:
- `BACKFILL_QUEUE`: clasificación por Alert ID.
- `BACKFILL_EPISODES`: resumen de episodios correlacionados.

Versión de clasificación: `BACKFILL_FILTER_R1`.

## 1. HARD DEDUP — EXACT CONTEXT
Dos alertas son duplicado exacto solo si:
- mismo Asset; y
- `Context JSON` raw es exactamente idéntico.

No deduplicar solo por cercanía temporal, mark parecido o `last_close_1m`.

Representante del grupo exacto:
1. menor Alert UTC;
2. empate => Alert ID lexicográficamente menor.

El representante puede analizarse. Los demás quedan `EXACT_DUP`.
Cuando el representante tenga Analysis ID, crear para cada duplicado un vínculo al mismo análisis:
- Link Type=`EXACT_CONTEXT`
- Status=`EXISTING_LINKED`
- Notes debe conservar que fue exact-context dedup.
Nunca crear un segundo análisis para un `EXACT_DUP`.

## 2. FAMILY
- Alert Type que empiece por `SCALP` => Family=`SCALP`.
- Cualquier otro tipo operativo actual => Family=`PRIMARY`.

## 3. RESEARCH EPISODE
Procesar no-duplicados por Asset y Alert UTC ascendente.

Iniciar episodio nuevo si ocurre cualquiera:
- Family cambia;
- Direction de la alerta cambia;
- `data.last_close_1h` cambia;
- gap desde la alerta anterior del episodio >20 minutos.

Episode ID estable:
`EP|<ASSET>|<FAMILY>|<DIR>|<LAST_1H_CLOSE>|<EPISODE_START_UTC>`

El Episode ID es una agrupación de investigación, NO una Thesis ID operativa.

## 4. PRIORITY VS DEFERRED
La primera alerta no-duplicada de cada episodio => `PRIORITY`, reason=`EPISODE_START`.

Una alerta posterior del mismo episodio => `PRIORITY`, reason=`MATERIAL_CHANGE`, si desde la última PRIORITY ocurre cualquiera:
- Alert Type cambia;
- para PRIMARY cambia TV ST 15m o TV DTR 15m;
- para SCALP cambia TV ST 5m o TV DTR 5m;
- cambia `tv.pattern.extension_warning` o su direction;
- cambia `tv.pattern.pullback_window` o su direction;
- OI 15m cambia de bucket: NEG < -0.02; FLAT [-0.02,+0.02]; POS > +0.02;
- ABS(Mark actual - Mark última PRIORITY) >= 0.50 * ATR15m de la última PRIORITY, si ATR15m válido;
- han pasado >=30 minutos desde la última PRIORITY del episodio.

Si no hay cambio material => `DEFERRED`, reason=`CORRELATED_REPEAT`.

No usar forward, outcome, MFE/MAE ni velas posteriores para clasificar.

## 5. BACKFILL_QUEUE
Columnas:
A Alert ID
B Alert UTC
C Asset
D Alert Type
E Direction
F Snapshot 1m Close UTC
G Snapshot Group ID
H Episode ID
I Queue Class
J Queue Reason
K Representative Alert ID
L Filter Version
M Processed Link Status
N Notes

Snapshot Group ID:
- para contexto único: `SNAP|<ASSET>|<LAST_1M>|<ALERT_ID>`
- para exact duplicates: usar el Alert ID representante en el último componente.

`Processed Link Status` refleja el vínculo actual cuando exista; no sustituye `ANALYSIS_ALERT_LINKS`.

## 6. BACKFILL_EPISODES
Columnas:
A Episode ID
B Asset
C Family
D Direction
E Anchor 1H Close
F First Alert UTC
G Last Alert UTC
H Priority Count
I Deferred Count
J Exact Dup Count
K Representative Alert ID
L Representative Analysis ID
M Rule Version
N Episode Status
O Notes

Episode Status:
- `OPEN`: tiene PRIORITY sin procesar;
- `PARTIAL`: alguna PRIORITY procesada y otras pendientes;
- `PRIORITY_COMPLETE`: todas las PRIORITY están vinculadas, aunque existan DEFERRED;
- `FULL_COMPLETE`: PRIORITY y DEFERRED procesadas.

## 7. COMANDOS
`EJECUTA BACKFILL [n]`:
- sincronizar clasificación de nuevos Alert ID;
- procesar solo `PRIORITY` no vinculados, en orden cronológico;
- `n` limita análisis nuevos, no vínculos EXACT_DUP;
- al procesar representante, enlazar también sus EXACT_DUP.

`EJECUTA BACKFILL DEFERRED [n]`:
- procesar DEFERRED no vinculados, oldest-first;
- no cambia ni borra su clasificación original;
- sigue aplicando hard dedup exacto.

`EJECUTA BACKFILL ALL [n]`:
- procesa PRIORITY y DEFERRED, respetando hard dedup.

`ESTADO BACKFILL` reporta por activo:
- capturas totales;
- linked;
- raw unlinked;
- PRIORITY pending;
- DEFERRED pending;
- EXACT_DUP awaiting representative/link;
- episodios abiertos/parciales/completos.

## 8. ESTADÍSTICA
No contar snapshots correlacionados como observaciones independientes por defecto.
Reportar performance en dos niveles:
1. análisis/snapshot;
2. episodios únicos y Thesis ID únicos cuando existan.

La métrica principal para inferencia comparativa debe privilegiar episodio/thesis único.

## 9. SEGURIDAD
- Nunca borrar `ALERT_RESEARCH`.
- Nunca convertir DEFERRED en pérdida de evidencia.
- Nunca crear SIGNAL/trade desde backfill.
- Nunca usar información futura para clasificación o decisión.
- Si faltan campos para detectar un cambio material, ser conservador: mantener la alerta como PRIORITY si la ambigüedad puede cambiar una decisión V3.4.
