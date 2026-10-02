# XRP Challenger Deployment Gate V2

## Purpose

Authoritative local gate for the clean XRP Challenger V3.2 relaunch.

Formal prospective start:
- `2026-10-02T12:00:00Z`
- `2026-10-02 06:00:00 America/Guatemala`

The gate changes deployment mechanics only. Scientific rules remain those frozen in XRP_FORWARD_V3_2.

## Fresh-start sequence

1. Pull the validated V3.2 deployment commit on Motorola.
2. Update the dedicated Apps Script project with the exact current `apps-script/XRP_Challenger_Receptor.gs`.
3. Deploy a **new Web App version** from that source.
4. Keep the dedicated `CHALLENGER_SHARED_SECRET`; it must remain different from XRP CURRENT.
5. Put the new Challenger `/exec` URL and the dedicated secret in `termux/config.json`.
6. Stop any old Challenger process.
7. Archive stale local launch artifacts:
   - `python termux/challenger_deployment_gate.py --reset-local-prelaunch`
8. Verify the reset did not alter `termux/config.json`.
9. Run the gate without activation:
   - `python termux/challenger_deployment_gate.py`
10. Require `PASS_DEPLOYMENT_GATE` and verify:
   - protocol `XRP_FORWARD_V3_2`;
   - receptor `XRP_RECEPTOR_CHALLENGER_V2_R1`;
   - collector `XRP_CHALLENGER_COLLECTOR_V2`;
   - registry SHA `99c17ecf3c3b376f734dc7469351445c7d6727f96d0cb7d5580ea59b5f9f932a`;
   - spreadsheet ID `14mVe2XXcsVBCojZSbp6A7qQKO2RFpovLtKntOYFDwvA`;
   - start `2026-10-02T12:00:00Z`.
11. Write activation in a separate command:
   - `python termux/challenger_deployment_gate.py --write-activation`
12. Start:
   - `bash termux/start_challenger_collector.sh`
13. The start command is successful only when it prints `RUNNING_READY`.
14. Verify independently:
   - `bash termux/status_challenger_collector.sh`
15. Status must report:
   - `status: RUNNING_READY`;
   - `ready: true`;
   - `activation_errors: []`;
   - a valid pre-start runtime marker.

## What the reset archives

The prelaunch reset archives, rather than silently deleting:
- challenger_activation.json
- challenger_runtime.json
- challenger_forward_state.json
- challenger_ready.json
- challenger_heartbeat.json
- challenger_collector.pid
- Challenger-specific log files

It does **not** modify:
- termux/config.json
- CURRENT collector state
- CURRENT receptor
- Google Sheets research rows
- Git-tracked source files

Reset is refused:
- while a Challenger PID is alive;
- within the final 10-minute safety window.

## Git cleanliness contract

Gate and collector use the same source-identity rule:
- tracked modifications make the worktree dirty;
- untracked/ignored runtime files and local backups do not alter the source Git SHA.

This removes the V3.1 mismatch where the gate could pass while the collector later produced `HEAD+DIRTY`.

The shell scripts are tracked as executable in V2 so normal Termux execution does not require a local chmod that would dirty Git.

## Receptor probe

The gate requires the deployed receptor to return all of:
- receptor version;
- dedicated spreadsheet ID;
- expected protocol version;
- expected registry SHA;
- expected collector version.

A stale Apps Script deployment therefore fails even if it still answers HTTP requests.

## Stale artifacts

The gate refuses to pass while any old launch artifact remains. It never automatically overwrites an activation.

This prevents accidental mixing of:
- V3.1 activation;
- V3.1 runtime marker;
- V3.1 state;
- stale PID/readiness state;
with the V3.2 launch.

## Readiness vs liveness

`PID alive` is not a launch success.

The collector becomes ready only after:
- activation validation;
- runtime-marker validation/creation;
- receptor recovery;
- READY marker creation bound to the current PID and provenance.

The start script waits for the READY state and kills the process if readiness never arrives within the startup timeout.

## Fail-closed cases

Do not launch if any of the following occurs:
- fewer than 10 minutes remain before start;
- tracked worktree is dirty;
- CURRENT XRP URL/secret are unavailable, so isolation cannot be proven;
- Challenger URL/secret are missing, placeholders, or equal CURRENT;
- stale local artifacts remain;
- receptor version/storage/protocol/registry/collector identity mismatch;
- activation validation fails;
- process is alive but not READY.

If these cannot be corrected before the safety cutoff, V3.2 is not backfilled. A new future protocol/start is required.

## Scientific boundary

Passing this gate authorizes only shadow research collection. It does not authorize trading or changes to XRP CURRENT.
