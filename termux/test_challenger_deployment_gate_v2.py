#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

from challenger_deployment_gate_v2 import (
    REPO_ROOT,
    git_tracked_dirty,
    validate_config_isolation,
)


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


def main():
    assert validate_config_isolation(cfg()) == []

    e=validate_config_isolation(cfg(challenger_url="https://example.com/current/exec"))
    assert "CHALLENGER_URL_EQUALS_CURRENT" in e

    e=validate_config_isolation(cfg(challenger_secret="current-secret"))
    assert "CHALLENGER_SECRET_EQUALS_CURRENT" in e

    e=validate_config_isolation(cfg(challenger_url="PEGA_AQUI_URL"))
    assert "CHALLENGER_URL_INVALID" in e or "CHALLENGER_CONFIG_STILL_PLACEHOLDER" in e

    # Regression: Android/Termux chmod-only changes must not block deployment.
    sh=Path(REPO_ROOT)/"termux/start_collector.sh"
    original_mode=sh.stat().st_mode
    try:
        os.chmod(sh, original_mode | 0o111)
        assert git_tracked_dirty() is False, "mode-only change incorrectly marked dirty"
    finally:
        os.chmod(sh, original_mode)

    # But tracked content changes MUST fail closed.
    readme=Path(REPO_ROOT)/"termux/README.md"
    original=readme.read_text(encoding="utf-8")
    try:
        readme.write_text(original+"\nV2_DIRTY_TEST\n", encoding="utf-8")
        assert git_tracked_dirty() is True, "tracked content change was not detected"
    finally:
        readme.write_text(original, encoding="utf-8")

    assert git_tracked_dirty() is False

    print("PASS XRP_CHALLENGER_DEPLOYMENT_GATE_V2")
    print("url_isolation=PASS secret_isolation=PASS chmod_noise=IGNORED tracked_content=BLOCKED")


if __name__ == "__main__":
    main()
