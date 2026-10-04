# SOLV Forward V3.4 R1 — Preregistration

Protocol ID: `SOLV_FORWARD_V3_4_R1`  
State: `PRELAUNCH_FROZEN`

## Formal time boundary

Start:
- UTC: `2026-10-05T06:00:00Z`
- America/Guatemala: `2026-10-05 00:00:00`

Readiness cutoff:
- UTC: `2026-10-05T05:30:00Z`
- America/Guatemala: `2026-10-04 23:30:00`

If readiness is not complete before the cutoff, this start is abandoned. No later backfill may be labeled prospective R1 evidence. A new future start and protocol revision must be frozen.

## Scientific lock

R1 does not change the scientific hypotheses already defined in `research/SOLV_V3_4_FORWARD_PROTOCOL.md`.

Frozen rules:
- rule: `SOLV_V3.4`;
- LONG: `LONG_SHADOW`, research only, 0% risk, never ACTIVE/SIGNAL;
- SHORT: `SHORT_EXPERIMENTAL`, only ACTIVE when the existing Execution Gate passes;
- production TP remains unchanged;
- `SOLV_TP1_1R_R1` remains shadow only;
- Thesis ID deduplication and expiry remain mandatory;
- chronological closed 1m candles determine fill/barrier order;
- ambiguous same-1m outcomes remain AMBIGUOUS.

No threshold, direction, setup, risk or target is being optimized at launch.

## Frozen source identities

- master blob: `af85c1ecc697dcd1a7f0ac6359094e63642b8ecf`
- receptor blob: `8b31939253e1aa22ec1340520c8ef2f7460bb157`
- receptor version: `SOLV_RECEPTOR_V3_4_V2`
- collector blob: `fafad1bc1315cae19e08df1bc257fa6f8172aa62`
- analysis tracker blob: `059c50122987c399bc3d43eceb615246146ccafe`
- signal tracker blob: `f4117f5cf38adcccc20132e3139196cd8ae9d1ff`
- schema: `SOLV_V3_4_SCHEMA_EC_AQ_V1`
- spreadsheet: `1H6oLPDHQKX3zpKVvWS_FhE3lUNnNtE0uEwLSIFZYPY8`

A deployment that does not match these identities is not R1.

## Pre-start exclusions

The following are explicitly excluded from confirmatory R1 evidence:
- all BACKFILL rows regardless of Rule Version;
- every observation before the formal start;
- `SOLV-20261003T231611Z-AN`, classified as PRELAUNCH_SMOKE;
- historical V3.3 rows;
- manually reconstructed or copied rows;
- any row generated while receptor identity/readiness is unverified.

Pre-start material may be used only as historical context or operational smoke evidence.

## Eligible R1 observations

For an ANALYSES row to enter the confirmatory sample:
1. Analysis UTC >= formal start.
2. Rule Version = `SOLV_V3.4`.
3. Analysis ID does not contain `BACKFILL`.
4. Live deployment passed the R1 readiness boundary before cutoff.
5. The row has valid live provenance and was not manually reconstructed.
6. Geometry/outcome telemetry is recorded by the existing tracker rather than invented retrospectively.

For statistical counting:
- unique Thesis ID is the primary unit;
- repeated analyses of the same Thesis ID are correlated observations;
- LONG and SHORT are reported separately;
- PRIMARY and SCALP are reported separately;
- production TP and shadow 1R are reported separately.

## Primary metrics

Per unique thesis:
- fill / no-fill;
- first barrier chronologically;
- realized R;
- minutes to fill;
- minutes in trade;
- production outcome;
- shadow 1R first barrier and R;
- execution blocker;
- direction;
- motor;
- ambiguity rate;
- missing/invalid telemetry rate.

Aggregate review must include expectancy, win/loss distribution, drawdown, profit factor where meaningful, and execution costs where available.

## Stopping / promotion boundary

No permanent promotion is permitted from a small winning streak.

Target review window:
- 50–100 unique prospective setups, unless a separately preregistered stopping rule supersedes it.

LONG remains shadow until an explicit prospective review promotes it.

The 1R shadow target cannot replace production TP solely because historical/backfill performance is better.

SHORT risk may be reduced or disabled if prospective evidence shows persistent negative expectancy or operational defects.

## Integrity rule

R1 is a prospective experiment, not a backfill label. Missing prospective evidence is missing evidence. It is never recreated after the fact.
