# BACKFILL_FILTER_R1 — Activation Record

Date: 2026-10-03 UTC

## Purpose

Activate a reversible first-pass filter for manual research backfill. The filter reduces correlated analyses while preserving every raw capture in ALERT_RESEARCH.

## Active components

- Protocol: agents/RESEARCH_BACKFILL_AGENT_V2.md
  - activation commit: 65e0b534e36190cd818b5e38e2dce5df4eb38f74
- Filter: agents/BACKFILL_FILTER_R1.md
  - activation commit: d2b202e8e7d3031d81f8ddab872e81803f9f7621
- SOLV master: agents/SOLV_V3_4_MASTER.txt
  - commit: 143a13d27632ca203253af502815bbe5179a36cb
- XRP master: agents/XRP_V3_4_MASTER.txt
  - commit: 8f8b4bc2126bf642538515f4bec9317e108989ab

## Workbook additions

Both SOLV_Market_Data and XRP_Market_Data now contain:
- BACKFILL_QUEUE
- BACKFILL_EPISODES

No rows were deleted from ALERT_RESEARCH.

## Initial classification snapshot

At final verification:
- SOLV: 202 unlinked rows -> 182 PRIORITY, 14 DEFERRED, 6 EXACT_DUP; 152 episodes.
- XRP: 225 unlinked rows -> 191 PRIORITY, 28 DEFERRED, 6 EXACT_DUP; 161 episodes.
- Combined first-pass queue: 373 PRIORITY, 42 DEFERRED, 12 EXACT_DUP.

Additionally, one pending SOLV alert with Context JSON identical to an already analyzed SOLV V3.4 alert was linked directly to the existing analysis with Link Type=EXACT_CONTEXT and removed from the analysis queue.

These counts are a point-in-time snapshot; the live collector can add later captures.

## Safety properties

- ALERT_RESEARCH remains immutable.
- Exact dedup requires raw Context JSON equality.
- Existing analysis reuse is Rule-Version aware: V3.3 cannot suppress creation of V3.4 evidence for a new Alert ID.
- DEFERRED means postponed, not discarded.
- EJECUTA BACKFILL processes PRIORITY by default.
- EJECUTA BACKFILL DEFERRED can later analyze correlated snapshots.
- No SIGNAL or trade may be created from backfill.
- Classification uses no forward outcome data.

## Statistical intent

Default inference should not treat correlated snapshots as independent observations. Report both snapshot-level results and episode/thesis-unique results, prioritizing the latter for comparative conclusions.
