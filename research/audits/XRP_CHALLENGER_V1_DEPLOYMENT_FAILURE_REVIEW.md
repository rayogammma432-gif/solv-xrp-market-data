# XRP Challenger V1 Deployment Failure Review

## Disposition

V1 / XRP_FORWARD_V3_1 is **ABORTED AS A PROSPECTIVE DEPLOYMENT**.

Frozen start:
- 2026-10-01T06:00:00Z

Accepted prospective V1 evidence:
- NONE.

## Failure modes identified

1. Local activation/runtime/state filenames were not versioned.
   A stale or partially-created V1 activation could block later activation attempts.

2. Git cleanliness treated file-mode changes as source changes.
   Termux chmod changes on tracked shell scripts produced GIT_TRACKED_WORKTREE_DIRTY even when file contents were unchanged.

3. Collector provenance used broad git status.
   Untracked/local runtime artifacts or mode-only noise could append +DIRTY and invalidate activation unexpectedly.

4. State existence could bypass the late-first-start guard.
   A state file is not proof that a valid pre-start process boot occurred. Only a cryptographically-bound runtime marker is valid evidence.

5. Receptor recovery could mutate local state during a diagnostic/prelaunch probe.
   Diagnostics must be read-only with respect to tracker state.

6. Runtime marker creation occurred before receptor recovery verification.
   A failed receptor after marker creation could leave a marker that looked like a valid pre-start boot.

7. Prelaunch CLI returned success even when activation_errors was non-empty.
   Shell wrappers could not reliably fail closed from exit status.

8. Status output tailed historical logs.
   Old fatal errors and current process state could be shown together, making a stopped/failed attempt look active.

9. Start wrapper validated process existence only.
   A live PID alone does not prove valid activation, runtime marker, receptor identity or cycle health.

10. Shell executable-bit handling caused operational friction.
    V2 is invoked explicitly with `bash ...`; executable bits are not part of deployment correctness.

## V2 corrections

- new V3.2 start/version and registry;
- versioned V2 local artifacts;
- 30-minute activation lead;
- content-only Git cleanliness with file-mode noise ignored;
- post-start restart requires a valid pre-start runtime marker unconditionally;
- diagnostic receptor probe is non-mutating;
- receptor verification precedes runtime marker creation;
- prelaunch errors return non-zero;
- heartbeat-based status;
- startup requires activation + receptor + runtime marker + heartbeat;
- dedicated V2 receptor version;
- V1 artifacts are never reused.
