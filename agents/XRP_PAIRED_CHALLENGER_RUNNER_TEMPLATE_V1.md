# XRP Paired Benchmark — CHALLENGER Runner Template V1

## Status

**TEMPLATE ONLY — NOT A CHALLENGER MASTER**

This file defines the execution interface required for a future challenger arm.

Formal paired benchmark launch is blocked until a separate challenger rule master is created and frozen.

## Required challenger properties

The future challenger must:
- analyze XRPUSDT research-only;
- receive exactly one PAIRED_CAPTURES snapshot;
- use no future information;
- use no CURRENT decision;
- output one standardized benchmark state:
  - TRADE_LONG
  - TRADE_SHORT
  - NO_TRADE
  - DATA_INSUFFICIENT
- explicitly map SCALP_TRIGGER and PRIMARY/PRIMARY_TRIGGER captures;
- document whether Entry/Stop/TP is produced;
- never create SIGNALS or orders;
- be versioned by rule file + 40-char commit SHA.

## Allowed reads

- PAIRED_CAPTURES
- PAIRED_CHALLENGER
- frozen challenger rule file

## Forbidden reads before persistence

- PAIRED_CURRENT
- PAIRED_OUTCOMES
- ALERT_FORWARD
- ALERT_MFE_MAE
- ANALYSES decisions
- future market data

## Decision ID

- `CHALLENGER|<Pair ID>`

## Independence requirement

The CHALLENGER arm must run in an isolated conversation/context from the CURRENT arm.

## Critical restriction

Do not create the challenger by inspecting paired benchmark outcomes.

Historical research already completed outside the paired benchmark may be used, but the benchmark itself cannot become training data for the same version being evaluated.
