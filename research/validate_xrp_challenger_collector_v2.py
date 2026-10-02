#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
UPSTREAM=ROOT/"research/experiments/XRP_FORWARD_REGISTRY_V3_2.jsonl"
REG=ROOT/"research/experiments/XRP_CHALLENGER_COLLECTOR_REGISTRY_V2.json"
PROTOCOL=ROOT/"research/XRP_CHALLENGER_COLLECTOR_PROTOCOL_V2.md"
COLLECTOR=ROOT/"termux/xrp_challenger_collector_v2.py"
TRACKER=ROOT/"termux/forward_v3_2_tracker.py"
DEPLOYMENT_GATE=ROOT/"termux/challenger_deployment_gate_v2.py"
CURRENT=ROOT/"termux/market_collector.py"
OPERATIONAL_RECEPTOR=ROOT/"apps-script/XRP_Receptor_Incremental.gs"
CHALLENGER_RECEPTOR=ROOT/"apps-script/XRP_Challenger_Receptor.gs"
ACTIVATION_EXAMPLE=ROOT/"termux/challenger_v2_activation.example.json"
START=ROOT/"termux/start_challenger_collector_v2.sh"
STATUS=ROOT/"termux/status_challenger_collector_v2.sh"
STOP=ROOT/"termux/stop_challenger_collector_v2.sh"

EXPECTED_REGISTRY_SHA="94babcf11323827e1ec7e77cc4c64977c5a656794cef0b1e2c2056c0cc2f34f9"
EXPECTED_START="2026-10-02T12:00:00Z"
EXPECTED_PROTOCOL="XRP_FORWARD_V3_2"
EXPECTED_COLLECTOR="XRP_CHALLENGER_COLLECTOR_V2"
EXPECTED_RECEPTOR="XRP_RECEPTOR_CHALLENGER_V2_R1"
EXPECTED_SHEET="14mVe2XXcsVBCojZSbp6A7qQKO2RFpovLtKntOYFDwvA"


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    errors=[]
    upstream_sha=sha256_file(UPSTREAM)
    reg=json.loads(REG.read_text(encoding="utf-8"))
    activation=json.loads(ACTIVATION_EXAMPLE.read_text(encoding="utf-8"))
    protocol=PROTOCOL.read_text(encoding="utf-8")
    collector=COLLECTOR.read_text(encoding="utf-8")
    tracker=TRACKER.read_text(encoding="utf-8")
    gate=DEPLOYMENT_GATE.read_text(encoding="utf-8")
    current=CURRENT.read_text(encoding="utf-8")
    op_receptor=OPERATIONAL_RECEPTOR.read_text(encoding="utf-8")
    receptor=CHALLENGER_RECEPTOR.read_text(encoding="utf-8")
    start=START.read_text(encoding="utf-8")
    status=STATUS.read_text(encoding="utf-8")
    stop=STOP.read_text(encoding="utf-8")

    if upstream_sha != EXPECTED_REGISTRY_SHA:
        errors.append(f"V3.2 registry SHA mismatch: {upstream_sha}")
    if reg.get("upstream_registry_sha256") != EXPECTED_REGISTRY_SHA:
        errors.append("collector registry upstream SHA mismatch")
    if reg.get("upstream_protocol") != EXPECTED_PROTOCOL:
        errors.append("collector registry protocol mismatch")
    if reg.get("frozen_forward_start_utc") != EXPECTED_START:
        errors.append("collector registry start mismatch")
    if reg.get("activation_enabled") is not False:
        errors.append("collector registry must remain not activated in source")
    if reg.get("formal_collection_started") is not False:
        errors.append("collector registry must remain prelaunch")
    if reg.get("current_collector_dependency") is not False:
        errors.append("CURRENT dependency must remain false")
    if any(reg.get(k) is not False for k in ("telegram","signals","orders")):
        errors.append("collector must remain research-only")

    if activation.get("enabled") is not False:
        errors.append("activation example must be disabled")
    if activation.get("protocol_version") != EXPECTED_PROTOCOL:
        errors.append("activation example protocol mismatch")
    if activation.get("registry_sha256") != EXPECTED_REGISTRY_SHA:
        errors.append("activation example registry mismatch")
    if activation.get("formal_start_utc") != EXPECTED_START:
        errors.append("activation example start mismatch")
    if activation.get("receptor_version") != EXPECTED_RECEPTOR:
        errors.append("activation example receptor mismatch")
    if activation.get("challenger_spreadsheet_id") != EXPECTED_SHEET:
        errors.append("activation example storage mismatch")

    # CURRENT must stay detached.
    for forbidden in (
        "ForwardV3Tracker","self.forward_v3","forwardV3Events",
        "forwardV3Outcomes","forwardV3Health","forwardV3RecoveryRequest"
    ):
        if forbidden in current:
            errors.append(f"CURRENT collector contains forbidden marker {forbidden}")

    tree=ast.parse(collector)
    imported=set()
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node,ast.ImportFrom) and node.module:
            imported.add(node.module)
    if "market_collector" in imported:
        errors.append("V2 collector imports market_collector")
    if "forward_v3_2_tracker" not in imported:
        errors.append("V2 collector does not import V3.2 tracker")

    for marker in (
        EXPECTED_COLLECTOR, EXPECTED_RECEPTOR, EXPECTED_START,
        "challenger_v2_activation.json","challenger_v2_runtime.json",
        "challenger_v2_forward_state.json","challenger_v2_heartbeat.json",
        "LATE_FIRST_START_BLOCKED_CREATE_NEW_PROTOCOL_START",
        "def probe_receptor(self):","def write_heartbeat(self, phase",
    ):
        if marker not in collector and marker not in tracker:
            errors.append(f"collector/tracker missing marker {marker}")

    # Regression guards for the failed V1 flow.
    if "elif formal_start and now >= formal_start:" not in collector:
        errors.append("late first boot is not runtime-marker-only fail closed")
    if "self.tracker.reconcile_remote" in collector.split("def probe_receptor(self):",1)[1].split("def reconcile_recovery",1)[0]:
        errors.append("receptor probe mutates tracker state")
    if '["git", "-c", "core.fileMode=false"' not in tracker:
        errors.append("tracker does not ignore file-mode-only git noise")
    if '"-c", "core.fileMode=false"' not in gate:
        errors.append("deployment gate does not ignore file-mode-only git noise")
    if "MIN_ACTIVATION_LEAD_SECONDS = 30 * 60" not in gate:
        errors.append("deployment gate lead is not 30 minutes")
    if "write_or_reuse_activation" not in gate:
        errors.append("deployment gate is not idempotent for valid activation")

    for marker in (
        EXPECTED_RECEPTOR, EXPECTED_PROTOCOL, EXPECTED_REGISTRY_SHA,
        EXPECTED_COLLECTOR, EXPECTED_SHEET,
        "challenger_recovery","challenger_incremental",
        "CHALLENGER_SHARED_SECRET"
    ):
        if marker not in receptor:
            errors.append(f"dedicated receptor missing {marker}")

    for forbidden in (
        EXPECTED_RECEPTOR,"XRP_RECEPTOR_CHALLENGER_V1_R2",
        "challenger_recovery","challenger_incremental",
        "challengerCandidates","challengerOutcomes","challengerHealth"
    ):
        if forbidden in op_receptor:
            errors.append(f"operational receptor contains Challenger marker {forbidden}")

    for script,name in ((start,"start"),(status,"status"),(stop,"stop")):
        if "challenger_v2_collector.pid" not in script:
            errors.append(f"{name} wrapper not V2 PID isolated")
    if "--prelaunch-check --check-receptor" not in start:
        errors.append("start wrapper lacks fail-closed foreground preflight")
    if "challenger_v2_heartbeat.json" not in start or "challenger_v2_heartbeat.json" not in status:
        errors.append("heartbeat not enforced by start/status")
    if "challenger_v2_collector.log" not in status:
        errors.append("status does not restrict output to V2 logs")

    for marker in (
        "2026-10-02T12:00:00Z",
        "2026-10-02 06:00:00 Guatemala",
        "V1/V3.1 disposition",
        "Local state existence never substitutes for the runtime marker",
        "2026-01-01 through 2026-08-31 remains LOCKED",
    ):
        if marker not in protocol:
            errors.append(f"protocol missing marker {marker}")

    report={
        "version":"XRP_CHALLENGER_COLLECTOR_PRELAUNCH_V2",
        "upstream_registry_sha256":upstream_sha,
        "formal_start_utc":EXPECTED_START,
        "status":"PASS_PRELAUNCH_NOT_ACTIVATED" if not errors else "FAIL",
        "formal_collection_started":False,
        "errors":errors,
    }
    out=ROOT/"challenger-collector-prelaunch-v2"
    out.mkdir(exist_ok=True)
    (out/"XRP_CHALLENGER_COLLECTOR_PRELAUNCH_V2.json").write_text(
        json.dumps(report,indent=2)+"\n",encoding="utf-8"
    )
    print(json.dumps(report,indent=2))
    if errors:
        raise SystemExit(2)


if __name__=="__main__":
    main()
