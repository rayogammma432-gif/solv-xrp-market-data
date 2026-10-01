#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

from xrp_challenger_collector import (
    EXPECTED_CHALLENGER_SPREADSHEET_ID,
    EXPECTED_RECEPTOR_VERSION,
    FORWARD_START_UTC,
    PROTOCOL_VERSION,
    REGISTRY_SHA256,
    validate_activation,
)

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
DEFAULT_CONFIG = HERE / "config.json"
DEFAULT_ACTIVATION = HERE / "challenger_activation.json"
RECEPTOR_FILE = "apps-script/XRP_Challenger_Receptor.gs"
MIN_ACTIVATION_LEAD_SECONDS = 10 * 60


def utc_now():
    return datetime.now(timezone.utc)


def iso_utc(dt):
    return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def git(args):
    p = subprocess.run(
        ["git", *args],
        cwd=str(REPO_ROOT),
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return p.stdout.strip()


def git_head():
    return git(["rev-parse", "HEAD"])


def git_file_commit(path):
    return git(["log", "-1", "--format=%H", "--", path])


def git_tracked_dirty():
    return bool(git(["status", "--porcelain", "--untracked-files=no"]))


def load_config(path):
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise RuntimeError(f"No existe config local: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def validate_config_isolation(data):
    errors = []
    current = data.get("xrp") or {}
    challenger = data.get("challenger") or {}

    c_url = str(current.get("web_app_url") or "").strip()
    c_secret = str(current.get("shared_secret") or "").strip()
    h_url = str(challenger.get("web_app_url") or "").strip()
    h_secret = str(challenger.get("shared_secret") or "").strip()

    if not h_url.startswith("https://") or "/exec" not in h_url:
        errors.append("CHALLENGER_URL_INVALID")
    if not h_secret:
        errors.append("CHALLENGER_SECRET_MISSING")
    if "PEGA_AQUI" in h_url or "PEGA_AQUI" in h_secret:
        errors.append("CHALLENGER_CONFIG_STILL_PLACEHOLDER")
    if c_url and h_url and c_url == h_url:
        errors.append("CHALLENGER_URL_EQUALS_CURRENT")
    if c_secret and h_secret and c_secret == h_secret:
        errors.append("CHALLENGER_SECRET_EQUALS_CURRENT")
    return errors


def probe_receptor(session, cfg, now):
    payload = {
        "secret": str(cfg["challenger"]["shared_secret"]),
        "mode": "challenger_recovery",
        "generatedAtUtc": iso_utc(now),
        "challengerRecoveryRequest": True,
    }
    r = session.post(
        str(cfg["challenger"]["web_app_url"]),
        json=payload,
        timeout=90,
        allow_redirects=True,
    )
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Receptor Challenger respondió error: {data}")
    version = str(data.get("challengerReceptorVersion") or "")
    storage = str(data.get("challengerSpreadsheetId") or "")
    if version != EXPECTED_RECEPTOR_VERSION:
        raise RuntimeError(
            f"RECEPTOR_VERSION_MISMATCH recibido={version!r} esperado={EXPECTED_RECEPTOR_VERSION!r}"
        )
    if storage != EXPECTED_CHALLENGER_SPREADSHEET_ID:
        raise RuntimeError(
            f"RECEPTOR_STORAGE_MISMATCH recibido={storage!r} esperado={EXPECTED_CHALLENGER_SPREADSHEET_ID!r}"
        )
    return {
        "version": version,
        "spreadsheet_id": storage,
        "recovery_present": data.get("challengerRecovery") is not None,
    }


def build_activation(now, head, receptor_commit):
    return {
        "enabled": True,
        "protocol_version": PROTOCOL_VERSION,
        "registry_sha256": REGISTRY_SHA256,
        "formal_start_utc": FORWARD_START_UTC.isoformat().replace("+00:00", "Z"),
        "deployment_verified_utc": iso_utc(now),
        "collector_commit_sha": head,
        "receptor_commit_sha": receptor_commit,
        "receptor_version": EXPECTED_RECEPTOR_VERSION,
        "challenger_spreadsheet_id": EXPECTED_CHALLENGER_SPREADSHEET_ID,
        "notes": (
            "Generated locally only after dedicated receptor/storage probe passed. "
            "Do not edit after runtime marker is created."
        ),
    }


def atomic_write(path, obj):
    p = Path(path)
    if p.exists():
        raise RuntimeError(f"Activation ya existe; no se sobrescribe automáticamente: {p}")
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(
        json.dumps(obj, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(p)


def run(config_path, activation_path, write_activation=False, now_fn=utc_now, session=None):
    now = now_fn()
    seconds_left = (FORWARD_START_UTC - now).total_seconds()
    if seconds_left <= MIN_ACTIVATION_LEAD_SECONDS:
        raise RuntimeError(
            "INSUFFICIENT_PRESTART_MARGIN: quedan "
            f"{max(0, int(seconds_left))}s; mínimo={MIN_ACTIVATION_LEAD_SECONDS}s. "
            "No activar V3.1; crear nueva versión/start."
        )

    if git_tracked_dirty():
        raise RuntimeError("GIT_TRACKED_WORKTREE_DIRTY")

    cfg = load_config(config_path)
    errors = validate_config_isolation(cfg)
    if errors:
        raise RuntimeError("CONFIG_ISOLATION_FAILED: " + ", ".join(errors))

    head = git_head()
    receptor_commit = git_file_commit(RECEPTOR_FILE)

    session = session or requests.Session()
    session.headers.update({"User-Agent": "xrp-challenger-deployment-gate/1.0"})
    receptor = probe_receptor(session, cfg, now)

    activation = build_activation(now, head, receptor_commit)
    activation_errors = validate_activation(
        activation,
        now=now,
        git_sha=head,
        state_exists=False,
        runtime_marker=None,
    )
    if activation_errors:
        raise RuntimeError("ACTIVATION_VALIDATION_FAILED: " + ", ".join(activation_errors))

    result = {
        "status": "PASS_DEPLOYMENT_GATE",
        "verified_utc": iso_utc(now),
        "seconds_to_formal_start": int(seconds_left),
        "formal_start_utc": FORWARD_START_UTC.isoformat().replace("+00:00", "Z"),
        "collector_git_sha": head,
        "receptor_file_commit_sha": receptor_commit,
        "protocol_version": PROTOCOL_VERSION,
        "registry_sha256": REGISTRY_SHA256,
        "receptor_version": receptor["version"],
        "challenger_spreadsheet_id": receptor["spreadsheet_id"],
        "config_isolated_from_current": True,
        "activation_written": False,
    }

    if write_activation:
        atomic_write(activation_path, activation)
        result["activation_written"] = True
        result["activation_path"] = str(Path(activation_path).resolve())

    return result


def main():
    ap = argparse.ArgumentParser(description="Fail-closed XRP Challenger deployment gate")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--activation", default=str(DEFAULT_ACTIVATION))
    ap.add_argument(
        "--write-activation",
        action="store_true",
        help="Write challenger_activation.json only after every pre-start gate passes.",
    )
    args = ap.parse_args()
    try:
        result = run(
            config_path=args.config,
            activation_path=args.activation,
            write_activation=args.write_activation,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
