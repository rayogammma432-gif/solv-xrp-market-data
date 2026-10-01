#!/usr/bin/env python3
"""
Independent XRP Challenger candidate collector.

This process is intentionally separate from market_collector.py.
It owns its state, recovery, health, retries and Google Sheets streams.

It implements the already-frozen XRP_FORWARD_V3_1 research rules through
ForwardV3Tracker. It creates research candidates/outcomes only; never SIGNALS,
orders, Telegram trade alerts or CURRENT-agent decisions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
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
LOG_DIR = HERE / "logs"
LOG_DIR.mkdir(exist_ok=True)

COLLECTOR_VERSION = "XRP_CHALLENGER_COLLECTOR_V1"
EXPECTED_RECEPTOR_VERSION = "XRP_RECEPTOR_CHALLENGER_V1"
CYCLE_SECOND = 8

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

    formal_start = parse_utc(activation.get("formal_start_utc"))
    if formal_start != FORWARD_START_UTC:
        errors.append("FORMAL_START_DOES_NOT_MATCH_FROZEN_V3_1")

    verified = parse_utc(activation.get("deployment_verified_utc"))
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
        first_boot = parse_utc(marker.get("first_boot_utc"))
        if formal_start and (first_boot is None or first_boot >= formal_start):
            errors.append("RUNTIME_FIRST_BOOT_NOT_PRESTART")
    elif formal_start and now >= formal_start and not state_exists:
        # Never silently turn a late deployment into a backfilled prospective launch.
        errors.append("LATE_FIRST_START_BLOCKED_CREATE_NEW_PROTOCOL_START")

    return errors


class ChallengerCollector:
    def __init__(
        self,
        config_path=DEFAULT_CONFIG,
        activation_path=DEFAULT_ACTIVATION,
        state_path=DEFAULT_STATE,
        runtime_path=DEFAULT_RUNTIME,
        now_fn=utc_now,
    ):
        self.cfg = load_xrp_config(config_path)
        self.activation_path = Path(activation_path)
        self.state_path = Path(state_path)
        self.runtime_path = Path(runtime_path)
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

    def receptor_recovery(self):
        payload = {
            "secret": self.cfg["shared_secret"],
            "mode": "challenger_recovery",
            "generatedAtUtc": utc_iso(self.now_fn()),
            "challengerRecoveryRequest": True,
        }
        response = post_json(self.session, self.cfg["web_app_url"], payload)
        version = str(response.get("challengerReceptorVersion") or "")
        if version != EXPECTED_RECEPTOR_VERSION:
            raise RuntimeError(
                f"Receptor Challenger inesperado: {version!r}; "
                f"esperado={EXPECTED_RECEPTOR_VERSION}"
            )
        self.tracker.reconcile_remote(response.get("challengerRecovery"))
        return response

    def cycle(self):
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
        version = str(response.get("challengerReceptorVersion") or "")
        if version != EXPECTED_RECEPTOR_VERSION:
            raise RuntimeError(
                f"Receptor Challenger inesperado: {version!r}; "
                f"esperado={EXPECTED_RECEPTOR_VERSION}"
            )

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
        return result


def sleep_to_cycle_second(now_fn=utc_now):
    now = now_fn()
    target = now.replace(second=CYCLE_SECOND, microsecond=0)
    if target <= now:
        target += timedelta(minutes=1)
    time.sleep(max(0.25, (target - now).total_seconds()))


def main():
    ap = argparse.ArgumentParser(description="XRP Challenger independent shadow collector")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--activation", default=str(DEFAULT_ACTIVATION))
    ap.add_argument("--state", default=str(DEFAULT_STATE))
    ap.add_argument("--runtime", default=str(DEFAULT_RUNTIME))
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--prelaunch-check", action="store_true")
    ap.add_argument("--check-receptor", action="store_true")
    args = ap.parse_args()

    try:
        collector = ChallengerCollector(
            config_path=args.config,
            activation_path=args.activation,
            state_path=args.state,
            runtime_path=args.runtime,
        )

        if args.prelaunch_check:
            print(json.dumps(
                collector.prelaunch_check(check_receptor=args.check_receptor),
                indent=2,
                sort_keys=True,
            ))
            return 0

        activation = collector.validate_live_activation()
        collector.ensure_runtime_marker(activation)
        collector.receptor_recovery()

        if args.once:
            result = collector.cycle()
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
                if result["posted"]:
                    logger.info("CHALLENGER DELTA OK: %s", result)
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                logger.exception("CHALLENGER ciclo falló: %s", exc)
                time.sleep(15)

    except KeyboardInterrupt:
        logger.info("CHALLENGER detenido por usuario")
        return 0
    except Exception as exc:
        logger.exception("CHALLENGER fallo global: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
