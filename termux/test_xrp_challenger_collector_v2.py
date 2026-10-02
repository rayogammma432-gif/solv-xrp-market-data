#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from datetime import timedelta
from pathlib import Path

from xrp_challenger_collector_v2 import (
    COLLECTOR_VERSION,
    EXPECTED_CHALLENGER_SPREADSHEET_ID,
    EXPECTED_RECEPTOR_VERSION,
    FORWARD_START_UTC,
    PROTOCOL_VERSION,
    REGISTRY_SHA256,
    sha256_json,
    validate_activation,
)


def activation(git_sha):
    return {
        "enabled": True,
        "protocol_version": PROTOCOL_VERSION,
        "registry_sha256": REGISTRY_SHA256,
        "formal_start_utc": FORWARD_START_UTC.isoformat().replace("+00:00", "Z"),
        "deployment_verified_utc": (FORWARD_START_UTC - timedelta(hours=2)).isoformat().replace("+00:00", "Z"),
        "collector_commit_sha": git_sha,
        "receptor_commit_sha": "b" * 40,
        "receptor_version": EXPECTED_RECEPTOR_VERSION,
        "challenger_spreadsheet_id": EXPECTED_CHALLENGER_SPREADSHEET_ID,
        "collector_version": COLLECTOR_VERSION,
    }


def main():
    git_sha = "a" * 40
    act = activation(git_sha)

    assert PROTOCOL_VERSION == "XRP_FORWARD_V3_2"
    assert COLLECTOR_VERSION == "XRP_CHALLENGER_COLLECTOR_V2"
    assert EXPECTED_RECEPTOR_VERSION == "XRP_RECEPTOR_CHALLENGER_V2_R1"
    assert FORWARD_START_UTC.isoformat().replace("+00:00","Z") == "2026-10-02T12:00:00Z"

    # Clean pre-start activation.
    errs = validate_activation(
        act,
        now=FORWARD_START_UTC - timedelta(hours=1),
        git_sha=git_sha,
        state_exists=False,
        runtime_marker=None,
    )
    assert errs == [], errs

    # Critical V1 bug regression: state existence NEVER authorizes a late first boot.
    errs = validate_activation(
        act,
        now=FORWARD_START_UTC + timedelta(minutes=1),
        git_sha=git_sha,
        state_exists=True,
        runtime_marker=None,
    )
    assert "LATE_FIRST_START_BLOCKED_CREATE_NEW_PROTOCOL_START" in errs, errs

    # A cryptographically-bound pre-start runtime marker does authorize restart.
    marker = {
        "activation_sha256": sha256_json(act),
        "first_boot_utc": (FORWARD_START_UTC - timedelta(minutes=20)).isoformat().replace("+00:00","Z"),
    }
    errs = validate_activation(
        act,
        now=FORWARD_START_UTC + timedelta(hours=2),
        git_sha=git_sha,
        state_exists=False,
        runtime_marker=marker,
    )
    assert errs == [], errs

    bad = dict(act)
    bad["challenger_spreadsheet_id"] = "wrong"
    errs = validate_activation(
        bad,
        now=FORWARD_START_UTC - timedelta(hours=1),
        git_sha=git_sha,
        state_exists=False,
        runtime_marker=None,
    )
    assert "CHALLENGER_SPREADSHEET_ID_MISMATCH" in errs, errs

    bad = dict(act)
    bad["collector_commit_sha"] = "c" * 40
    errs = validate_activation(
        bad,
        now=FORWARD_START_UTC - timedelta(hours=1),
        git_sha=git_sha,
        state_exists=False,
        runtime_marker=None,
    )
    assert "COLLECTOR_GIT_SHA_MISMATCH" in errs, errs

    # Versioned artifacts: V1 names must not be defaults in V2 source.
    root=Path(__file__).resolve().parents[1]
    src=(root/"termux/xrp_challenger_collector_v2.py").read_text(encoding="utf-8")
    for required in (
        "challenger_v2_activation.json",
        "challenger_v2_runtime.json",
        "challenger_v2_forward_state.json",
        "challenger_v2_heartbeat.json",
        "from forward_v3_2_tracker import",
    ):
        assert required in src, required

    print("PASS XRP_CHALLENGER_COLLECTOR_V2")
    print("late_state_bypass=BLOCKED runtime_restart=PASS storage_identity=PASS versioned_artifacts=PASS")


if __name__ == "__main__":
    main()
