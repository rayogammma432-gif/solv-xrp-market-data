#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REG=ROOT/"research/experiments/XRP_PAIRED_BENCHMARK_REGISTRY_DRAFT_V1.json"
PROTOCOL=ROOT/"research/XRP_PAIRED_BENCHMARK_PROTOCOL_V1.md"

def latest_file_commit(path):
    try:
        return subprocess.run(["git","log","-1","--format=%H","--",path],cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip()
    except Exception:return ""

def main():
    reg=json.loads(REG.read_text())
    blockers=[];errors=[]
    cur=reg.get("current_arm") or {};cha=reg.get("challenger_arm") or {}
    if cur.get("rule_file")!="agents/XRP_V3_3_MASTER.txt":errors.append("unexpected CURRENT rule file")
    sha=cur.get("rule_commit_sha") or ""
    if len(sha)!=40:errors.append("CURRENT rule SHA invalid")
    actual=latest_file_commit(cur.get("rule_file",""))
    if actual and actual!=sha:errors.append(f"CURRENT frozen SHA mismatch actual={actual} registry={sha}")
    for k in ("agent_name","agent_version","rule_file","rule_commit_sha","runner_file"):
        if not cha.get(k):blockers.append(f"CHALLENGER_{k.upper()}_MISSING")
    if reg.get("execution_cost_contract") is None:blockers.append("EXECUTION_COST_CONTRACT_NOT_FROZEN_FOR_NET_VERDICT")
    if reg.get("formal_launch"):errors.append("draft registry cannot have formal_launch=true")
    text=PROTOCOL.read_text()
    for marker in ("two isolated executions","PRELAUNCH / BACKFILL SUPPORTIVE","60 calendar days","1,000 complete pairs"):
        if marker not in text:errors.append(f"protocol marker missing: {marker}")
    report={"status":"READY_INFRA_BLOCKED_LAUNCH" if not errors else "ERROR","errors":errors,"launch_blockers":blockers,"formal_launch":False,"current_rule_commit_verified":actual==sha if actual else None}
    out=ROOT/"paired-prelaunch";out.mkdir(exist_ok=True)
    (out/"XRP_PAIRED_PRELAUNCH_VALIDATION.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
    if errors:raise SystemExit(2)

if __name__=="__main__":main()
