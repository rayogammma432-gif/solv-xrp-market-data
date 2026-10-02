#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "research/experiments/XRP_FORWARD_REGISTRY_V3_2.jsonl"
REG = ROOT / "research/experiments/XRP_CHALLENGER_COLLECTOR_REGISTRY_V2.json"
PROTOCOL = ROOT / "research/XRP_CHALLENGER_COLLECTOR_PROTOCOL_V2.md"
FORWARD_PROTOCOL = ROOT / "research/XRP_FORWARD_RESEARCH_PROTOCOL_V3_2.md"
COLLECTOR = ROOT / "termux/xrp_challenger_collector.py"
TRACKER = ROOT / "termux/forward_v3_tracker.py"
DEPLOYMENT_GATE = ROOT / "termux/challenger_deployment_gate.py"
CURRENT = ROOT / "termux/market_collector.py"
OPERATIONAL_RECEPTOR = ROOT / "apps-script/XRP_Receptor_Incremental.gs"
CHALLENGER_RECEPTOR = ROOT / "apps-script/XRP_Challenger_Receptor.gs"
CONFIG_EXAMPLE = ROOT / "termux/config.example.json"
ACTIVATION_EXAMPLE = ROOT / "termux/challenger_activation.example.json"
START = ROOT / "termux/start_challenger_collector.sh"
STATUS = ROOT / "termux/status_challenger_collector.sh"
GITIGNORE = ROOT / ".gitignore"

EXPECTED_REGISTRY_SHA = "99c17ecf3c3b376f734dc7469351445c7d6727f96d0cb7d5580ea59b5f9f932a"
EXPECTED_START = "2026-10-02T12:00:00Z"
EXPECTED_PROTOCOL = "XRP_FORWARD_V3_2"
EXPECTED_COLLECTOR = "XRP_CHALLENGER_COLLECTOR_V2_R2"
EXPECTED_RECEPTOR = "XRP_RECEPTOR_CHALLENGER_V2_R3"
EXPECTED_RECEPTOR_BUILD = "XRP_CHALLENGER_RECEPTOR_BUILD_20261002_R3"
EXPECTED_SHEET = "14mVe2XXcsVBCojZSbp6A7qQKO2RFpovLtKntOYFDwvA"


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    errors = []
    upstream_sha = sha256_file(UPSTREAM)
    reg = json.loads(REG.read_text(encoding="utf-8"))
    activation = json.loads(ACTIVATION_EXAMPLE.read_text(encoding="utf-8"))
    protocol = PROTOCOL.read_text(encoding="utf-8")
    forward_protocol = FORWARD_PROTOCOL.read_text(encoding="utf-8")
    collector = COLLECTOR.read_text(encoding="utf-8")
    tracker = TRACKER.read_text(encoding="utf-8")
    deployment_gate = DEPLOYMENT_GATE.read_text(encoding="utf-8")
    current = CURRENT.read_text(encoding="utf-8")
    operational_receptor = OPERATIONAL_RECEPTOR.read_text(encoding="utf-8")
    challenger_receptor = CHALLENGER_RECEPTOR.read_text(encoding="utf-8")
    config_example = json.loads(CONFIG_EXAMPLE.read_text(encoding="utf-8"))
    start = START.read_text(encoding="utf-8")
    status = STATUS.read_text(encoding="utf-8")
    gitignore = GITIGNORE.read_text(encoding="utf-8")

    if upstream_sha != EXPECTED_REGISTRY_SHA:
        errors.append(f"upstream V3.2 registry SHA changed: {upstream_sha}")
    if reg.get("upstream_registry_sha256") != upstream_sha:
        errors.append("collector registry upstream SHA mismatch")
    if reg.get("upstream_protocol") != EXPECTED_PROTOCOL:
        errors.append("collector registry protocol mismatch")
    if reg.get("frozen_forward_start_utc") != EXPECTED_START:
        errors.append("collector registry start mismatch")
    if reg.get("status") != "PRELAUNCH_DEPLOYMENT_NOT_VERIFIED":
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
    if activation.get("formal_start_utc") != EXPECTED_START:
        errors.append("activation example start mismatch")
    if activation.get("protocol_version") != EXPECTED_PROTOCOL:
        errors.append("activation example protocol mismatch")
    if activation.get("registry_sha256") != EXPECTED_REGISTRY_SHA:
        errors.append("activation example registry mismatch")
    if activation.get("receptor_version") != EXPECTED_RECEPTOR:
        errors.append("activation example receptor mismatch")
    if activation.get("receptor_build_id") != EXPECTED_RECEPTOR_BUILD:
        errors.append("activation example receptor build mismatch")
    if activation.get("challenger_spreadsheet_id") != EXPECTED_SHEET:
        errors.append("activation example sheet mismatch")

    for forbidden in (
        "ForwardV3Tracker", "self.forward_v3", "forwardV3Events",
        "forwardV3Outcomes", "forwardV3Health", "forwardV3RecoveryRequest",
    ):
        if forbidden in current:
            errors.append(f"CURRENT collector still contains {forbidden}")

    tree = ast.parse(collector)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    if "market_collector" in imported:
        errors.append("independent collector imports market_collector")

    for marker in (
        EXPECTED_COLLECTOR,
        EXPECTED_RECEPTOR,
        "challenger_ready.json",
        "challenger_heartbeat.json",
        "RUNNING_READY",
        "RUNNING_DEGRADED",
        "RUNTIME_COLLECTOR_GIT_SHA_MISMATCH",
        "LATE_FIRST_START_BLOCKED_CREATE_NEW_PROTOCOL_START",
    ):
        if marker not in collector:
            errors.append(f"collector missing marker {marker}")

    for marker in (
        EXPECTED_PROTOCOL,
        EXPECTED_REGISTRY_SHA,
        "STATE_PROVENANCE_MISMATCH_RESET_REQUIRED",
        "--untracked-files=no",
        "Fail closed on a gap",
        "same-cycle health accounting exact",
        "core.fileMode=false",
    ):
        if marker not in tracker:
            errors.append(f"tracker missing hardening marker {marker}")

    for marker in (
        EXPECTED_RECEPTOR,
        EXPECTED_RECEPTOR_BUILD,
        EXPECTED_PROTOCOL,
        EXPECTED_REGISTRY_SHA,
        EXPECTED_COLLECTOR,
        EXPECTED_SHEET,
        "LockService.getScriptLock",
        "challengerProtocolVersion",
        "challengerRegistrySha256",
        "challengerCollectorVersion",
        "IDEMPOTENCY_CONFLICT",
    ):
        if marker not in challenger_receptor:
            errors.append(f"dedicated receptor missing marker {marker}")

    for forbidden in (
        EXPECTED_RECEPTOR, "challenger_recovery", "challenger_incremental",
        "challengerCandidates", "challengerOutcomes", "challengerHealth",
    ):
        if forbidden in operational_receptor:
            errors.append(f"operational receptor contains Challenger marker {forbidden}")

    if "challenger" not in config_example:
        errors.append("config example missing challenger block")

    for marker in (
        "PASS_DEPLOYMENT_GATE",
        "CURRENT_XRP_URL_MISSING_CANNOT_VERIFY_ISOLATION",
        "STALE_LOCAL_ARTIFACTS_PRESENT_RUN_RESET_FIRST",
        "--reset-local-prelaunch",
        "RESET_BLOCKED_INSUFFICIENT_PRESTART_MARGIN",
        "core.fileMode=false",
        "MIN_ACTIVATION_LEAD_SECONDS = 30 * 60",
        "RECEPTOR_BUILD_ID_MISMATCH",
        "RECEPTOR_PROTOCOL_MISMATCH",
        "RECEPTOR_REGISTRY_MISMATCH",
        "RECEPTOR_COLLECTOR_MISMATCH",
    ):
        if marker not in deployment_gate:
            errors.append(f"deployment gate missing marker {marker}")

    if "RUNNING_READY" not in start:
        errors.append("start script does not wait for readiness")
    if "UNREGISTERED_RUNNING" not in start or "RUNNING_NOT_READY" not in start or "RUNNING_DEGRADED" not in start:
        errors.append("start script does not block discovered duplicate/unready/degraded collector")
    if "--status-json" not in status or "tail -n" in status:
        errors.append("status script is not authoritative machine-readable status")

    for marker in (
        "termux/challenger_ready.json",
        "termux/challenger_heartbeat.json",
        "termux/prelaunch_archive/",
        "termux/config.json.backup",
    ):
        if marker not in gitignore:
            errors.append(f".gitignore missing {marker}")

    for marker in (
        "ABORTED PRELAUNCH / NO VALID FORMAL COLLECTION",
        EXPECTED_START,
        "Git cleanliness semantics",
        "cursor",
        "READY",
        "30 minutes",
    ):
        if marker not in protocol:
            errors.append(f"collector protocol missing marker {marker}")

    for marker in (
        EXPECTED_PROTOCOL,
        EXPECTED_START,
        "2027-03-31T12:00:00Z",
        "2026-12-31T12:00:00Z",
        "evaluation stops at the gap",
    ):
        if marker not in forward_protocol:
            errors.append(f"forward protocol missing marker {marker}")

    report = {
        "version": "XRP_CHALLENGER_COLLECTOR_PRELAUNCH_V2",
        "upstream_registry_sha256": upstream_sha,
        "status": "PASS_PRELAUNCH_NOT_ACTIVATED" if not errors else "FAIL",
        "formal_collection_started": False,
        "errors": errors,
    }
    out = ROOT / "challenger-collector-prelaunch-v2"
    out.mkdir(exist_ok=True)
    (out / "XRP_CHALLENGER_COLLECTOR_PRELAUNCH_V2.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
