# XRP Challenger vs CURRENT Comparison Contract V1

## Status

**DESIGN CONSTRAINT — NO COMPARISON YET**

A future comparison must be preregistered before reading comparative performance.

Raw win-rate comparison between different opportunity populations is forbidden.

## Permitted designs

### Paired comparison

Use the same decision timestamps/events for both systems.

Report:
- both decisions;
- disagreement rate;
- paired forward/net outcome difference;
- block-bootstrap CI of the paired difference.

### Portfolio comparison

Each system may select its own opportunities, but both must use:
- same evaluation calendar;
- same starting capital;
- same risk budget;
- same leverage constraints;
- same fee/slippage/latency model;
- same mark-to-market convention.

Report:
- net return;
- drawdown;
- volatility;
- turnover;
- exposure;
- event count;
- tail losses.

## Prohibited shortcut

Do not conclude that one agent is better solely because it has:
- higher win rate;
- higher average return per selected event;
- more signals;

when the populations, risk or costs differ.

## Two comparison layers

A **paired decision-quality benchmark** may be frozen and run prospectively before a Forward candidate clears the execution-economics gate, provided it:
- uses the same frozen captures for both arms;
- remains isolated from paired outcomes before each decision;
- uses a normalized common cost only as a benchmark convention;
- makes no claim of account-level deployability or independent opportunity discovery.

That research benchmark is defined by `XRP_PAIRED_BENCHMARK_PROTOCOL_V1.md`.

An **operational/economic comparison for deployment** remains blocked until a Forward research candidate clears the separate execution-economics gate. Only that later comparison may support claims about executable strategy economics.

Thus the paired benchmark does not supersede the execution-economics requirement; it answers a narrower question about decision quality on a common opportunity universe.
