#!/usr/bin/env python3
from __future__ import annotations

import os
import tempfile
from datetime import timedelta
from pathlib import Path

import challenger_deployment_gate as gate
from challenger_deployment_gate import (
    MIN_ACTIVATION_LEAD_SECONDS,
    REPO_ROOT,
    git_tracked_dirty,
    validate_config_isolation,
)
from xrp_challenger_collector import FORWARD_START_UTC


def cfg(
    xrp_url="https://example.com/current/exec",
    xrp_secret="current-secret",
    challenger_url="https://example.com/challenger/exec",
    challenger_secret="challenger-secret",
):
    return {
        "xrp": {"web_app_url": xrp_url, "shared_secret": xrp_secret},
        "challenger": {
            "web_app_url": challenger_url,
            "shared_secret": challenger_secret,
        },
    }


def test_config_isolation():
    assert validate_config_isolation(cfg()) == []

    e = validate_config_isolation(cfg(challenger_url="https://example.com/current/exec"))
    assert "CHALLENGER_URL_EQUALS_CURRENT" in e

    e = validate_config_isolation(cfg(challenger_secret="current-secret"))
    assert "CHALLENGER_SECRET_EQUALS_CURRENT" in e

    e = validate_config_isolation(cfg(challenger_url="PEGA_AQUI_LA_URL_EXEC_DEL_RECEPTOR_CHALLENGER"))
    assert "CHALLENGER_URL_INVALID" in e or "CHALLENGER_CONFIG_STILL_PLACEHOLDER" in e

    e = validate_config_isolation(cfg(challenger_secret=""))
    assert "CHALLENGER_SECRET_MISSING" in e

    e = validate_config_isolation({
        "xrp": {},
        "challenger": {
            "web_app_url": "https://example.com/challenger/exec",
            "shared_secret": "challenger-secret",
        },
    })
    assert "CURRENT_XRP_URL_MISSING_CANNOT_VERIFY_ISOLATION" in e
    assert "CURRENT_XRP_SECRET_MISSING_CANNOT_VERIFY_ISOLATION" in e



def test_git_cleanliness_semantics():
    # Android/Termux chmod-only changes must not invalidate deployment.
    sh = Path(REPO_ROOT) / "termux/start_collector.sh"
    original_mode = sh.stat().st_mode
    try:
        os.chmod(sh, original_mode | 0o111)
        assert git_tracked_dirty() is False, "chmod-only change incorrectly marked dirty"
    finally:
        os.chmod(sh, original_mode)

    # Tracked content changes still fail closed.
    readme = Path(REPO_ROOT) / "termux/README.md"
    original = readme.read_text(encoding="utf-8")
    try:
        readme.write_text(original + "\nV2_TRACKED_CONTENT_DIRTY_TEST\n", encoding="utf-8")
        assert git_tracked_dirty() is True, "tracked content change was not detected"
    finally:
        readme.write_text(original, encoding="utf-8")
    assert git_tracked_dirty() is False


def test_minimum_lead():
    assert MIN_ACTIVATION_LEAD_SECONDS == 30 * 60

def test_safe_prelaunch_reset():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        here = root / "termux"
        here.mkdir()
        logs = here / "logs"
        logs.mkdir()
        archive = here / "prelaunch_archive"

        old = {
            "HERE": gate.HERE,
            "ARCHIVE_ROOT": gate.ARCHIVE_ROOT,
            "DEFAULT_RUNTIME": gate.DEFAULT_RUNTIME,
            "DEFAULT_STATE": gate.DEFAULT_STATE,
            "DEFAULT_READY": gate.DEFAULT_READY,
            "DEFAULT_HEARTBEAT": gate.DEFAULT_HEARTBEAT,
            "DEFAULT_PID": gate.DEFAULT_PID,
        }
        try:
            gate.HERE = here
            gate.ARCHIVE_ROOT = archive
            gate.DEFAULT_RUNTIME = here / "challenger_runtime.json"
            gate.DEFAULT_STATE = here / "challenger_forward_state.json"
            gate.DEFAULT_READY = here / "challenger_ready.json"
            gate.DEFAULT_HEARTBEAT = here / "challenger_heartbeat.json"
            gate.DEFAULT_PID = here / "challenger_collector.pid"
            activation = here / "challenger_activation.json"

            for p in [
                activation,
                gate.DEFAULT_RUNTIME,
                gate.DEFAULT_STATE,
                gate.DEFAULT_READY,
                gate.DEFAULT_HEARTBEAT,
            ]:
                p.write_text("{}\n", encoding="utf-8")
            gate.DEFAULT_PID.write_text("99999999\n", encoding="utf-8")
            (logs / "challenger_collector.log").write_text("old\n", encoding="utf-8")
            (logs / "challenger_stdout.log").write_text("old\n", encoding="utf-8")

            result = gate.reset_local_prelaunch(
                activation_path=activation,
                now_fn=lambda: FORWARD_START_UTC - timedelta(hours=2),
            )
            assert result["status"] == "RESET_PRELAUNCH_OK"
            assert len(result["archived"]) == 8, result
            for p in [
                activation,
                gate.DEFAULT_RUNTIME,
                gate.DEFAULT_STATE,
                gate.DEFAULT_READY,
                gate.DEFAULT_HEARTBEAT,
                gate.DEFAULT_PID,
                logs / "challenger_collector.log",
                logs / "challenger_stdout.log",
            ]:
                assert not p.exists(), p
            assert archive.exists()

            try:
                gate.reset_local_prelaunch(
                    activation_path=activation,
                    now_fn=lambda: FORWARD_START_UTC - timedelta(minutes=5),
                )
            except RuntimeError as exc:
                assert "RESET_BLOCKED_INSUFFICIENT_PRESTART_MARGIN" in str(exc)
            else:
                raise AssertionError("reset inside final safety window must fail")
        finally:
            for k, v in old.items():
                setattr(gate, k, v)


def main():
    test_config_isolation()
    test_git_cleanliness_semantics()
    test_minimum_lead()
    test_safe_prelaunch_reset()
    print("PASS XRP_CHALLENGER_DEPLOYMENT_GATE_V2")
    print("url_isolation=PASS secret_isolation=PASS current_presence=PASS chmod_noise=IGNORED tracked_content=BLOCKED lead_30m=PASS safe_reset=PASS")


if __name__ == "__main__":
    main()
