#!/usr/bin/env python3
"""
Independent XRP Challenger candidate collector.

This process is intentionally separate from market_collector.py.
It owns its state, recovery, health, retries and Google Sheets streams.

It implements the frozen XRP_FORWARD_V3_2 research rules through
ForwardV3Tracker. It creates research candidates/outcomes only; never SIGNALS,
orders, Telegram trade alerts or CURRENT-agent decisions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

from forward_v3_tracker import (
    FORWARD_START_UTC,
    PROTOCOL_VERSION,
    REGISTRY_SHA256,
    ForwardV3Tracker,
    current_git_sha,
)

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "config.json"
DEFAULT_ACTIVATION = HERE / "challenger_activation.json"
DEFAULT_STATE = HERE / "challenger_forward_state.json"
DEFAULT_RUNTIME = HERE / "challenger_runtime.json"
DEFAULT_READY = HERE / "challenger_ready.json"
DEFAULT_HEARTBEAT = HERE / "challenger_heartbeat.json"
DEFAULT_PID = HERE / "challenger_collector.pid"
LOG_DIR = HERE / "logs"
LOG_DIR.mkdir(exist_ok=True)

COLLECTOR_VERSION = "XRP_CHALLENGER_COLLECTOR_V2_R2"
EXPECTED_RECEPTOR_VERSION = "XRP_RECEPTOR_CHALLENGER_V2_R3"
EXPECTED_RECEPTOR_BUILD_ID = "XRP_CHALLENGER_RECEPTOR_BUILD_20261002_R3"
EXPECTED_CHALLENGER_SPREADSHEET_ID = "14mVe2XXcsVBCojZSbp6A7qQKO2RFpovLtKntOYFDwvA"
CYCLE_SECOND = 8
HEARTBEAT_STALE_SECONDS = 180

logger = logging.getLogger("xrp_challenger_collector")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fmt = logging.Formatter("%(asctime)sZ %(levelname)s %(message)s", "%Y-%m-%dT%H:%M:%S")
    fh = RotatingFileHandler(
        LOG_DIR / "challenger_collector.log",
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)


def utc_now():
    return datetime.now(timezone.utc)


def utc_iso(dt=None):
    dt = utc_now() if dt is None else dt.astimezone(timezone.utc)
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_utc(value):
    if not value:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)


def sha256_json(obj):
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_xrp_config(path):
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise RuntimeError(f"No existe config: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    item = data.get("challenger") or {}
    url = str(item.get("web_app_url", "")).strip()
    secret = str(item.get("shared_secret", "")).strip()
    if not url.startswith("https://") or "/exec" not in url:
        raise RuntimeError("challenger.web_app_url inválida o ausente")
    if not secret:
        raise RuntimeError("challenger.shared_secret ausente")
    return {"web_app_url": url, "shared_secret": secret}


def load_json(path):
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def save_json_atomic(path, obj):
    p = Path(path)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(
        json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )
    tmp.replace(p)


def post_json(session, url, payload, tries=3):
    last = None
    for attempt in range(1, tries + 1):
        try:
            r = session.post(url, json=payload, timeout=90, allow_redirects=True)
            r.raise_for_status()
            data = r.json()
            if not data.get("ok"):
                raise RuntimeError(f"Receptor respondió error: {data.get('error', data)}")
            return data
        except Exception as exc:
            last = exc
            if attempt < tries:
                time.sleep(3 * attempt)
    raise RuntimeError(f"POST falló tras {tries} intentos: {last}")


def validate_activation(
    activation,
    *,
    now,
    git_sha,
    state_exists,
    runtime_marker,
):
    errors = []
    if not isinstance(activation, dict):
        return ["ACTIVATION_FILE_MISSING_OR_INVALID"]

    if activation.get("enabled") is not True:
        errors.append("ACTIVATION_NOT_ENABLED")
    if activation.get("protocol_version") != PROTOCOL_VERSION:
        errors.append("PROTOCOL_VERSION_MISMATCH")
    if activation.get("registry_sha256") != REGISTRY_SHA256:
        errors.append("REGISTRY_SHA_MISMATCH")
    if activation.get("receptor_version") != EXPECTED_RECEPTOR_VERSION:
        errors.append("RECEPTOR_VERSION_MISMATCH")
    if activation.get("receptor_build_id") != EXPECTED_RECEPTOR_BUILD_ID:
        errors.append("RECEPTOR_BUILD_ID_MISMATCH")
    if activation.get("challenger_spreadsheet_id") != EXPECTED_CHALLENGER_SPREADSHEET_ID:
        errors.append("SPREADSHEET_ID_MISMATCH")

    try:
        formal_start = parse_utc(activation.get("formal_start_utc"))
    except Exception:
        formal_start = None
        errors.append("FORMAL_START_INVALID")
    if formal_start != FORWARD_START_UTC:
        errors.append("FORMAL_START_DOES_NOT_MATCH_FROZEN_V3_2")

    try:
        verified = parse_utc(activation.get("deployment_verified_utc"))
    except Exception:
        verified = None
        errors.append("DEPLOYMENT_VERIFIED_UTC_INVALID")
    if formal_start and (verified is None or verified >= formal_start):
        errors.append("DEPLOYMENT_NOT_VERIFIED_BEFORE_FORMAL_START")

    expected_git = str(activation.get("collector_commit_sha") or "")
    if not expected_git or expected_git != git_sha:
        errors.append("COLLECTOR_GIT_SHA_MISMATCH")
    if git_sha.endswith("+DIRTY") or git_sha == "UNKNOWN":
        errors.append("COLLECTOR_WORKTREE_NOT_CLEAN")

    marker = runtime_marker if isinstance(runtime_marker, dict) else None
    if marker is not None:
        if marker.get("activation_sha256") != sha256_json(activation):
            errors.append("RUNTIME_ACTIVATION_HASH_MISMATCH")
        if marker.get("protocol_version") != PROTOCOL_VERSION:
            errors.append("RUNTIME_PROTOCOL_MISMATCH")
        if marker.get("registry_sha256") != REGISTRY_SHA256:
            errors.append("RUNTIME_REGISTRY_MISMATCH")
        if marker.get("collector_version") != COLLECTOR_VERSION:
            errors.append("RUNTIME_COLLECTOR_VERSION_MISMATCH")
        if marker.get("collector_git_sha") != git_sha:
            errors.append("RUNTIME_COLLECTOR_GIT_SHA_MISMATCH")
        if marker.get("formal_start_utc") != utc_iso(FORWARD_START_UTC):
            errors.append("RUNTIME_FORMAL_START_MISMATCH")
        try:
            first_boot = parse_utc(marker.get("first_boot_utc"))
        except Exception:
            first_boot = None
            errors.append("RUNTIME_FIRST_BOOT_INVALID")
        if formal_start and (first_boot is None or first_boot >= formal_start):
            errors.append("RUNTIME_FIRST_BOOT_NOT_PRESTART")
    elif formal_start and now >= formal_start:
        # State alone never authorizes a late first boot. A valid pre-start
        # runtime marker is mandatory.
        errors.append("LATE_FIRST_START_BLOCKED_CREATE_NEW_PROTOCOL_START")

    return errors


class ChallengerCollector:
    def __init__(
        self,
        config_path=DEFAULT_CONFIG,
        activation_path=DEFAULT_ACTIVATION,
        state_path=DEFAULT_STATE,
        runtime_path=DEFAULT_RUNTIME,
        ready_path=DEFAULT_READY,
        heartbeat_path=DEFAULT_HEARTBEAT,
        now_fn=utc_now,
    ):
        self.cfg = load_xrp_config(config_path)
        self.activation_path = Path(activation_path)
        self.state_path = Path(state_path)
        self.runtime_path = Path(runtime_path)
        self.ready_path = Path(ready_path)
        self.heartbeat_path = Path(heartbeat_path)
        self.now_fn = now_fn
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "xrp-challenger-collector/1.0"})
        self.git_sha = current_git_sha()
        self.tracker = ForwardV3Tracker(
            state_path=self.state_path,
            now_fn=self.now_fn,
            collector_version=COLLECTOR_VERSION,
        )

    def activation(self):
        return load_json(self.activation_path)

    def runtime_marker(self):
        return load_json(self.runtime_path)

    def validate_live_activation(self):
        act = self.activation()
        errors = validate_activation(
            act,
            now=self.now_fn(),
            git_sha=self.git_sha,
            state_exists=self.state_path.exists(),
            runtime_marker=self.runtime_marker(),
        )
        if errors:
            raise RuntimeError("Challenger activation bloqueada: " + ", ".join(errors))
        return act

    def ensure_runtime_marker(self, activation):
        marker = self.runtime_marker()
        if marker:
            return marker
        now = self.now_fn()
        if now >= FORWARD_START_UTC:
            raise RuntimeError(
                "Primer arranque Challenger ocurrió después del start congelado; "
                "no se permite backfill prospectivo. Crear nueva versión/start."
            )
        marker = {
            "first_boot_utc": utc_iso(now),
            "formal_start_utc": utc_iso(FORWARD_START_UTC),
            "protocol_version": PROTOCOL_VERSION,
            "registry_sha256": REGISTRY_SHA256,
            "collector_version": COLLECTOR_VERSION,
            "collector_git_sha": self.git_sha,
            "activation_sha256": sha256_json(activation),
        }
        save_json_atomic(self.runtime_path, marker)
        return marker

    def write_ready_marker(self, activation, receptor_response):
        marker = {
            "ready_utc": utc_iso(self.now_fn()),
            "pid": os.getpid(),
            "protocol_version": PROTOCOL_VERSION,
            "registry_sha256": REGISTRY_SHA256,
            "formal_start_utc": utc_iso(FORWARD_START_UTC),
            "collector_version": COLLECTOR_VERSION,
            "collector_git_sha": self.git_sha,
            "activation_sha256": sha256_json(activation),
            "receptor_version": str(receptor_response.get("challengerReceptorVersion") or ""),
            "receptor_build_id": str(receptor_response.get("challengerReceptorBuildId") or ""),
            "challenger_spreadsheet_id": str(receptor_response.get("challengerSpreadsheetId") or ""),
        }
        save_json_atomic(self.ready_path, marker)
        return marker

    def write_heartbeat(self, status, detail=None):
        payload = {
            "heartbeat_utc": utc_iso(self.now_fn()),
            "pid": os.getpid(),
            "status": str(status),
            "protocol_version": PROTOCOL_VERSION,
            "collector_version": COLLECTOR_VERSION,
            "collector_git_sha": self.git_sha,
        }
        if detail is not None:
            payload["detail"] = detail
        save_json_atomic(self.heartbeat_path, payload)

    @staticmethod
    def validate_receptor_identity(response):
        received = {
            "receptor_version": str(response.get("challengerReceptorVersion") or ""),
            "receptor_build_id": str(response.get("challengerReceptorBuildId") or ""),
            "spreadsheet_id": str(response.get("challengerSpreadsheetId") or ""),
            "protocol_version": str(response.get("challengerProtocolVersion") or ""),
            "registry_sha256": str(response.get("challengerRegistrySha256") or ""),
            "collector_version": str(response.get("challengerCollectorVersion") or ""),
        }
        expected = {
            "receptor_version": EXPECTED_RECEPTOR_VERSION,
            "receptor_build_id": EXPECTED_RECEPTOR_BUILD_ID,
            "spreadsheet_id": EXPECTED_CHALLENGER_SPREADSHEET_ID,
            "protocol_version": PROTOCOL_VERSION,
            "registry_sha256": REGISTRY_SHA256,
            "collector_version": COLLECTOR_VERSION,
        }
        mismatches = [
            f"{key}={received[key]!r} expected={expected[key]!r}"
            for key in expected
            if received[key] != expected[key]
        ]
        if mismatches:
            raise RuntimeError("RECEPTOR_IDENTITY_MISMATCH: " + "; ".join(mismatches))
        return received

    def validate_runtime_integrity(self):
        live_git = current_git_sha()
        if live_git != self.git_sha:
            raise RuntimeError(
                f"COLLECTOR_SOURCE_CHANGED_DURING_RUNTIME: boot={self.git_sha} live={live_git}"
            )
        act = self.activation()
        errors = validate_activation(
            act,
            now=self.now_fn(),
            git_sha=live_git,
            state_exists=self.state_path.exists(),
            runtime_marker=self.runtime_marker(),
        )
        if errors:
            raise RuntimeError(
                "RUNTIME_INTEGRITY_BLOCKED: " + ", ".join(errors)
            )
        return act

    def receptor_recovery(self):
        payload = {
            "secret": self.cfg["shared_secret"],
            "mode": "challenger_recovery",
            "generatedAtUtc": utc_iso(self.now_fn()),
            "challengerRecoveryRequest": True,
        }
        response = post_json(self.session, self.cfg["web_app_url"], payload)
        self.validate_receptor_identity(response)
        self.tracker.reconcile_remote(response.get("challengerRecovery"))
        return response

    def cycle(self):
        self.validate_runtime_integrity()
        candidates, outcomes, health = self.tracker.evaluate(self.session)
        if not (candidates or outcomes or health):
            return {
                "candidates": 0,
                "outcomes": 0,
                "health": 0,
                "posted": False,
            }

        payload = {
            "secret": self.cfg["shared_secret"],
            "mode": "challenger_incremental",
            "generatedAtUtc": utc_iso(self.now_fn()),
        }
        if candidates:
            payload["challengerCandidates"] = candidates
        if outcomes:
            payload["challengerOutcomes"] = outcomes
        if health:
            payload["challengerHealth"] = health

        response = post_json(self.session, self.cfg["web_app_url"], payload)
        self.validate_receptor_identity(response)

        self.tracker.ack(
            event_rows=candidates,
            outcome_rows=outcomes,
            health_rows=health,
        )
        return {
            "candidates": len(candidates),
            "outcomes": len(outcomes),
            "health": len(health),
            "posted": True,
        }

    def prelaunch_check(self, check_receptor=False):
        result = {
            "collector_version": COLLECTOR_VERSION,
            "collector_git_sha": self.git_sha,
            "protocol_version": PROTOCOL_VERSION,
            "registry_sha256": REGISTRY_SHA256,
            "frozen_forward_start_utc": utc_iso(FORWARD_START_UTC),
            "activation_file_exists": self.activation_path.exists(),
            "state_file_exists": self.state_path.exists(),
            "runtime_marker_exists": self.runtime_path.exists(),
            "receptor_checked": False,
        }
        act = self.activation()
        if act:
            result["activation_errors"] = validate_activation(
                act,
                now=self.now_fn(),
                git_sha=self.git_sha,
                state_exists=self.state_path.exists(),
                runtime_marker=self.runtime_marker(),
            )
        else:
            result["activation_errors"] = ["ACTIVATION_NOT_CREATED"]

        if check_receptor:
            response = self.receptor_recovery()
            result["receptor_checked"] = True
            result["receptor_version"] = response.get("challengerReceptorVersion")
            result["receptor_build_id"] = response.get("challengerReceptorBuildId")
            result["receptor_spreadsheet_id"] = response.get("challengerSpreadsheetId")
            result["receptor_protocol_version"] = response.get("challengerProtocolVersion")
            result["receptor_registry_sha256"] = response.get("challengerRegistrySha256")
            result["receptor_collector_version"] = response.get("challengerCollectorVersion")
        return result


def sleep_to_cycle_second(now_fn=utc_now):
    now = now_fn()
    target = now.replace(second=CYCLE_SECOND, microsecond=0)
    if target <= now:
        target += timedelta(minutes=1)
    time.sleep(max(0.25, (target - now).total_seconds()))


def _pid_alive(pid):
    try:
        pid = int(pid)
        if pid <= 0:
            return False
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def find_live_collector_pids():
    """Find long-running collector processes even if the PID file is missing."""
    found = []
    proc = Path("/proc")
    if not proc.exists():
        return found
    own = os.getpid()
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid == own:
            continue
        try:
            raw = (entry / "cmdline").read_bytes()
            cmd = raw.replace(b"\x00", b" ").decode("utf-8", errors="ignore")
        except Exception:
            continue
        if "xrp_challenger_collector.py" not in cmd:
            continue
        # Status and prelaunch probes are not the long-running collector.
        if "--status-json" in cmd or "--prelaunch-check" in cmd:
            continue
        if _pid_alive(pid):
            found.append(pid)
    return sorted(set(found))


def _heartbeat_is_fresh(heartbeat, now=None):
    if not isinstance(heartbeat, dict):
        return False
    try:
        ts = parse_utc(heartbeat.get("heartbeat_utc"))
    except Exception:
        return False
    if ts is None:
        return False
    now = utc_now() if now is None else now
    age = (now - ts).total_seconds()
    return -5 <= age <= HEARTBEAT_STALE_SECONDS


def _heartbeat_allows_ready(heartbeat):
    if not isinstance(heartbeat, dict):
        return False
    return str(heartbeat.get("status") or "") in {"STARTUP_READY", "CYCLE_OK"}


def status_snapshot(
    activation_path=DEFAULT_ACTIVATION,
    runtime_path=DEFAULT_RUNTIME,
    state_path=DEFAULT_STATE,
    ready_path=DEFAULT_READY,
    heartbeat_path=DEFAULT_HEARTBEAT,
    pid_path=DEFAULT_PID,
):
    git_sha = current_git_sha()
    activation = load_json(activation_path)
    runtime = load_json(runtime_path)
    ready = load_json(ready_path)
    heartbeat = load_json(heartbeat_path)

    pid = None
    try:
        p = Path(pid_path)
        if p.exists():
            pid = int(p.read_text(encoding="utf-8").strip())
    except Exception:
        pid = None
    running = _pid_alive(pid)
    discovered_pids = find_live_collector_pids()
    unregistered_pids = [x for x in discovered_pids if x != pid]

    activation_errors = validate_activation(
        activation,
        now=utc_now(),
        git_sha=git_sha,
        state_exists=Path(state_path).exists(),
        runtime_marker=runtime,
    )

    heartbeat_fresh = _heartbeat_is_fresh(heartbeat)
    heartbeat_status = str((heartbeat or {}).get("status") or "")
    heartbeat_ok = bool(
        heartbeat_fresh
        and int((heartbeat or {}).get("pid") or -1) == int(pid or -2)
        and _heartbeat_allows_ready(heartbeat)
    )
    ready_valid = bool(
        running
        and not unregistered_pids
        and isinstance(ready, dict)
        and int(ready.get("pid") or -1) == int(pid or -2)
        and isinstance(activation, dict)
        and ready.get("activation_sha256") == sha256_json(activation)
        and ready.get("protocol_version") == PROTOCOL_VERSION
        and ready.get("registry_sha256") == REGISTRY_SHA256
        and ready.get("collector_version") == COLLECTOR_VERSION
        and ready.get("collector_git_sha") == git_sha
        and ready.get("receptor_version") == EXPECTED_RECEPTOR_VERSION
        and ready.get("receptor_build_id") == EXPECTED_RECEPTOR_BUILD_ID
        and ready.get("challenger_spreadsheet_id") == EXPECTED_CHALLENGER_SPREADSHEET_ID
        and heartbeat_ok
        and not activation_errors
    )

    if unregistered_pids:
        status = "UNREGISTERED_RUNNING"
    elif running and ready_valid:
        status = "RUNNING_READY"
    elif running and heartbeat_fresh and heartbeat_status == "CYCLE_ERROR":
        status = "RUNNING_DEGRADED"
    elif running:
        status = "RUNNING_NOT_READY"
    elif pid is not None:
        status = "STALE_PID"
    else:
        status = "STOPPED"

    return {
        "status": status,
        "pid": pid,
        "running": running,
        "discovered_live_pids": discovered_pids,
        "unregistered_live_pids": unregistered_pids,
        "ready": ready_valid,
        "heartbeat_fresh": heartbeat_fresh,
        "heartbeat_status": heartbeat_status,
        "activation_present": Path(activation_path).exists(),
        "runtime_marker_present": Path(runtime_path).exists(),
        "state_present": Path(state_path).exists(),
        "ready_marker_present": Path(ready_path).exists(),
        "heartbeat_present": Path(heartbeat_path).exists(),
        "activation_errors": activation_errors,
        "protocol_version": PROTOCOL_VERSION,
        "formal_start_utc": utc_iso(FORWARD_START_UTC),
        "collector_version": COLLECTOR_VERSION,
        "collector_git_sha": git_sha,
        "ready_marker": ready,
        "heartbeat": heartbeat,
    }


def main():
    ap = argparse.ArgumentParser(description="XRP Challenger independent shadow collector")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--activation", default=str(DEFAULT_ACTIVATION))
    ap.add_argument("--state", default=str(DEFAULT_STATE))
    ap.add_argument("--runtime", default=str(DEFAULT_RUNTIME))
    ap.add_argument("--ready", default=str(DEFAULT_READY))
    ap.add_argument("--heartbeat", default=str(DEFAULT_HEARTBEAT))
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--prelaunch-check", action="store_true")
    ap.add_argument("--check-receptor", action="store_true")
    ap.add_argument("--status-json", action="store_true")
    args = ap.parse_args()

    if args.status_json:
        print(json.dumps(status_snapshot(
            activation_path=args.activation,
            runtime_path=args.runtime,
            state_path=args.state,
            ready_path=args.ready,
            heartbeat_path=args.heartbeat,
        ), indent=2, sort_keys=True))
        return 0

    try:
        collector = ChallengerCollector(
            config_path=args.config,
            activation_path=args.activation,
            state_path=args.state,
            runtime_path=args.runtime,
            ready_path=args.ready,
            heartbeat_path=args.heartbeat,
        )

        if args.prelaunch_check:
            print(json.dumps(
                collector.prelaunch_check(check_receptor=args.check_receptor),
                indent=2,
                sort_keys=True,
            ))
            return 0

        activation = collector.validate_live_activation()
        # A runtime marker proves a full pre-start handshake, not merely that
        # Python started. Receptor identity/recovery must succeed first.
        receptor_response = collector.receptor_recovery()
        collector.ensure_runtime_marker(activation)
        collector.write_ready_marker(activation, receptor_response)
        collector.write_heartbeat("STARTUP_READY")

        if args.once:
            result = collector.cycle()
            collector.write_heartbeat("CYCLE_OK", result)
            logger.info("CHALLENGER ONCE OK: %s", result)
            return 0

        logger.info(
            "CHALLENGER iniciado protocol=%s start=%s git=%s",
            PROTOCOL_VERSION,
            utc_iso(FORWARD_START_UTC),
            collector.git_sha,
        )
        while True:
            try:
                sleep_to_cycle_second()
                result = collector.cycle()
                collector.write_heartbeat("CYCLE_OK", result)
                if result["posted"]:
                    logger.info("CHALLENGER DELTA OK: %s", result)
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                collector.write_heartbeat("CYCLE_ERROR", {"error": str(exc)})
                logger.exception("CHALLENGER ciclo falló: %s", exc)
                time.sleep(15)

    except KeyboardInterrupt:
        logger.info("CHALLENGER detenido por usuario")
        return 0
    except Exception as exc:
        try:
            Path(args.ready).unlink(missing_ok=True)
            save_json_atomic(args.heartbeat, {
                "heartbeat_utc": utc_iso(),
                "pid": os.getpid(),
                "status": "GLOBAL_ERROR",
                "protocol_version": PROTOCOL_VERSION,
                "collector_version": COLLECTOR_VERSION,
                "collector_git_sha": current_git_sha(),
                "detail": {"error": str(exc)},
            })
        except Exception:
            pass
        logger.exception("CHALLENGER fallo global: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
