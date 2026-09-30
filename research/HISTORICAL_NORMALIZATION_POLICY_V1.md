# Historical Normalization Policy V1 — XRP / BTC

## Propósito

Transformar archivos oficiales Binance en una capa histórica reproducible y anti-look-ahead antes de crear features o estrategias.

## Orden de precedencia

1. Contract klines 1m auditados.
2. Recuperaciones daily oficiales documentadas para gaps mensuales específicos.
3. Funding oficial.
4. Mark/index/premium oficiales como series auxiliares.
5. Metrics oficial, normalizado bajo reglas de este documento.

## Timestamps

Todo en UTC.

### Contract klines
Una barra 1m abierta en `t` solo está disponible al cierre de esa barra.

### Higher timeframes
5m/15m/1H/4H/1D se reconstruyen desde 1m.
Una barra superior solo está disponible después de su cierre completo.

### Funding
Usar último evento con timestamp <= decision_time.
No usar el funding siguiente aunque su intervalo ya haya comenzado.

### Metrics
Por precaución ante cambios de semántica del archivo:
`available_at = create_time + 5 minutes`.

Solo hacer backward as-of join por `available_at`.

## Missingness

No interpolar variables de mercado.

No usar:
- nearest join que pueda seleccionar futuro;
- backward fill desde un timestamp posterior;
- medias que incluyan intervalos ausentes como si fueran observaciones cero.

Cada feature derivada debe propagar NA cuando no tenga suficientes observaciones reales.

## Duplicados

### Idénticos
Colapsar a una fila y guardar flag de deduplicación.

### Conflictivos
Excluir esa observación de features y reportarla.

## Orden físico

Ordenar siempre por timestamp antes de cálculo.

Nunca asumir que el orden del CSV es cronológico.

## Ceros de OI

`sum_open_interest <= 0` o `sum_open_interest_value <= 0` en mercado activo:
- mantener valor raw para trazabilidad;
- marcar inválido para cambios porcentuales/log changes;
- no dividir por ese valor;
- no convertirlo en señal.

## Provenance mínima por fila normalizada

- symbol
- dataset_family
- source_file
- source_checksum_sha256
- source_granularity
- source_timestamp
- available_at
- normalization_version = HIST_NORM_V1
- recovered_from_daily (bool)
- dedup_identical (bool)
- source_zero (bool)
- source_missing_fields (bool)

## Freeze

Cualquier cambio que altere:
- timestamp de disponibilidad;
- reglas de deduplicación;
- tratamiento de gaps;
- tratamiento de ceros;
- resampling;

requiere `HIST_NORM_V2` y no puede aplicarse silenciosamente a experimentos V1 ya registrados.
