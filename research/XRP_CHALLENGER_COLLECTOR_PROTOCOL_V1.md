# XRP Challenger Independent Collector Protocol V1

## Estado

**PRELAUNCH — IMPLEMENTED, NOT FORMALLY ACTIVATED**

Purpose:
- collect Challenger research candidates independently of CURRENT;
- preserve XRP_FORWARD_V3_1 rules exactly;
- create no SIGNALS, orders, Telegram trade alerts or CURRENT decisions.

## Separation

CURRENT path:
`Binance → market_collector.py → AlertDetector → CURRENT agent`

Challenger path:
`Binance → xrp_challenger_collector.py → ForwardV3Tracker → CHALLENGER_* tables`

The Challenger process has:
- its own PID;
- its own logs;
- its own state file;
- its own runtime activation marker;
- its own recovery stream;
- its own health table.

It does not import or call `market_collector.py`.

The CURRENT collector no longer instantiates or executes `ForwardV3Tracker`.

## Frozen research rules

Upstream protocol:
- `research/XRP_FORWARD_RESEARCH_PROTOCOL_V3_1.md`

Upstream registry SHA256:
- `4905aa1e94cbf2fe9318c761942d440a298ba5655d78e8e3a80bfc5cb85caded`

No thresholds/horizons/floors are changed here.

### A — Taker-flow exhaustion
Role:
- `DIRECTIONAL_RESEARCH_CANDIDATE`

Grid:
- closed XRPUSDT 1m.

Rule:
- abs(taker imbalance) >= 0.30
- rel volume20 >= 1.5
- direction = -sign(taker imbalance)

Primary:
- 15m.

### B — OI moderator
Role:
- `RESEARCH_MODERATOR`

Grid:
- PRIMARY_15M reconstructed from 1m.

Rule:
- abs(ret12) >= 0.005
- abs(oi_chg_15m) >= 0.005

It remains research context:
- it is not an operational entry rule;
- it creates no SIGNAL;
- it does not alter A/C direction.

Primary research effect:
- expansion minus contraction signed 60m.

### C — Momentum exhaustion
Role:
- `DIRECTIONAL_RESEARCH_CANDIDATE`

Grid:
- PRIMARY_15M reconstructed from exact 1m.

Rule:
- abs(ret12) >= 0.010
- rel volume20 >= 1.5
- direction = -sign(ret12)

Primary:
- 60m.

## Storage

Dedicated Google spreadsheet:
- title: `XRP_Challenger_Research`
- spreadsheet ID: `14mVe2XXcsVBCojZSbp6A7qQKO2RFpovLtKntOYFDwvA`

Dedicated tabs:
- `CHALLENGER_CANDIDATES`
- `CHALLENGER_OUTCOMES`
- `CHALLENGER_HEALTH`
- `CHALLENGER_AUDIT`

The operational XRP workbook does not contain Challenger destination tabs.

Legacy/prelaunch `FORWARD_V3_*` tables remain historical scaffolding only and are not the independent collector destination.

## Candidate stream vs operational stream

V1 implements only the **candidate research stream**.

Every qualifying A/B/C event is preserved.

There is deliberately no:
- cooldown;
- position-netting;
- pyramiding;
- capital allocation;
- duplicate-signal suppression beyond identical Event ID;
- Telegram trade signal.

A future operational stream requires a separately frozen execution/overlap policy after research validation.

## No giant event snapshots

The Challenger collector does not store a full multi-timeframe bar snapshot for every candidate.

Instead each row stores:
- exact decision timestamp;
- reference close;
- exact feature values;
- rule parameters;
- protocol/registry provenance;
- collector Git SHA;
- payload SHA256.

The underlying market series remain independently reproducible from official Binance data.

This avoids duplicating hundreds of nearly identical bars for high-frequency candidate streams.

## Recovery / disconnects

The tracker:
- catches up every missed 1m decision in chronological order;
- paginates Binance klines;
- reconstructs PRIMARY 15m from exact consecutive 1m bars;
- never nearest-fills or interpolates.

Google Sheets recovery returns:
- recent CHALLENGER_CANDIDATES rows;
- existing CHALLENGER_OUTCOMES IDs;
- latest CHALLENGER_HEALTH row.

Local state is therefore not the only recovery source.

## OI limitation

OI uses Binance 5m historical OI with:
- timestamp t available at t+5m;
- exact t-15m required.

If provider retention prevents recovery:
- Candidate B is not fabricated;
- health records OI failure.

A/C remain evaluable from XRP 1m.

## Activation guard

The formal frozen V3.1 start is:
- `2026-10-01T06:00:00Z`

The independent collector is fail-closed.

It requires `termux/challenger_activation.json` containing:
- enabled=true;
- exact protocol version;
- exact registry SHA;
- exact deployed collector Git SHA;
- expected receptor version;
- deployment_verified_utc strictly before formal start.

On first valid pre-start boot it creates:
- `termux/challenger_runtime.json`

If the first live boot occurs after the frozen start and there is no valid pre-start runtime marker/state:
- the collector refuses to backfill;
- V3.1 must not be called prospective;
- a new protocol/start version is required.

## Process cadence

The collector runs independently near second 08 of each UTC minute.

This provides a short close/API propagation buffer while remaining well before the next minute.

The tracker itself deduplicates decisions/outcomes.

## Receptor isolation

Dedicated source:
- `apps-script/XRP_Challenger_Receptor.gs`

This must be deployed as a separate Apps Script web app from the operational XRP receptor.

Dedicated Script Property:
- `CHALLENGER_SHARED_SECRET`

Dedicated config block:
- `challenger.web_app_url`
- `challenger.shared_secret`

Accepted modes:
- `challenger_recovery`
- `challenger_incremental`

The operational XRP receptor rejects these modes and contains no Challenger write path.

Expected dedicated receptor version:
- `XRP_RECEPTOR_CHALLENGER_V1_R2`

## Health

One finalized hourly row records:
- expected/evaluated/missing 1m;
- expected/evaluated/missing PRIMARY 15m;
- OI checks/failures;
- A/B/C candidate counts;
- pending outcomes;
- incomplete outcomes;
- last evaluated timestamps;
- collector provenance.

## Formal scientific gates

Unchanged from XRP_FORWARD_V3_1.

The independent collector is an implementation change, not a hypothesis change.

No interim candidate outcome may be used to alter:
- thresholds;
- direction;
- primary horizon;
- effect floors.

## Deployment boundary

Source code being committed is not formal activation.

Before live start:
1. deploy exact Git commit to Motorola;
2. deploy `apps-script/XRP_Challenger_Receptor.gs` as its own Apps Script web app;
3. configure a unique `CHALLENGER_SHARED_SECRET`;
4. put that dedicated URL/secret in the local `challenger` config block;
5. confirm the dedicated Challenger workbook/tabs exist;
6. run prelaunch source/receptor smoke;
7. create activation file with exact deployed SHAs;
8. verify activation strictly before frozen start;
9. start independent process before frozen start.

If step 6/7 cannot be satisfied:
- do not backfill;
- create a new forward version/start.

## 2026 historical holdout

Unchanged:
- 2026-01-01 → 2026-08-31 remains LOCKED.
