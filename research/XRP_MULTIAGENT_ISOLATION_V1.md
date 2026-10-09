# XRP MULTIAGENT LAB V1 — ISOLATION AND DATA CONTRACT
STATUS: SETUP_ONLY / SHADOW / NO PRODUCTION EXECUTION.
DATE: 2026-10-09. CURRENT authority continues independently at XRP_V3.6 BASE V3.5 + OVERRIDE V3.6. No modification or fork in main.

## Role split
- Source: Google Sheet XRP_Market_Data ID 1ag0yaE0hcDoG8uED4qejfHGlD2OuXZxvUPYZRUzjqG0. Read only. LIVE_STATE is authoritative for lab features; MARKET is context. Never touch production ANALYSES/SIGNALS/PERFORMANCE/PAIRED_*.
- A: Google Sheet 1e9NLM4TZLl5eZgrMdQ6eg4TRNfuKXXcqEv8gJO86lcs, write exclusively RUNS, DECISIONS, AUDIT in A. STATE/OUTCOMES reserved for subsequent explicit workflows.
- B: Google Sheet 15egzvPYgLwdGtEMYfsiLDRZRWsRSbw-KTNQf3KUnUPU, write exclusively RUNS, DECISIONS, AUDIT in B.
- Evaluator: Google Sheet 1VJDdlItLry7EWKndsWLvzuwhD362In3g0KBcOJbDKrg. Can read completed A/B decisions only AFTER BOTH COMPLETE; not part of agents' prompts. Evaluator cannot write any source/production/A/B row.
- Existing Challenger and PAIRED benchmark are separate and explicitly NOT inputs.

## Authoritative lab branch
Repository rayogammma432-gif/solv-xrp-market-data, branch lab/xrp-multiagent-v1. This is not an operational CURRENT branch. Do NOT merge to main, modify XRP_MASTER_MANIFEST.json, modify XRP_SYSTEM_STATUS.md or production scripts. Masters are read with blob SHA validation from LAB manifest only.

## Production protection is a permissions problem
Instruction-based isolation is insufficient. Run each arm under least-privilege credentials:
- CAPTURE identity: reader on XRP_Market_Data; no write access anywhere, no trading credentials.
- A writer identity: writer on A sheet only, no access to source, B, comparison, production or archives.
- B writer identity: writer on B sheet only; no access to A or source.
- Evaluator identity: reader on A/B and writer on comparison only; no production write access.
Connected ChatGPT OAuth sessions commonly retain broader access: do NOT characterize prompt restrictions as a verified IAM boundary. Production protection remains PENDING until separate credentials and tests confirm denied writes.

## Capture protocol
At a single capture instant, read LIVE_STATE once. Verify:
- market.symbol == XRPUSDT; system.generated_at_utc parses as UTC;
- capture system age <=120 seconds and clock skew not >15 seconds;
- canonical XRP data.sync_1m/5m/15m/1h/4h/1d == OK;
- canonical XRP data.last_close_TF == expected_last_close_TF;
- BTC btc.data.sync_1m/5m/15m/1h/4h/1d == OK and last_close times exist;
- required numeric features finite, parse decimal comma without silently coercing missing values;
- timestamps and snapshot read are from a consistent API response.
Freeze sorted key-value canonical JSON and SHA256; snapshot_id='XLAB1|'+sha256[0:24]. Both agents receive exactly these bytes. If any gate fails => DATA_INSUFFICIENT for both, no price signal.
Capture provenance: UTC, source spreadsheet id, observed clock, collector id, sha, candle closes. Preserve original snapshot file for later audit if authorized; never publish credentials in GitHub.

## Run and output contract
No order API, no Telegram production channel, no SIGNAL, no ACTIVE, no user trade modification.
Allowed decision: SHADOW_LONG, SHADOW_SHORT, NO_TRADE, DATA_INSUFFICIENT.
Allowed RUN status: STARTED, COMPLETE, DATA_INSUFFICIENT, PERSISTENCE_FAILED. RUNS and DECISIONS are append-only; do not rewrite history. run_id is deterministic agent_id/master blob SHA/snapshot SHA/model ID/run mode. Every decision_id references a single run_id.
Every run must persist RUNS + DECISIONS + AUDIT with read-back verification before reporting COMPLETE. If a partial write occurred, do not generate a new run_id; audit and reconcile idempotently. No concurrency without an external single-writer lock per agent; Sheets is not a transactional database and append is not atomic across tabs.
Do not infer model ID; record exact or UNAVAILABLE. Run mode is MANUAL_SHADOW / AUTOMATED_SHADOW and must be factual.
Do not treat results as PnL. OUTCOMES only after horizon maturity and under separately preregistered fees, fill/slippage, risk model and same capture cohorts.

## Evaluation
Compare only if SAME full snapshot SHA256, same Model ID and Run Mode, both statuses COMPLETE, identical frozen cost/horizon rules, no CONTAMINATION. Evaluator writes only comparison Sheet and never prompts A/B with results.
Report raw agreement and provenance failures descriptively first. No winning model, accuracy or performance claim without mature, preregistered prospective study. Do not reuse or contaminate existing PAIRED benchmark.

## Deployment boundary
This branch and these Sheets constitute SCHEMA/MASTER SETUP. They are NOT background automations or standalone ChatGPT Projects; a launcher/scheduler with distinct credentials must be provisioned and tested before unattended executions. Require negative permission tests and a simultaneous same-snapshot dry-run before moving to ACTIVATED_SHADOW. No step here authorizes live orders or modifying CURRENT.
