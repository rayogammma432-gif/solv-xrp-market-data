#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
UPSTREAM=ROOT/"research/experiments/XRP_FORWARD_REGISTRY_V3_1.jsonl"
REG=ROOT/"research/experiments/XRP_CHALLENGER_COLLECTOR_REGISTRY_V1.json"
PROTOCOL=ROOT/"research/XRP_CHALLENGER_COLLECTOR_PROTOCOL_V1.md"
COLLECTOR=ROOT/"termux/xrp_challenger_collector.py"
CURRENT=ROOT/"termux/market_collector.py"
RECEPTOR=ROOT/"apps-script/XRP_Receptor_Incremental.gs"
ACTIVATION_EXAMPLE=ROOT/"termux/challenger_activation.example.json"


def sha256_file(path):
    h=hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main():
    errors=[]
    upstream_sha=sha256_file(UPSTREAM)
    reg=json.loads(REG.read_text(encoding="utf-8"))
    activation=json.loads(ACTIVATION_EXAMPLE.read_text(encoding="utf-8"))
    protocol=PROTOCOL.read_text(encoding="utf-8")
    collector=COLLECTOR.read_text(encoding="utf-8")
    current=CURRENT.read_text(encoding="utf-8")
    receptor=RECEPTOR.read_text(encoding="utf-8")

    if upstream_sha!="4905aa1e94cbf2fe9318c761942d440a298ba5655d78e8e3a80bfc5cb85caded":
        errors.append(f"upstream V3.1 registry SHA changed: {upstream_sha}")
    if reg.get("upstream_registry_sha256")!=upstream_sha:
        errors.append("collector registry upstream SHA mismatch")
    if reg.get("status")!="PRELAUNCH_DEPLOYMENT_NOT_VERIFIED":
        errors.append("collector registry must remain prelaunch")
    if reg.get("activation_enabled") is not False:
        errors.append("collector registry activation must be false")
    if reg.get("formal_collection_started") is not False:
        errors.append("formal collection must not be marked started")
    if reg.get("current_collector_dependency") is not False:
        errors.append("CURRENT collector dependency must be false")
    if reg.get("signals") is not False or reg.get("orders") is not False or reg.get("telegram") is not False:
        errors.append("challenger collector must remain research-only")

    if activation.get("enabled") is not False:
        errors.append("activation example must be disabled")
    if activation.get("formal_start_utc")!="2026-10-01T06:00:00Z":
        errors.append("activation example frozen start mismatch")

    for forbidden in (
        "ForwardV3Tracker","self.forward_v3","forwardV3Events",
        "forwardV3Outcomes","forwardV3Health","forwardV3RecoveryRequest"
    ):
        if forbidden in current:
            errors.append(f"CURRENT collector still contains {forbidden}")

    if "from forward_v3_tracker import" not in collector:
        errors.append("independent collector does not import frozen V3.1 tracker")
    if "import market_collector" in collector or "from market_collector" in collector:
        errors.append("independent collector imports market_collector")
    for marker in (
        "challenger_recovery","challenger_incremental",
        "challengerCandidates","challengerOutcomes","challengerHealth",
        "LATE_FIRST_START_BLOCKED_CREATE_NEW_PROTOCOL_START"
    ):
        if marker not in collector:
            errors.append(f"collector missing marker {marker}")

    for marker in (
        "XRP_RECEPTOR_CHALLENGER_V1","CHALLENGER_CANDIDATES",
        "CHALLENGER_OUTCOMES","CHALLENGER_HEALTH",
        "challenger_recovery","challenger_incremental"
    ):
        if marker not in receptor:
            errors.append(f"receptor missing marker {marker}")

    for marker in (
        "**PRELAUNCH — IMPLEMENTED, NOT FORMALLY ACTIVATED**",
        "Candidate stream vs operational stream",
        "LATE_FIRST_START",
        "2026-01-01 → 2026-08-31 remains LOCKED"
    ):
        if marker not in protocol:
            errors.append(f"protocol missing marker {marker}")

    report={
        "version":"XRP_CHALLENGER_COLLECTOR_PRELAUNCH_V1",
        "upstream_registry_sha256":upstream_sha,
        "status":"PASS_PRELAUNCH_NOT_ACTIVATED" if not errors else "FAIL",
        "formal_collection_started":False,
        "errors":errors,
    }
    out=ROOT/"challenger-collector-prelaunch";out.mkdir(exist_ok=True)
    (out/"XRP_CHALLENGER_COLLECTOR_PRELAUNCH_V1.json").write_text(
        json.dumps(report,indent=2),encoding="utf-8"
    )
    print(json.dumps(report,indent=2))
    if errors:
        raise SystemExit(2)


if __name__=="__main__":
    main()
