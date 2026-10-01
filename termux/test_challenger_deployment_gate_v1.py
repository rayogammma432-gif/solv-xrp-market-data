#!/usr/bin/env python3
from __future__ import annotations

from challenger_deployment_gate import validate_config_isolation


def cfg(xrp_url="https://example.com/current/exec", xrp_secret="current-secret",
        challenger_url="https://example.com/challenger/exec", challenger_secret="challenger-secret"):
    return {
        "xrp": {"web_app_url": xrp_url, "shared_secret": xrp_secret},
        "challenger": {"web_app_url": challenger_url, "shared_secret": challenger_secret},
    }


def main():
    assert validate_config_isolation(cfg()) == []

    e = validate_config_isolation(cfg(challenger_url="https://example.com/current/exec"))
    assert "CHALLENGER_URL_EQUALS_CURRENT" in e

    e = validate_config_isolation(cfg(challenger_secret="current-secret"))
    assert "CHALLENGER_SECRET_EQUALS_CURRENT" in e

    e = validate_config_isolation(cfg(challenger_url="PEGA_AQUI_LA_URL_EXEC_DEL_RECEPTOR_CHALLENGER"))
    assert "CHALLENGER_URL_INVALID" in e or "CHALLENGER_CONFIG_STILL_PLACEHOLDER" in e

    e = validate_config_isolation(cfg(challenger_secret=""))
    assert "CHALLENGER_SECRET_MISSING" in e

    print("PASS XRP_CHALLENGER_DEPLOYMENT_GATE_V1")
    print("url_isolation=PASS secret_isolation=PASS placeholder_block=PASS")


if __name__ == "__main__":
    main()
