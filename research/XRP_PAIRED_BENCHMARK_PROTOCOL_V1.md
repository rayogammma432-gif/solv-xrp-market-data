# XRP Paired Benchmark Protocol V1

## Estado

**PRELAUNCH DESIGN — FORMAL LAUNCH BLOCKED UNTIL CHALLENGER MASTER IS FROZEN**

Asset:
- XRPUSDT

Spreadsheet:
- XRP_Market_Data
- `1ag0yaE0hcDoG8uED4qejfHGlD2OuXZxvUPYZRUzjqG0`

## Question answered

This benchmark answers:

> Given the exact same detector capture, which analysis agent makes the better decision?

It does **not** answer:
- which full system discovers better opportunities across the entire market;
- which detector is better;
- whether a statistically better decision engine is executable after costs.

Those questions remain separate from XRP_FORWARD_V3_1 and the execution-economics gate.

## Pair unit

Primary key:
- `Pair ID = Alert ID`

Universe:
- rows from `ALERT_RESEARCH` only;
- Telegram-sent research captures only;
- each Pair ID appears once in the capture table.

The exact snapshot is frozen before either arm is evaluated.

For formal prospective pairs the frozen snapshot includes:
- the 11-field ALERT_RESEARCH record;
- XRPUSDT and BTCUSDT bars for 1m/5m/15m/1h/4h/1d;
- 360 XRPUSDT 1m bars;
- 250 bars for each other logical symbol/timeframe series;
- each logical series split into chunks of at most 180 bars;
- chunk SHA256 values;
- exactly 12 logical series;
- one Full Snapshot SHA256 covering the research row + every chunk hash.

Formal pairs require `Snapshot Completeness = FULL`.
A bar with close_time after Alert UTC is forbidden.

## Storage

### PAIRED_CAPTURES
One immutable snapshot per Pair ID.

### PAIRED_CURRENT
One CURRENT-arm decision per Pair ID.

### PAIRED_CHALLENGER
One CHALLENGER-arm decision per Pair ID.

### PAIRED_OUTCOMES
One shared, direction-neutral market outcome per Pair ID.

### PAIRED_AUDIT
Append-only provenance / validation log.

Operational `ANALYSES` is not used as the benchmark decision table.

## Why ANALYSES is not reused

Existing analyses can have:
- different rule versions;
- different generation times;
- live vs backfill origins;
- shared-event links across multiple Alert IDs.

The benchmark therefore **replays each arm from the frozen capture** under one fixed rule commit.

This prevents a moving-target comparison.

## Independent arms

Formal comparison requires two isolated executions.

CURRENT runner:
- reads PAIRED_CAPTURES and PAIRED_SNAPSHOT_BARS;
- reads frozen CURRENT rule file;
- reads only PAIRED_CURRENT for deduplication;
- must not read PAIRED_CHALLENGER;
- must not read PAIRED_OUTCOMES;
- must not read ALERT_FORWARD / ALERT_MFE_MAE;
- must not reuse an existing ANALYSES decision as its benchmark answer.

CHALLENGER runner:
- reads PAIRED_CAPTURES and PAIRED_SNAPSHOT_BARS;
- reads frozen CHALLENGER rule file;
- reads only PAIRED_CHALLENGER for deduplication;
- must not read PAIRED_CURRENT;
- must not read PAIRED_OUTCOMES;
- must not read ALERT_FORWARD / ALERT_MFE_MAE;
- must not use CURRENT output as input or rationale.

The two arms should be run in separate ChatGPT conversations / isolated execution contexts.

Running both arms sequentially in one context is **not** considered blinded paired evaluation.

## Frozen CURRENT baseline

Current baseline intended for V1:
- rule file: `agents/XRP_V3_3_MASTER.txt`
- rule commit SHA: `b6f62ed220226a10f653c45c5c3680320a0dd7fd`

Operational XRP rules may evolve later.
The paired benchmark V1 baseline does not silently follow later commits.

Any baseline rule change creates a new benchmark version.

## CHALLENGER requirement

Formal launch requires:
The frozen research challenger is:
- rule file: `agents/XRP_CHALLENGER_PAIRED_V1.md`
- rule commit: `5ff3f938245a547b5b4e16ff6bc9ce366a98609b`

It was derived only from pre-existing V2/V3.1 research and frozen before paired outcomes were opened.

XRP_FORWARD_V3_1 itself is not the paired agent. The paired Challenger uses only the direct, preregistered signal components that can be interpreted without inventing an OI trading rule.

## Standardized benchmark decision

For each Pair ID each arm emits exactly one:

- `TRADE_LONG`
- `TRADE_SHORT`
- `NO_TRADE`
- `DATA_INSUFFICIENT`

Additional agent-native fields may be stored:
- setup;
- score;
- entry;
- stop;
- TP1;
- TP2;
- gross RR;
- reason;
- reconsideration.

### Relevant module mapping

For `SCALP_TRIGGER` captures:
- benchmark the agent's operational SCALP decision.

For `PRIMARY_TRIGGER` and `PRIMARY` captures:
- benchmark the agent's PRIMARY decision.

A trade exists only when the relevant module is actually ACTIVE.

CONDICIONAL / NO_OPERAR:
- benchmark state = NO_TRADE.

DATA_INSUFFICIENT:
- benchmark state = DATA_INSUFFICIENT;
- standardized PnL contribution = 0;
- counted separately as missing-decision burden.

## Shared reference price

Reference price:
- `Context JSON["market.mark_price"]`
- same field used by the existing alert-outcome tracker.

No arm may substitute its own reference price for the standardized decision-quality benchmark.

Agent-specific entry/stop/TP is retained only for later execution-model research.

## Shared outcome reconstruction

Existing `ALERT_FORWARD` stores returns signed in the **detector direction**.

Existing `ALERT_MFE_MAE` stores excursions in the detector direction.

The paired benchmark first reconstructs direction-neutral market outcomes.

Let:
- d = +1 if Detector Direction = LONG
- d = -1 if Detector Direction = SHORT
- F_dir(h) = ALERT_FORWARD directional percent return.

Then:
- `raw_forward_pct(h) = d * F_dir(h)`

For excursions:

If detector direction = LONG:
- raw_up_pct(h) = MFE(h)
- raw_down_pct(h) = -MAE(h)

If detector direction = SHORT:
- raw_up_pct(h) = MAE(h)
- raw_down_pct(h) = -MFE(h)

No agent direction is used while building PAIRED_OUTCOMES.

## Standardized primary horizon

SCALP_TRIGGER:
- 15 minutes.

PRIMARY_TRIGGER:
- 60 minutes.

PRIMARY:
- 60 minutes.

These horizons are frozen before comparison.

Secondary:
- 5 / 30 / 240m as available;
- descriptive only.

## Gross standardized return per capture

At the frozen primary horizon:

TRADE_LONG:
- `gross_pct = raw_forward_pct`

TRADE_SHORT:
- `gross_pct = -raw_forward_pct`

NO_TRADE:
- `gross_pct = 0`

DATA_INSUFFICIENT:
- `gross_pct = 0`

This primary metric intentionally evaluates:
- direction quality;
- abstention quality;
- selection quality conditional on the CURRENT detector universe.

## Execution / net profitability

The standardized primary execution contract is frozen in:
- `research/XRP_PAIRED_STANDARD_COST_V1.md`

Primary cost:
- 10 bps round-trip per TRADE.

Sensitivity:
- 5 bps and 15 bps descriptive only.

This is a normalized research cost, not the user's exact account fee tier. Actual deployment profitability still requires the separate execution-economics gate.

Agent-specific entry/stop/TP profitability is a later execution study because MFE/MAE alone does not reveal intrabar hit ordering when both stop and TP are reachable.

## Primary paired statistic

Unit:
- capture.

Primary effect:
- `mean(net_return_per_capture_CHALLENGER - net_return_per_capture_CURRENT)`

If net cost model is not frozen:
- use gross difference only as research diagnostic.

Inference:
- UTC-day block bootstrap;
- 5,000 replicates;
- paired within capture;
- percentile CI95.

A formal superiority claim requires:
1. both arms complete for all included Pair IDs;
2. shared outcome complete;
3. minimum sample gate;
4. lower CI95 of paired net difference > 0;
5. positive total net return for winning arm;
6. no unresolved provenance failures.

No multiple-testing correction is needed for the single predeclared primary paired effect.
Secondary metrics never replace it.

## Minimum formal checkpoint

Whichever occurs later:
- 60 calendar days from formal benchmark start;
- 1,000 complete pairs.

Additional minimum:
- >=40 unique UTC days with complete pairs.

Before the checkpoint:
- descriptive monitoring allowed;
- no winner declaration;
- no rule changes from interim performance.

## Secondary diagnostics

Per arm:
- sum of gross/net per-capture returns (diagnostic, **not portfolio PnL** when alerts overlap);
- mean return per capture;
- mean return per trade;
- trade count;
- trade rate;
- win rate among trades;
- DATA_INSUFFICIENT rate;
- max drawdown under equal-notional sequential captures;
- monthly return;
- worst day;
- tail percentiles.

Paired:
- agreement rate;
- both trade same direction;
- both trade opposite direction;
- CURRENT trade / CHALLENGER abstain;
- CHALLENGER trade / CURRENT abstain;
- both abstain;
- mean paired difference by alert type;
- mean paired difference by disagreement category.

## Detector-selection limitation

ALERT_RESEARCH exists because the CURRENT detector selected an event.

Therefore the paired benchmark is conditional on the CURRENT detector opportunity universe.

A paired win means:
- better analysis decisions on CURRENT-detector captures.

It does **not** prove:
- superior independent opportunity discovery.

That is why XRP_FORWARD_V3_1 remains a separate experiment.

## Existing prelaunch pool

At infrastructure audit time:
- ALERT_RESEARCH rows observed: 58
- first capture: 2026-09-30T09:45:56Z
- latest observed capture: 2026-10-01T00:01:23Z
- Research Version: ALERT_R1

These are frozen as a **PRELAUNCH / BACKFILL SUPPORTIVE** pool only if:
- snapshot is copied verbatim;
- snapshot hash is recorded;
- no paired outcome is shown to either arm before its decision;
- the challenger is not designed using their outcomes.

Because the challenger does not yet exist at the time this pool is observed, these captures do **not** determine the formal superiority verdict.

After the challenger master is frozen, a separate prospective formal batch begins at an exact UTC timestamp recorded in the sealed registry.

Use:
- prelaunch pool = supportive paired backfill;
- post-freeze captures = formal prospective paired benchmark.

No arm should be executed on the prelaunch pool until the challenger master is frozen.

## Versioning

Any change to:
- agent rules;
- standardized horizon;
- state mapping;
- cost model;
- sample gate;
- primary statistic

creates a new benchmark version.

## Formal launch blockers

V1 cannot launch while any of these is missing:
- CHALLENGER master file;
- CHALLENGER rule commit SHA;
- isolated runner protocol verification;
- snapshot hash completeness;
- benchmark registry seal.

Net winner evaluation additionally requires:
- frozen execution-cost contract.


## LLM / runner provenance

Every decision stores:
- Model ID;
- Run Mode;
- rule commit;
- runner commit;
- input Full Snapshot SHA256;
- output SHA256.

For every formal Pair ID:
- CURRENT and CHALLENGER must use the same Model ID;
- CURRENT and CHALLENGER must use the same Run Mode.

The aggregate report stratifies model provenance. A mismatched pair fails provenance.

## Overlapping alerts

Multiple detector alerts can occur close together and their outcome windows may overlap.

Therefore:
- primary inference is paired **per capture**;
- UTC-day block bootstrap handles temporal dependence;
- summed returns and max drawdown are diagnostics only;
- they must not be described as executable portfolio PnL without a separately frozen overlap/capital allocation policy.

No duplicate or inconvenient Pair ID may be removed merely because its outcome overlaps another capture.
