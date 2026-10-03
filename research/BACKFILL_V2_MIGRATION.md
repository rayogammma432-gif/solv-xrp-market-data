# BACKFILL V2 — Migration Record

Date: 2026-10-03 UTC

## Purpose

Migrate the manual research backfill from V1 / V3.3 rule pointers to an explicitly versioned V2 protocol using the current V3.4 masters, without rewriting historical backfills.

## Authorized files

- Protocol: `agents/RESEARCH_BACKFILL_AGENT_V2.md`
  - activation baseline commit: `bba36e0d8da6868fcf5b036de384cb4c890fe3d6`
- XRP rules: `agents/XRP_V3_4_MASTER.txt`
  - baseline commit: `8f8b4bc2126bf642538515f4bec9317e108989ab`
- SOLV rules: `agents/SOLV_V3_4_MASTER.txt`
  - baseline commit: `143a13d27632ca203253af502815bbe5179a36cb`
- Project instruction source: `agents/PROJECT_INSTRUCTIONS_BACKFILL.md`
  - migration commit: `a7999d92d85b7ff0ae40e95d09a2cc9433f2d232`

Runtime backfill must still retrieve the latest commit containing each authorized file at the start of every manual run and persist the exact SHA actually used.

## Rule precedence

BACKFILL V2 uses historical `ALERT_RESEARCH` snapshots as the decision-time source. Live-source freshness requirements in the V3.4 masters are overridden only inside backfill. Technical V3.4 logic remains applicable.

## Historical preservation

Existing V1/V3.3 analyses and links are immutable historical evidence. Normal V2 backfill processes only Alert IDs not already linked. Reanalysis of an already-linked snapshot under V3.4 requires a separate paired/replay protocol.

## Activation condition

Repository migration is complete. ChatGPT project `backfill` becomes operationally V2 only after its static Project Instructions are replaced with the current contents of `agents/PROJECT_INSTRUCTIONS_BACKFILL.md`.

Until that manual project-setting update is made, do not run `EJECUTA BACKFILL`.