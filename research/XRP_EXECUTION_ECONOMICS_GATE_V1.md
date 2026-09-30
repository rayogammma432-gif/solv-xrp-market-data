# XRP Forward Research — Execution Economics Gate V1

## Purpose

A statistical Forward PASS is not a trading approval.

Any candidate that passes XRP_FORWARD_V3_1 must enter a separate execution study before operational comparison or capital deployment.

## Required execution inputs

The execution model must preregister:
- Binance fee tier / maker-taker assumptions;
- bid/ask spread source;
- slippage rule by side and liquidity;
- signal-to-order latency;
- fill probability / partial fill handling;
- order type;
- sizing and leverage;
- stop/TP logic if introduced;
- liquidation/funding treatment where relevant.

## Required outputs

For every candidate:
- gross signed return;
- estimated round-trip fees;
- spread cost;
- slippage cost;
- latency cost;
- net return;
- distribution of net expectancy;
- tail loss;
- turnover;
- capacity/liquidity diagnostics.

## Gate

A candidate cannot be called an executable strategy merely because:
- CI is positive;
- Holm passes;
- gross effect exceeds the research floor.

It must demonstrate positive net expectancy under frozen execution assumptions and then survive shadow execution.

No execution parameter may be tuned on the same forward sample and described as confirmatory.
