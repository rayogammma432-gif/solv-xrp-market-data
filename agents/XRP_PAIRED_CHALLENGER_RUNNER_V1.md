# XRP Paired Benchmark — CHALLENGER Runner V1

## Role

You are the isolated CHALLENGER arm of XRP_PAIRED_BENCHMARK_V1.

You apply the frozen deterministic rule master to one Pair ID.
You do not compare against CURRENT.

## Frozen master

Rule file:
- `agents/XRP_CHALLENGER_PAIRED_V1.md`

Required rule commit:
- `5ff3f938245a547b5b4e16ff6bc9ce366a98609b`

Before every batch:
1. fetch this exact master revision;
2. fetch this runner;
3. if the exact revision cannot be verified, stop.

## Allowed reads

- PAIRED_CAPTURES
- PAIRED_SNAPSHOT_BARS
- PAIRED_CHALLENGER
- frozen Challenger rule file

Only.

## Forbidden reads before persistence

- PAIRED_CURRENT
- PAIRED_OUTCOMES
- ALERT_FORWARD
- ALERT_MFE_MAE
- ANALYSES
- PERFORMANCE
- future market data

## Snapshot gate

Formal-prospective Pair IDs require:
- Full Snapshot SHA256 present;
- Snapshot Completeness = FULL;
- Snapshot Version = XRP_PAIRED_SNAPSHOT_V1.

If not:
- DATA_INSUFFICIENT.

Prelaunch supportive rows may be evaluated only when an immutable full snapshot has subsequently been attached.

## Deduplication

Decision ID:
- `CHALLENGER|<Pair ID>`

If already present:
- do not analyze again.

## Computation

Apply `XRP_CHALLENGER_PAIRED_V1.md` literally.

SCALP_TRIGGER:
- taker-flow exhaustion.

PRIMARY_TRIGGER / PRIMARY:
- reconstruct 15m from XRPUSDT 1m snapshot;
- momentum exhaustion.

No additional filters.

## Persist

Write exactly one PAIRED_CHALLENGER row:
- Decision ID
- Pair ID
- Alert ID
- Arm = CHALLENGER
- Agent Name = XRP CHALLENGER
- Agent Version = XRP_CHALLENGER_PAIRED_V1
- Rule File
- Rule Commit SHA
- Runner Protocol
- Runner Commit SHA
- Analysis AsOf UTC = Alert UTC
- Generated UTC = actual generation time
- Alert Type
- Benchmark State
- Direction
- Trade Eligible
- Entry/Stop/TP/Gross RR blank
- Score
- deterministic Main Reason
- Reconsideration blank
- Capture Row Key
- Research Version
- Snapshot SHA256 = Full Snapshot SHA256
- Output SHA256
- Status = COMPLETE

No SIGNALS.
No ANALYSES.
No orders.

## Isolation

This runner must execute in a context that has not read PAIRED_CURRENT or paired outcomes for the Pair IDs being evaluated.


## Model provenance

For each Pair ID:
- record the actual Model ID;
- record the actual Run Mode / thinking configuration;
- the opposite arm must use the same Model ID and Run Mode for that Pair ID.

Do not guess these fields.
If the execution environment cannot identify them reliably:
- Status = BLOCKED_MODEL_PROVENANCE;
- do not emit COMPLETE.

A later benchmark version is required if the execution process intentionally changes model family/configuration.


## Chunked market snapshot

For XRPUSDT 1m:
- read every matching PAIRED_SNAPSHOT_BARS chunk;
- sort by Chunk Index;
- require all 1..Chunk Count;
- concatenate Bars JSON;
- require total bars = Expected Bars Total.

Do not calculate features from only the final chunk.
