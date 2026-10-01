#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REG=ROOT/"research/experiments/XRP_PAIRED_BENCHMARK_REGISTRY_DRAFT_V1.json"
PROTOCOL=ROOT/"research/XRP_PAIRED_BENCHMARK_PROTOCOL_V1.md"

def latest_file_commit(path):
    return subprocess.run(
        ["git","log","-1","--format=%H","--",path],
        cwd=ROOT,check=True,capture_output=True,text=True
    ).stdout.strip()

def verify_frozen(path,expected,label,errors):
    if not path or not expected:
        errors.append(f"{label}: missing path/SHA")
        return
    actual=latest_file_commit(path)
    if actual!=expected:
        errors.append(f"{label}: frozen SHA mismatch actual={actual} registry={expected}")

def main():
    reg=json.loads(REG.read_text(encoding="utf-8"))
    errors=[];blockers=[]

    if reg.get("benchmark_version")!="XRP_PAIRED_BENCHMARK_V1":
        errors.append("wrong benchmark version")
    if reg.get("formal_launch") is not False:
        errors.append("prelaunch registry must have formal_launch=false")
    if reg.get("status")!="READY_PRELAUNCH_DEPLOYMENT_PENDING":
        errors.append("unexpected prelaunch status")

    cur=reg.get("current_arm") or {}
    cha=reg.get("challenger_arm") or {}
    verify_frozen(cur.get("rule_file"),cur.get("rule_commit_sha"),"CURRENT rule",errors)
    verify_frozen(cur.get("runner_file"),cur.get("runner_commit_sha"),"CURRENT runner",errors)
    verify_frozen(cha.get("rule_file"),cha.get("rule_commit_sha"),"CHALLENGER rule",errors)
    verify_frozen(cha.get("runner_file"),cha.get("runner_commit_sha"),"CHALLENGER runner",errors)

    cost=reg.get("execution_cost_contract") or {}
    verify_frozen(cost.get("file"),cost.get("commit_sha"),"cost contract",errors)
    if cost.get("primary_round_trip_bps")!=10:
        errors.append("primary standardized cost must be 10 bps")
    if cost.get("sensitivity_round_trip_bps")!=[5,15]:
        errors.append("cost sensitivity mismatch")

    snap=reg.get("snapshot") or {}
    if snap.get("version")!="XRP_PAIRED_SNAPSHOT_V1":errors.append("snapshot version mismatch")
    if snap.get("formal_required_completeness")!="FULL":errors.append("formal snapshot must be FULL")
    if snap.get("required_segments")!=12:errors.append("snapshot must have 12 segments")
    if snap.get("xrp_1m_bars")!=360:errors.append("XRP 1m snapshot must have 360 bars")
    if snap.get("other_segment_bars")!=250:errors.append("other segments must have 250 bars")

    horizons=reg.get("standardized_horizons_min") or {}
    if horizons!={"SCALP_TRIGGER":15,"PRIMARY_TRIGGER":60,"PRIMARY":60}:
        errors.append("standardized horizon mapping changed")
    boot=reg.get("bootstrap") or {}
    if boot.get("unit")!="UTC_DAY" or boot.get("replicates")!=5000:
        errors.append("bootstrap contract changed")
    minimum=reg.get("minimum_checkpoint") or {}
    if minimum!={"calendar_days":60,"complete_pairs":1000,"unique_utc_days":40}:
        errors.append("minimum checkpoint changed")

    model=reg.get("model_provenance") or {}
    if not model.get("same_model_id_within_pair") or not model.get("same_run_mode_within_pair"):
        errors.append("model provenance pairing not enforced")

    text=PROTOCOL.read_text(encoding="utf-8")
    for marker in (
        "two isolated executions",
        "PRELAUNCH / BACKFILL SUPPORTIVE",
        "Full Snapshot SHA256",
        "10 bps",
        "Overlapping alerts",
        "60 calendar days",
        "1,000 complete pairs"
    ):
        if marker not in text:errors.append(f"protocol marker missing: {marker}")

    if not reg.get("formal_start_utc"):blockers.append("FORMAL_START_NOT_FROZEN")
    if not reg.get("deployment_verified"):blockers.append("DEPLOYMENT_NOT_VERIFIED")
    if not reg.get("isolated_run_process_verified"):blockers.append("ISOLATED_RUN_PROCESS_NOT_VERIFIED")

    report={
        "status":"READY_INFRA_BLOCKED_LAUNCH" if not errors and blockers else ("READY_FOR_SEAL" if not errors else "ERROR"),
        "errors":errors,
        "launch_blockers":blockers,
        "formal_launch":False,
        "current_rule_commit_verified":not any(x.startswith("CURRENT rule") for x in errors),
        "challenger_rule_commit_verified":not any(x.startswith("CHALLENGER rule") for x in errors),
        "cost_contract_verified":not any(x.startswith("cost contract") for x in errors),
        "snapshot_contract_verified":not any("snapshot" in x.lower() for x in errors)
    }
    out=ROOT/"paired-prelaunch";out.mkdir(exist_ok=True)
    (out/"XRP_PAIRED_PRELAUNCH_VALIDATION.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
    if errors:raise SystemExit(2)

if __name__=="__main__":
    main()
