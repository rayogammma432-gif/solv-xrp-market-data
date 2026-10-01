# XRP Paired Benchmark — Standardized Execution Cost V1

## Estado

**FROZEN BEFORE FORMAL PAIRED BENCHMARK**

Purpose:
- compare CURRENT vs CHALLENGER under one identical normalized execution model.

This is not a claim about the user's exact Binance fee tier.

## Shared execution

For every Pair ID:

Reference entry:
- PAIRED_OUTCOMES Reference Price;
- identical for both arms.

Exit:
- close at the predeclared primary horizon:
  - SCALP_TRIGGER: 15m
  - PRIMARY_TRIGGER: 60m
  - PRIMARY: 60m

No benchmark stop/TP:
- agent-specific Entry/Stop/TP remains diagnostic;
- standardized primary PnL does not use intrabar stop/TP ordering.

## Primary standardized cost

Round-trip execution cost:
- **10 basis points per TRADE**
- equivalent to **0.10%** deducted from signed gross return.

Applied once to:
- TRADE_LONG
- TRADE_SHORT

Applied to neither:
- NO_TRADE
- DATA_INSUFFICIENT

Formula:

`net_pct = signed_gross_pct - 0.10%` for trades.

## Sensitivity

Descriptive only:
- 5 bps round trip
- 15 bps round trip

The primary superiority verdict remains:
- 10 bps.

Sensitivity scenarios cannot replace the primary result after outcomes are observed.

## Equal opportunity accounting

Primary unit:
- one capture.

NO_TRADE contributes:
- 0% return.

DATA_INSUFFICIENT contributes:
- 0% return;
- also counted separately as a quality burden.

This prevents dropping abstentions or missing decisions to inflate expectancy.

## Interpretation

A winner under this contract means:
- superior normalized decision economics on the CURRENT-detector capture universe under 10 bps standardized round-trip cost.

It does not mean:
- exact realized account PnL;
- better independent detector;
- better fill quality;
- better sizing.

Actual deployment still requires the separate XRP execution economics gate with account-specific fees/spread/slippage/latency.
