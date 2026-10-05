# XRP Decision Telemetry V1

## Status
Research/shadow instrumentation only. This contract MUST NOT change XRP_V3.6 decisions, gates, thresholds, Entry/Stop/TP, thesis expiry, or state precedence.

Live sheet: `XRP_Market_Data`  
Tab: `XRP_DECISION_TELEMETRY_V1`  
Schema: `XRP_DECISION_TELEMETRY_V1`  
Write policy: append-only, one row per normal CURRENT `ANALIZA`.

## Ordering
The canonical XRP decision is computed and persisted first under the active normative authority. Telemetry is written only after that decision exists. A telemetry failure must never change, retry with different rules, or suppress the canonical decision.

Deterministic Telemetry ID:
`DT1|<Analysis ID>`

If that Telemetry ID already exists, do not append a second row. Never rewrite an older telemetry row to make historical missing data look collected.

## Missing-data semantics
- Unknown/unavailable values are blank or an explicit `UNKNOWN_*` token.
- Data that was not collected historically is `NOT_COLLECTED`, never numeric zero.
- Do not parse narrative text to fabricate structured fields.
- `Collection Status=COMPLETE` only when all fields that were actually knowable at decision time and required by this contract were persisted. Otherwise use `PARTIAL` and explain in Research Notes.

## Provenance
For every V3.6 row store:
- actual Rule Version;
- actual Model ID;
- actual Run Mode / thinking configuration;
- repository and ref;
- descriptor path/blob;
- base path/blob;
- override path/blob;
- expiry-aware tracker path/blob.

Model provenance must be factual. If the runtime cannot identify a model/configuration reliably, write `UNAVAILABLE`; never guess.

## Direction and execution criteria
Persist D1..D6 and E1..E5 separately as `YES`, `NO`, or `UNKNOWN`, plus one evidence field per criterion. Total Direction Score and Execution Score are not substitutes for the individual criteria.

For V3.6 E2 additionally persist the numerical inputs and thresholds:
- `entryAnchorDist`
- `entryAnchorDist Max` (0.50 under V3.6)
- `markEntryExtension`
- `markEntryExtension Max` (0.50 under V3.6)
- `RR_real`
- `RR Min` (1.5 under V3.6)
- first obstacle price/type

## Structural evidence
Persist the exact evidence used at decision time when available:
- Setup Type and Setup Anchor;
- Entry Zone Low/High;
- Entry, Stop, TP1, TP2;
- last confirmed Swing High/Low with their UTC timestamps;
- invalidation level/type;
- Trigger Type, Trigger Level, Trigger Close UTC;
- retest/hold UTC and level when applicable;
- 5m execution state;
- whether MICRO_1M_CONTRARIA applied;
- structured BTC state, strongly-contrary flag, structure and momentum.

Do not retrospectively reconstruct a different swing/trigger and write it as if it had been known at decision time.

## Market execution snapshot
At decision time copy the freshest research-only execution snapshot available from LIVE_STATE / `XRP_EXECUTION_MARKET_V1`:
- Mark, Index, Basis and Basis bps;
- Funding and next funding time;
- Open Interest;
- Best Bid, Best Ask, Spread and Spread bps;
- Top-5 and Top-20 bid/ask notional depth;
- depth level count and snapshot UTC.

A market snapshot older than 90 seconds must be treated as stale and the affected fields marked unavailable/partial rather than silently reused.

## Archive coverage
`XRP_ARCHIVE_HEALTH` is the authority for missing 1m intervals. Telemetry may record a contemporaneous coverage assessment, but counterfactual studies MUST recompute coverage for the exact replay interval.

If a missing interval could change entry fill, barrier ordering, expiry outcome, or another requested counterfactual result, the case result is `UNKNOWN`, not NO_FILL/STOP/TP by inference.

## Column order
The Sheet header is authoritative. It begins with Telemetry ID and Telemetry Schema Version and includes all fields described above. Producers must map by header name rather than relying on hard-coded column offsets where possible.
