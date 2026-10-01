# XRP PAIRED BENCHMARK PRELAUNCH AUDIT V1

## Status

**READY_INFRA_BLOCKED_LAUNCH**

Formal launch:
- **NO**

Final prelaunch CI:
- workflow: `XRP Paired Benchmark Prelaunch V1`
- run: `36797538546`
- head commit: `701724e21269b41f38dee40f160697ef411909ca`
- conclusion: **SUCCESS**
- artifact: `11134456226`
- artifact SHA256: `93b82b5e473de3cbd0b6696f8464b2d4e7ad250205779a15d9bbf82dcba125de`

## Frozen prelaunch pool

PAIRED_CAPTURES:
- 61 rows
- role: `PRELAUNCH_POOL`
- snapshot class: `RESEARCH_ONLY`
- batch: `XRP_PAIR_PRELAUNCH_V1`
- frozen UTC: `2026-10-01T00:41:45.144Z`

These rows are supportive only.

They cannot determine the formal winner because:
- their full market-bar snapshots were not frozen at Alert UTC;
- they predate formal benchmark activation.

At audit close:
- PAIRED_CURRENT rows: 0
- PAIRED_CHALLENGER rows: 0
- PAIRED_OUTCOMES rows: 0

Therefore no paired performance result was opened.

## Frozen CURRENT arm

- agent: XRP CURRENT
- baseline: `XRP_V3.3_PAIRED_BASELINE_V1`
- rule file: `agents/XRP_V3_3_MASTER.txt`
- frozen rule commit: `b6f62ed220226a10f653c45c5c3680320a0dd7fd`

## Frozen CHALLENGER arm

- agent: XRP CHALLENGER
- version: `XRP_CHALLENGER_PAIRED_V1`
- rule file: `agents/XRP_CHALLENGER_PAIRED_V1.md`
- frozen rule commit: `bb6605e06066fc42d8b440954ec92a9f401d99bf`

Rules:
- SCALP: taker-flow exhaustion
- PRIMARY: 15m momentum exhaustion reconstructed from frozen XRP 1m bars
- no OI entry rule
- no detector direction input

## Standardized economic comparison

Primary execution cost:
- 10 bps round trip per TRADE

Sensitivity:
- 5 bps
- 15 bps

Primary unit:
- capture

NO_TRADE:
- 0% contribution

DATA_INSUFFICIENT:
- 0% contribution and counted separately

Primary effect:
- mean paired standardized net return per capture
- Challenger minus CURRENT

Inference:
- UTC-day block bootstrap
- 5,000 replicates
- percentile CI95

Minimum formal checkpoint:
- 60 calendar days
- 1,000 complete prospective pairs
- 40 unique UTC days

## Full prospective snapshot

Formal pairs require:
- `XRP_PAIRED_SNAPSHOT_V1`
- exactly 12 logical Symbol/Timeframe series
- XRPUSDT + BTCUSDT
- 1m / 5m / 15m / 1h / 4h / 1d
- XRPUSDT 1m: 360 bars
- every other logical series: 250 bars
- chunk size: <=180 bars
- Full Snapshot SHA256
- exact continuity
- exact latest closed bar at Alert UTC
- no bar with close_time > Alert UTC

Collector:
- `termux/market_collector.py`
- commit: `fc27fe20340c1d9fd6f047b5a42adc549079839d`

Receptor:
- `apps-script/XRP_Receptor_Incremental.gs`
- commit: `dac8e1e9d0280b6bf57f911c7fcdd8ceb11395f2`

## Isolation

Frozen protocol:
- `research/XRP_PAIRED_ISOLATION_PROTOCOL_V1.md`
- commit: `178355de67d6b3b0c0414daf40615c1794484a61`

Required execution contexts:
1. CURRENT-only
2. CHALLENGER-only
3. evaluation-only after both decisions are COMPLETE

Within each Pair ID:
- same Model ID
- same Run Mode

Outcomes are materialized only after both decisions are persisted.

## Important issues found before launch

### 1. Missing full market history in ALERT_RESEARCH

ALERT_RESEARCH alone does not contain enough recent bar history for a fair replay of XRP_V3.3 structure/trigger logic.

Fix:
- formal prospective captures now freeze complete market-bar snapshots for both arms.

### 2. Detector-signed outcomes were not agent-neutral

ALERT_FORWARD / ALERT_MFE_MAE are signed by detector direction.

Fix:
- PAIRED_OUTCOMES reconstructs direction-neutral raw market outcomes before applying each agent's LONG/SHORT/NO_TRADE decision.

### 3. Google Sheets 50k-character cell risk

A 360-bar XRP 1m JSON segment reached 48,191 characters in smoke testing.

Fix:
- logical series are chunked into <=180 bars;
- the full snapshot hash covers every chunk;
- receptor reconstructs and verifies logical series.

### 4. Row count is not continuity

Having 250 rows does not prove a snapshot is gap-free or current.

Fix:
- collector and receptor both require exact timeframe spacing;
- final close must equal the exact latest bar that should have been closed before Alert UTC.

### 5. LLM/model drift

The same rule can yield different outputs under different model/configuration.

Fix:
- every decision stores Model ID and Run Mode;
- paired provenance fails if the two arms differ within the same Pair ID.

### 6. Overlapping alerts

Summing all per-alert returns can overstate executable portfolio economics when alerts overlap.

Fix:
- primary statistical unit remains capture;
- summed return / drawdown are diagnostics only;
- no portfolio-PnL claim without a separate capital-overlap policy.

### 7. Prelaunch contamination risk

Existing captures were observed before a challenger was frozen.

Fix:
- 61 historical captures are supportive only;
- the formal superiority verdict uses only post-freeze `FORMAL_PROSPECTIVE` captures.

## Final CI gates

PASS:
- Python syntax
- Apps Script syntax
- frozen CURRENT commit
- frozen CHALLENGER commit
- frozen cost contract
- frozen snapshot contract
- exact infrastructure revisions
- snapshot SHA determinism
- 12 logical series / 24 smoke chunks
- no-look-ahead
- continuity
- Google Sheets cell-size safety
- formal-start eligibility gate
- synthetic evaluator with 1,200 pairs / 60 days

The synthetic evaluator's displayed winner is test data only and has no empirical meaning.

## Remaining formal-launch blockers

Exactly three blockers remain:

1. `FORMAL_START_NOT_FROZEN`
2. `DEPLOYMENT_NOT_VERIFIED`
3. `ISOLATED_RUN_PROCESS_NOT_VERIFIED`

These are intentional.

## Correct next step

Do **not** set the formal start yet.

First:
1. deploy the exact collector commit to the Motorola/Termux environment;
2. deploy the exact Apps Script receptor revision;
3. generate one non-formal live smoke capture and verify:
   - PAIRED_CAPTURES written;
   - all snapshot chunks written;
   - hashes match;
   - latest-close/continuity checks pass;
4. execute one isolated CURRENT + CHALLENGER dry-run pair without outcomes;
5. verify Model ID / Run Mode provenance;
6. mark deployment and isolation as verified;
7. freeze a future UTC `formal_start_utc`;
8. seal registry;
9. only then start `FORMAL_PROSPECTIVE`.

No formal paired result should be evaluated before step 9.
