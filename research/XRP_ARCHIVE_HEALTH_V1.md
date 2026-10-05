# XRP Archive Health V1

## Status
Research-only coverage ledger for `XRP_Research_Archive`.

Tab: `XRP_ARCHIVE_HEALTH`  
Schema: `XRP_ARCHIVE_HEALTH_V1`  
Policy: append-only provenance ledger.

## Scope
The strict 60-second cadence rule applies to:
- `XRP_1M_ARCHIVE`
- `BTC_1M_ARCHIVE`

OI sampling has different historical cadence and is not declared complete by this contract.

## Gap definition
For consecutive present 1m timestamps A and B, when B-A > 60 seconds:
- Gap Start UTC = A + 60 seconds
- Gap End UTC = B - 60 seconds
- Missing Minutes = (B-A)/60 - 1

Each stream gets its own health row even when XRP and BTC share the same gap.

Deterministic Health ID:
`AHV1|<STREAM>|<COMPACT_GAP_START_UTC>|<MISSING_MINUTES>`

## Status
- `OPEN`: original archive is missing the interval and no recovery has been accepted.
- `RECOVERED`: data was recovered from an explicit source with provenance.
- `INVALIDATED`: a purported recovery was rejected; original gap remains scientifically relevant.

Never overwrite an OPEN row to hide that a gap existed. Recovery is recorded with Recovery Source, Recovery Provenance and Recovered UTC.

## Replay coverage
Every counterfactual/replay defines an evidence interval. Intersect that interval with all OPEN/INVALIDATED gaps for all required streams.

Return:
- `COVERAGE_COMPLETE=YES` only if no relevant gap intersects the evidence interval;
- `COVERAGE_COMPLETE=NO` when a relevant gap intersects and cannot affect the requested outcome only if that irrelevance is mathematically provable;
- `COVERAGE_COMPLETE=UNKNOWN` when a gap could change fill, barrier order, expiry, or the requested metric.

The default in any ambiguous case is UNKNOWN.

## Prospective detection
The receptor may detect new gaps while appending archive rows. Detection is best-effort research telemetry and MUST NOT interrupt the operational XRP feed.
