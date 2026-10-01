#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from datetime import timedelta
from pathlib import Path

from xrp_challenger_collector import (
    COLLECTOR_VERSION,
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
        "deployment_verified_utc": (FORWARD_START_UTC - timedelta(hours=1))
        .isoformat()
        .replace("+00:00", "Z"),
        "collector_commit_sha": git_sha,
        "receptor_commit_sha": "b" * 40,
        "receptor_version": EXPECTED_RECEPTOR_VERSION,
    }


def main():
    git_sha = "a" * 40
    act = activation(git_sha)

    # Valid pre-start first boot.
    errs = validate_activation(
        act,
        now=FORWARD_START_UTC - timedelta(minutes=30),
        git_sha=git_sha,
        state_exists=False,
        runtime_marker=None,
    )
    assert errs == [], errs

    # Late first boot without any pre-start marker/state must fail closed.
    errs = validate_activation(
        act,
        now=FORWARD_START_UTC + timedelta(minutes=1),
        git_sha=git_sha,
        state_exists=False,
        runtime_marker=None,
    )
    assert "LATE_FIRST_START_BLOCKED_CREATE_NEW_PROTOCOL_START" in errs, errs

    # A pre-start runtime marker permits post-start restart/recovery.
    marker = {
        "activation_sha256": sha256_json(act),
        "first_boot_utc": (FORWARD_START_UTC - timedelta(minutes=20))
        .isoformat()
        .replace("+00:00", "Z"),
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
    bad["enabled"] = False
    errs = validate_activation(
        bad,
        now=FORWARD_START_UTC - timedelta(minutes=30),
        git_sha=git_sha,
        state_exists=False,
        runtime_marker=None,
    )
    assert "ACTIVATION_NOT_ENABLED" in errs

    bad = dict(act)
    bad["registry_sha256"] = "0" * 64
    errs = validate_activation(
        bad,
        now=FORWARD_START_UTC - timedelta(minutes=30),
        git_sha=git_sha,
        state_exists=False,
        runtime_marker=None,
    )
    assert "REGISTRY_SHA_MISMATCH" in errs

    bad = dict(act)
    bad["deployment_verified_utc"] = FORWARD_START_UTC.isoformat().replace("+00:00", "Z")
    errs = validate_activation(
        bad,
        now=FORWARD_START_UTC - timedelta(minutes=30),
        git_sha=git_sha,
        state_exists=False,
        runtime_marker=None,
    )
    assert "DEPLOYMENT_NOT_VERIFIED_BEFORE_FORMAL_START" in errs

    bad = dict(act)
    bad["collector_commit_sha"] = "c" * 40
    errs = validate_activation(
        bad,
        now=FORWARD_START_UTC - timedelta(minutes=30),
        git_sha=git_sha,
        state_exists=False,
        runtime_marker=None,
    )
    assert "COLLECTOR_GIT_SHA_MISMATCH" in errs

    root = Path(__file__).resolve().parents[1]
    current_src = (root / "termux/market_collector.py").read_text(encoding="utf-8")
    challenger_src = (root / "termux/xrp_challenger_collector.py").read_text(encoding="utf-8")
    receptor_src = (root / "apps-script/XRP_Receptor_Incremental.gs").read_text(encoding="utf-8")

    # Operational separation: CURRENT collector no longer runs the Challenger tracker.
    for forbidden in (
        "ForwardV3Tracker",
        "self.forward_v3",
        "forwardV3Events",
        "forwardV3Outcomes",
        "forwardV3Health",
        "forwardV3RecoveryRequest",
    ):
        assert forbidden not in current_src, forbidden

    assert "import market_collector" not in challenger_src
    assert "from market_collector" not in challenger_src
    assert 'mode": "challenger_incremental"' in challenger_src
    assert '"challengerCandidates"' in challenger_src
    assert '"challengerOutcomes"' in challenger_src
    assert '"challengerHealth"' in challenger_src
    assert '"challengerRecoveryRequest"' in challenger_src

    assert "XRP_RECEPTOR_CHALLENGER_V1" in receptor_src
    assert "CHALLENGER_CANDIDATES" in receptor_src
    assert "CHALLENGER_OUTCOMES" in receptor_src
    assert "CHALLENGER_HEALTH" in receptor_src
    assert "challenger_recovery" in receptor_src
    assert "challenger_incremental" in receptor_src

    assert COLLECTOR_VERSION == "XRP_CHALLENGER_COLLECTOR_V1"

    print("PASS XRP_CHALLENGER_INDEPENDENT_COLLECTOR_V1")
    print(
        "activation_guard=PASS late_start_block=PASS restart_recovery=PASS "
        "current_detached=PASS receptor_isolation=PASS"
    )


if __name__ == "__main__":
    main()
