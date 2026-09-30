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

The exact comparison design will be frozen only after a V3.1 research candidate clears the execution-economics gate.
