#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
from datetime import timedelta
from pathlib import Path

from xrp_challenger_collector import (
    COLLECTOR_VERSION,
    EXPECTED_CHALLENGER_SPREADSHEET_ID,
    EXPECTED_RECEPTOR_VERSION,
    EXPECTED_RECEPTOR_BUILD_ID,
    FORWARD_START_UTC,
    PROTOCOL_VERSION,
    REGISTRY_SHA256,
    sha256_json,
    validate_activation,
    _heartbeat_allows_ready,
)


def activation(git_sha):
    return {
        "enabled": True,
        "protocol_version": PROTOCOL_VERSION,
        "registry_sha256": REGISTRY_SHA256,
        "formal_start_utc": FORWARD_START_UTC.isoformat().replace("+00:00", "Z"),
        "deployment_verified_utc": (FORWARD_START_UTC - timedelta(hours=1))
        .isoformat()
        .replace("+00:00", "Z"),
        "collector_commit_sha": git_sha,
        "receptor_commit_sha": "b" * 40,
        "receptor_version": EXPECTED_RECEPTOR_VERSION,
        "receptor_build_id": EXPECTED_RECEPTOR_BUILD_ID,
        "challenger_spreadsheet_id": EXPECTED_CHALLENGER_SPREADSHEET_ID,
    }


def runtime_marker(act, git_sha):
    return {
        "activation_sha256": sha256_json(act),
        "first_boot_utc": (FORWARD_START_UTC - timedelta(minutes=20))
        .isoformat()
        .replace("+00:00", "Z"),
        "formal_start_utc": FORWARD_START_UTC.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "protocol_version": PROTOCOL_VERSION,
        "registry_sha256": REGISTRY_SHA256,
        "collector_version": COLLECTOR_VERSION,
        "collector_git_sha": git_sha,
    }


def main():
    git_sha = "a" * 40
    act = activation(git_sha)

    errs = validate_activation(
        act,
        now=FORWARD_START_UTC - timedelta(minutes=30),
        git_sha=git_sha,
        state_exists=False,
        runtime_marker=None,
    )
    assert errs == [], errs

    # State never substitutes for a pre-start runtime marker.
    for state_exists in (False, True):
        errs = validate_activation(
            act,
            now=FORWARD_START_UTC + timedelta(minutes=1),
            git_sha=git_sha,
            state_exists=state_exists,
            runtime_marker=None,
        )
        assert "LATE_FIRST_START_BLOCKED_CREATE_NEW_PROTOCOL_START" in errs, errs

    marker = runtime_marker(act, git_sha)
    errs = validate_activation(
        act,
        now=FORWARD_START_UTC + timedelta(hours=2),
        git_sha=git_sha,
        state_exists=False,
        runtime_marker=marker,
    )
    assert errs == [], errs

    bad_marker = dict(marker)
    bad_marker["collector_git_sha"] = "c" * 40
    errs = validate_activation(
        act,
        now=FORWARD_START_UTC + timedelta(hours=2),
        git_sha=git_sha,
        state_exists=False,
        runtime_marker=bad_marker,
    )
    assert "RUNTIME_COLLECTOR_GIT_SHA_MISMATCH" in errs

    bad = dict(act)
    bad["enabled"] = False
    assert "ACTIVATION_NOT_ENABLED" in validate_activation(
        bad, now=FORWARD_START_UTC - timedelta(minutes=30),
        git_sha=git_sha, state_exists=False, runtime_marker=None
    )

    bad = dict(act)
    bad["registry_sha256"] = "0" * 64
    assert "REGISTRY_SHA_MISMATCH" in validate_activation(
        bad, now=FORWARD_START_UTC - timedelta(minutes=30),
        git_sha=git_sha, state_exists=False, runtime_marker=None
    )

    bad = dict(act)
    bad["challenger_spreadsheet_id"] = "wrong"
    assert "SPREADSHEET_ID_MISMATCH" in validate_activation(
        bad, now=FORWARD_START_UTC - timedelta(minutes=30),
        git_sha=git_sha, state_exists=False, runtime_marker=None
    )

    bad = dict(act)
    bad["collector_commit_sha"] = "c" * 40
    assert "COLLECTOR_GIT_SHA_MISMATCH" in validate_activation(
        bad, now=FORWARD_START_UTC - timedelta(minutes=30),
        git_sha=git_sha, state_exists=False, runtime_marker=None
    )

    root = Path(__file__).resolve().parents[1]
    current_src = (root / "termux/market_collector.py").read_text(encoding="utf-8")
    challenger_src = (root / "termux/xrp_challenger_collector.py").read_text(encoding="utf-8")
    tracker_src = (root / "termux/forward_v3_tracker.py").read_text(encoding="utf-8")
    start_src = (root / "termux/start_challenger_collector.sh").read_text(encoding="utf-8")
    status_src = (root / "termux/status_challenger_collector.sh").read_text(encoding="utf-8")
    receptor_src = (root / "apps-script/XRP_Challenger_Receptor.gs").read_text(encoding="utf-8")
    operational_receptor_src = (root / "apps-script/XRP_Receptor_Incremental.gs").read_text(encoding="utf-8")
    config_example = json.loads((root / "termux/config.example.json").read_text(encoding="utf-8"))

    for forbidden in (
        "ForwardV3Tracker", "self.forward_v3", "forwardV3Events",
        "forwardV3Outcomes", "forwardV3Health", "forwardV3RecoveryRequest",
    ):
        assert forbidden not in current_src, forbidden

    tree = ast.parse(challenger_src)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert "market_collector" not in imported

    for marker_text in (
        "challenger_ready.json",
        "challenger_heartbeat.json",
        "RUNNING_READY",
        "RUNTIME_COLLECTOR_GIT_SHA_MISMATCH",
        "LATE_FIRST_START_BLOCKED_CREATE_NEW_PROTOCOL_START",
        "COLLECTOR_SOURCE_CHANGED_DURING_RUNTIME",
        "RECEPTOR_IDENTITY_MISMATCH",
        "UNREGISTERED_RUNNING",
        "HEARTBEAT_STALE_SECONDS",
    ):
        assert marker_text in challenger_src, marker_text

    assert '--untracked-files=no' in tracker_src
    assert 'RUNNING_READY' in start_src
    assert 'UNREGISTERED_RUNNING' in start_src
    assert 'RUNNING_NOT_READY' in start_src
    assert 'RUNNING_DEGRADED' in start_src
    assert '--status-json' in start_src
    assert '--status-json' in status_src
    assert 'tail -n' not in status_src

    for marker_text in (
        "XRP_RECEPTOR_CHALLENGER_V2_R3",
        "XRP_CHALLENGER_RECEPTOR_BUILD_20261002_R3",
        "XRP_FORWARD_V3_2",
        "XRP_CHALLENGER_COLLECTOR_V2_R2",
        "99c17ecf3c3b376f734dc7469351445c7d6727f96d0cb7d5580ea59b5f9f932a",
        "LockService.getScriptLock",
        "challengerProtocolVersion",
        "challengerRegistrySha256",
        "challengerCollectorVersion",
        "IDEMPOTENCY_CONFLICT",
    ):
        assert marker_text in receptor_src, marker_text

    for forbidden in (
        "XRP_RECEPTOR_CHALLENGER_V2_R2",
        "challenger_recovery",
        "challenger_incremental",
        "challengerCandidates",
        "challengerOutcomes",
        "challengerHealth",
    ):
        assert forbidden not in operational_receptor_src, forbidden

    assert "challenger" in config_example
    assert COLLECTOR_VERSION == "XRP_CHALLENGER_COLLECTOR_V2_R2"
    assert PROTOCOL_VERSION == "XRP_FORWARD_V3_2"

    assert _heartbeat_allows_ready({"status": "STARTUP_READY"}) is True
    assert _heartbeat_allows_ready({"status": "CYCLE_OK"}) is True
    assert _heartbeat_allows_ready({"status": "CYCLE_ERROR"}) is False
    assert _heartbeat_allows_ready({"status": "GLOBAL_ERROR"}) is False

    print("PASS XRP_CHALLENGER_INDEPENDENT_COLLECTOR_V2")
    print(
        "activation_guard=PASS late_start=PASS runtime_binding=PASS "
        "git_semantics=PASS readiness=PASS heartbeat=PASS process_discovery=PASS runtime_revalidation=PASS degraded_cycle_readiness=PASS receptor_identity=PASS receptor_build=PASS receptor_lock=PASS isolation=PASS"
    )


if __name__ == "__main__":
    main()
