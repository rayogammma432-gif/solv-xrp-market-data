# XRP Challenger V3.1 Launch Abort and V3.2 Relaunch Audit

## Classification

V3.1 deployment result:
- **ABORTED PRELAUNCH / NO VALID FORMAL COLLECTION**

Reason:
- the deployment gate passed, but the collector could subsequently classify the same checkout as dirty because the two components used different Git-status semantics;
- local backup/runtime artifacts and ambiguous PID/status behavior made launch state non-authoritative;
- the observed activation failures occurred before a trustworthy prospective runtime was established.

Dedicated data tables at the V3.2 design point:
- CHALLENGER_CANDIDATES: header only;
- CHALLENGER_OUTCOMES: header only;
- CHALLENGER_HEALTH: header only;
- CHALLENGER_AUDIT: prelaunch/deployment audit rows only.

Therefore no candidate/outcome/health observations from V3.1 are used to alter scientific rules.

## Root cause

A concrete trigger was the local backup `termux/config.json.backup` created during deployment support:
- the deployment gate used `git status --porcelain --untracked-files=no`;
- `current_git_sha()` used `git status --porcelain` and therefore included untracked files;
- the gate could write an activation pinned to clean HEAD while the collector reported `HEAD+DIRTY`;
- activation then failed with a collector Git SHA mismatch.

Additional hardening findings:
- startup tested PID liveness rather than full readiness;
- status tailed historical logs next to current process state;
- no one-command safe reset existed for stale prelaunch artifacts;
- runtime marker provenance checks were incomplete;
- data cursors could advance over transient missing bars;
- same-cycle INCOMPLETE outcomes could be absent from the health count;
- receptor retry concurrency had no script lock;
- CI triggers did not cover all relevant source changes.

## Corrective action

A new forward version is used instead of modifying V3.1 retroactively:
- protocol: `XRP_FORWARD_V3_2`
- start: `2026-10-02T12:00:00Z` = 06:00 Guatemala
- scientific hypotheses: unchanged
- formal 180-day gate: `2027-03-31T12:00:00Z`
- A informational checkpoint: `2026-12-31T12:00:00Z`

V3.1 remains frozen as an aborted prelaunch record.
