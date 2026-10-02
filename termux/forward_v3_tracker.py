#!/usr/bin/env python3
"""
XRP_FORWARD_V3_2 forward-only shadow tracker.

Properties:
- hard start at 2026-10-02T12:00:00Z
- fetches/catches up every missed XRP 1m decision in chronological order
- reconstructs PRIMARY_15M from exact 1m bars, matching HIST_NORM_V1 resampling semantics
- fixed V3.2 candidate rules; no CURRENT-agent decisions
- exact-timestamp outcomes; no nearest/interpolation
- durable local state + Google Sheets recovery metadata
- hourly coverage health checkpoints
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
from pathlib import Path
from datetime import datetime, timedelta, timezone

FORWARD_START_UTC = datetime(2026, 10, 2, 12, 0, 0, tzinfo=timezone.utc)
FORWARD_START_MS = int(FORWARD_START_UTC.timestamp() * 1000)
PROTOCOL_VERSION = "XRP_FORWARD_V3_2"
PROTOCOL_FILE = "research/XRP_FORWARD_RESEARCH_PROTOCOL_V3_2.md"
PROTOCOL_COMMIT_SHA = "bf4d2a34684c3315dc36c997b61efd0d7595ade7"
REGISTRY_FILE = "research/experiments/XRP_FORWARD_REGISTRY_V3_2.jsonl"
REGISTRY_SHA256 = "99c17ecf3c3b376f734dc7469351445c7d6727f96d0cb7d5580ea59b5f9f932a"

FEATURE_SET_VERSION = "FEATURES_V1_LIVE_EQUIV_V1"
NORMALIZATION_VERSION = "LIVE_BINANCE_NORMALIZATION_EQUIV_V1"
COLLECTOR_VERSION = "XRP_FORWARD_V3_2_COLLECTOR_V1"
OUTCOME_ENGINE_VERSION = "XRP_FORWARD_V3_2_OUTCOME_V1"

BASE_URL = "https://fapi.binance.com"
WARMUP_MINUTES = 360
OUTCOME_INCOMPLETE_GRACE_MS = 5 * 60_000
HEALTH_FINALIZE_GRACE_MS = 10 * 60_000
RECOVERY_LOOKBACK_HOURS = 12

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
DEFAULT_STATE_PATH = HERE / "forward_v3_state.json"

CANDIDATES = {
    "XRP-FWD-V3-A-TAKER-EXHAUSTION": {
        "grid": "SCALP_1M",
        "horizons": [5, 15, 30],
        "primary": 15,
        "params": {"abs_taker_imbalance_min": 0.30, "rel_volume20_min": 1.5},
    },
    "XRP-FWD-V3-B-OI-MODERATOR": {
        "grid": "PRIMARY_15M_RESAMPLED_1M",
        "horizons": [60],
        "primary": 60,
        "params": {"abs_ret_12_min": 0.005, "abs_oi_chg_15m": 0.005},
    },
    "XRP-FWD-V3-C-MOMENTUM-EXHAUSTION": {
        "grid": "PRIMARY_15M_RESAMPLED_1M",
        "horizons": [15, 60, 240],
        "primary": 60,
        "params": {"abs_ret_12_min": 0.010, "rel_volume20_min": 1.5},
    },
}


def utc_now():
    return datetime.now(timezone.utc)


def iso_ms(ms):
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).isoformat(
        timespec="milliseconds"
    ).replace("+00:00", "Z")


def parse_iso_ms(value):
    if value in (None, ""):
        return None
    return int(
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        .astimezone(timezone.utc)
        .timestamp()
        * 1000
    )


def row_open_ms(row):
    return parse_iso_ms(row[0])


def row_available_at_ms(row):
    return parse_iso_ms(row[6]) + 1


def _hour_start_ms(ms):
    return (int(ms) // 3_600_000) * 3_600_000


def _canonical_hash(values):
    raw = json.dumps(values, ensure_ascii=False, separators=(",", ":"), sort_keys=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def current_git_sha():
    try:
        p = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT),
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        sha = p.stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=str(REPO_ROOT),
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        return sha + ("+DIRTY" if dirty else "")
    except Exception:
        return "UNKNOWN"


def _tail_is_consecutive(rows, count, step_ms):
    if len(rows) < int(count):
        return False
    tail = rows[-int(count):]
    opens = [row_open_ms(r) for r in tail]
    return all(
        opens[i] - opens[i - 1] == int(step_ms)
        for i in range(1, len(opens))
    )


def rel_volume20(rows):
    if len(rows) < 21:
        return None
    prior = [float(r[5]) for r in rows[-21:-1]]
    avg = sum(prior) / 20.0
    return float(rows[-1][5]) / avg if avg > 0 else None


def ret_12(rows):
    if len(rows) < 13:
        return None
    prev = float(rows[-13][4])
    cur = float(rows[-1][4])
    return (cur / prev) - 1.0 if prev else None


def taker_imbalance(row):
    vol = float(row[5])
    if vol <= 0:
        return None
    ratio = float(row[9]) / vol
    if ratio < 0 or ratio > 1:
        return None
    return 2.0 * ratio - 1.0


def _state_meta():
    return {
        "protocol_version": PROTOCOL_VERSION,
        "registry_sha256": REGISTRY_SHA256,
        "formal_start_utc": FORWARD_START_UTC.isoformat().replace("+00:00", "Z"),
    }


def _new_state():
    return {
        "meta": _state_meta(),
        "events": {},
        "coverage": {
            "last_evaluated_1m_ms": None,
            "last_evaluated_15m_ms": None,
            "hours": {},
            "posted_health_ids": [],
        },
    }


def _load_state(path):
    p = Path(path)
    if not p.exists():
        return _new_state()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError("STATE_FILE_INVALID_RESET_REQUIRED") from exc

    if data.get("meta") != _state_meta():
        raise RuntimeError("STATE_PROVENANCE_MISMATCH_RESET_REQUIRED")

    cov = dict(data.get("coverage") or {})
    cov.setdefault("last_evaluated_1m_ms", None)
    cov.setdefault("last_evaluated_15m_ms", None)
    cov.setdefault("hours", {})
    cov.setdefault("posted_health_ids", [])
    return {
        "meta": _state_meta(),
        "events": dict(data.get("events") or {}),
        "coverage": cov,
    }


def _save_state(path, state):
    p = Path(path)
    state["meta"] = _state_meta()
    tmp = p.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(state, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )
    tmp.replace(p)


def _kline_to_row(k):
    return [
        iso_ms(k[0]),
        float(k[1]),
        float(k[2]),
        float(k[3]),
        float(k[4]),
        float(k[5]),
        iso_ms(k[6]),
        float(k[7]),
        int(k[8]),
        float(k[9]),
        float(k[10]),
    ]


def resample_15m_from_1m(rows_1m):
    groups = {}
    for r in rows_1m:
        om = row_open_ms(r)
        bucket = (om // 900_000) * 900_000
        groups.setdefault(bucket, []).append(r)

    out = []
    for bucket in sorted(groups):
        g = sorted(groups[bucket], key=row_open_ms)
        expected = [bucket + k * 60_000 for k in range(15)]
        opens = [row_open_ms(r) for r in g]
        if opens != expected:
            continue
        close_ms = bucket + 900_000 - 1
        out.append(
            [
                iso_ms(bucket),
                float(g[0][1]),
                max(float(x[2]) for x in g),
                min(float(x[3]) for x in g),
                float(g[-1][4]),
                sum(float(x[5]) for x in g),
                iso_ms(close_ms),
                sum(float(x[7]) for x in g),
                sum(int(x[8]) for x in g),
                sum(float(x[9]) for x in g),
                sum(float(x[10]) for x in g),
            ]
        )
    return out


class ForwardV3Tracker:
    def __init__(
        self,
        state_path=DEFAULT_STATE_PATH,
        now_fn=utc_now,
        oi_feature_fetcher=None,
        collector_version=COLLECTOR_VERSION,
    ):
        self.state_path = Path(state_path)
        self.state = _load_state(self.state_path)
        self.now_fn = now_fn
        self.oi_feature_fetcher = oi_feature_fetcher
        self.collector_version = str(collector_version)
        self.collector_git_sha = current_git_sha()

    @staticmethod
    def _event_id(candidate_id, decision_time_ms):
        return f"{candidate_id}|{iso_ms(decision_time_ms)}"

    @staticmethod
    def _outcome_id(event_id, horizon):
        return f"{event_id}|H{int(horizon)}"

    def _hour(self, decision_ms):
        key = iso_ms(_hour_start_ms(decision_ms))
        h = self.state["coverage"]["hours"].setdefault(
            key,
            {
                "evaluated_1m": 0,
                "evaluated_15m": 0,
                "oi_checks": 0,
                "oi_failures": 0,
                "events_a": 0,
                "events_b": 0,
                "events_c": 0,
            },
        )
        return key, h

    def _fetch_1m_window(self, session, start_available_ms, end_available_ms):
        if end_available_ms <= start_available_ms:
            return []

        start_open = max(0, int(start_available_ms) - 60_000)
        end_open = int(end_available_ms) - 60_000
        if end_open < start_open:
            return []

        cursor = start_open
        rows = {}
        while cursor <= end_open:
            chunk_end = min(end_open, cursor + (1499 * 60_000))
            params = {
                "symbol": "XRPUSDT",
                "interval": "1m",
                "startTime": cursor,
                "endTime": chunk_end,
                "limit": 1500,
            }
            r = session.get(f"{BASE_URL}/fapi/v1/klines", params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list):
                raise RuntimeError("XRP 1m catch-up devolvió formato inválido")
            for k in data:
                row = _kline_to_row(k)
                av = row_available_at_ms(row)
                if start_available_ms <= av <= end_available_ms:
                    rows[row_open_ms(row)] = row
            cursor = chunk_end + 60_000

        return [rows[k] for k in sorted(rows)]

    @staticmethod
    def _get_oi_feature(session, decision_time_ms):
        start = decision_time_ms - 35 * 60_000
        params = {
            "symbol": "XRPUSDT",
            "period": "5m",
            "startTime": start,
            "endTime": decision_time_ms,
            "limit": 20,
        }
        r = session.get(
            f"{BASE_URL}/futures/data/openInterestHist",
            params=params,
            timeout=30,
        )
        r.raise_for_status()
        raw = r.json()
        if not isinstance(raw, list):
            return None, None

        rows = []
        for item in raw:
            ts = int(item["timestamp"])
            available_at = ts + 300_000
            if available_at <= decision_time_ms:
                rows.append(
                    {
                        "source_ts": ts,
                        "available_at": available_at,
                        "oi": float(item["sumOpenInterest"]),
                    }
                )
        if not rows:
            return None, None
        rows.sort(key=lambda x: x["source_ts"])
        cur = rows[-1]
        by_ts = {x["source_ts"]: x for x in rows}
        prev = by_ts.get(cur["source_ts"] - 900_000)
        if prev is None or prev["oi"] <= 0 or cur["oi"] <= 0:
            return None, iso_ms(cur["available_at"])
        return (cur["oi"] / prev["oi"]) - 1.0, iso_ms(cur["available_at"])

    def _register_event(
        self,
        candidate_id,
        row,
        direction,
        features,
        metrics_available_at="",
        extra_snapshot=None,
    ):
        decision_ms = row_available_at_ms(row)
        if decision_ms < FORWARD_START_MS:
            return self._event_id(candidate_id, decision_ms), False

        event_id = self._event_id(candidate_id, decision_ms)
        events = self.state.setdefault("events", {})
        if event_id in events:
            return event_id, False

        spec = CANDIDATES[candidate_id]
        snapshot = {
            "xrp_ret_12": features.get("xrp_ret_12"),
            "xrp_rel_volume20": features.get("xrp_rel_volume20"),
            "xrp_taker_imbalance": features.get("xrp_taker_imbalance"),
            "xrp_oi_chg_15m": features.get("xrp_oi_chg_15m"),
        }
        if extra_snapshot:
            snapshot.update(extra_snapshot)

        record = {
            "event_id": event_id,
            "candidate_id": candidate_id,
            "decision_grid": spec["grid"],
            "decision_time_ms": decision_ms,
            "decision_time": iso_ms(decision_ms),
            "bar_open": str(row[0]),
            "direction": direction,
            "reference_price": float(row[4]),
            "features": snapshot,
            "metrics_available_at": metrics_available_at or "",
            "rule_params": spec["params"],
            "horizons": list(spec["horizons"]),
            "primary_horizon": int(spec["primary"]),
            "event_posted": False,
            "posted_horizons": [],
            "outcome_status": {},
            "created_utc": self.now_fn()
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
        }
        events[event_id] = record
        return event_id, True

    def _evaluate_1m_decisions(self, rows_1m):
        cov = self.state["coverage"]
        last = cov.get("last_evaluated_1m_ms")
        if last is None:
            last = FORWARD_START_MS - 60_000
        expected = int(last) + 60_000

        for i, row in enumerate(rows_1m):
            decision = row_available_at_ms(row)
            if decision < FORWARD_START_MS or decision <= last:
                continue
            if decision < expected:
                continue
            if decision > expected:
                # Fail closed on a gap. Never advance beyond a missing decision.
                break

            _, h = self._hour(decision)
            h["evaluated_1m"] += 1
            ti = taker_imbalance(row)
            history_1m = rows_1m[: i + 1]
            rv = (
                rel_volume20(history_1m)
                if _tail_is_consecutive(history_1m, 21, 60_000)
                else None
            )

            if ti is not None and rv is not None and abs(ti) >= 0.30 and rv >= 1.5:
                h["events_a"] += 1
                self._register_event(
                    "XRP-FWD-V3-A-TAKER-EXHAUSTION",
                    row,
                    "SHORT" if ti > 0 else "LONG",
                    {"xrp_taker_imbalance": ti, "xrp_rel_volume20": rv},
                )

            cov["last_evaluated_1m_ms"] = decision
            last = decision
            expected = decision + 60_000

    def _evaluate_15m_decisions(self, rows_15m, session):
        cov = self.state["coverage"]
        last = cov.get("last_evaluated_15m_ms")
        if last is None:
            last = FORWARD_START_MS - 900_000
        expected = int(last) + 900_000

        for i, row in enumerate(rows_15m):
            decision = row_available_at_ms(row)
            if decision < FORWARD_START_MS or decision <= last:
                continue
            if decision < expected:
                continue
            if decision > expected:
                # Same continuity contract as 1m: do not skip a missing 15m decision.
                break

            _, h = self._hour(decision)
            h["evaluated_15m"] += 1
            history_15m = rows_15m[: i + 1]
            r12 = (
                ret_12(history_15m)
                if _tail_is_consecutive(history_15m, 13, 900_000)
                else None
            )
            rv = (
                rel_volume20(history_15m)
                if _tail_is_consecutive(history_15m, 21, 900_000)
                else None
            )

            h["oi_checks"] += 1
            try:
                if self.oi_feature_fetcher is not None:
                    oi15, oi_available = self.oi_feature_fetcher(session, decision)
                else:
                    oi15, oi_available = self._get_oi_feature(session, decision)
            except Exception:
                oi15, oi_available = None, None
            if oi15 is None:
                h["oi_failures"] += 1

            if r12 is not None and oi15 is not None and abs(r12) >= 0.005 and abs(oi15) >= 0.005:
                h["events_b"] += 1
                self._register_event(
                    "XRP-FWD-V3-B-OI-MODERATOR",
                    row,
                    "LONG" if r12 > 0 else "SHORT",
                    {"xrp_ret_12": r12, "xrp_oi_chg_15m": oi15},
                    metrics_available_at=oi_available or "",
                    extra_snapshot={"oi_group": "EXPANSION" if oi15 > 0 else "CONTRACTION"},
                )

            if r12 is not None and rv is not None and abs(r12) >= 0.010 and rv >= 1.5:
                h["events_c"] += 1
                self._register_event(
                    "XRP-FWD-V3-C-MOMENTUM-EXHAUSTION",
                    row,
                    "SHORT" if r12 > 0 else "LONG",
                    {"xrp_ret_12": r12, "xrp_rel_volume20": rv},
                )

            cov["last_evaluated_15m_ms"] = decision
            last = decision
            expected = decision + 900_000

    @staticmethod
    def _one_minute_map(rows_1m):
        return {row_available_at_ms(r): r for r in rows_1m or []}

    def pending_event_rows(self):
        rows = []
        for rec in self.state.get("events", {}).values():
            if rec.get("event_posted"):
                continue
            f = rec.get("features") or {}
            base = [
                rec["event_id"],
                PROTOCOL_VERSION,
                rec["candidate_id"],
                "XRPUSDT",
                rec["decision_grid"],
                rec["decision_time"],
                rec["bar_open"],
                rec["direction"],
                rec["reference_price"],
                "" if f.get("xrp_ret_12") is None else f.get("xrp_ret_12"),
                "" if f.get("xrp_rel_volume20") is None else f.get("xrp_rel_volume20"),
                "" if f.get("xrp_taker_imbalance") is None else f.get("xrp_taker_imbalance"),
                "" if f.get("xrp_oi_chg_15m") is None else f.get("xrp_oi_chg_15m"),
                json.dumps(rec.get("rule_params") or {}, separators=(",", ":"), sort_keys=True),
                json.dumps(f, separators=(",", ":"), sort_keys=True),
                FEATURE_SET_VERSION,
                NORMALIZATION_VERSION,
                rec["decision_time"],
                rec.get("metrics_available_at", ""),
                REGISTRY_FILE,
                REGISTRY_SHA256,
                PROTOCOL_FILE,
                PROTOCOL_COMMIT_SHA,
                self.collector_version,
                rec["created_utc"],
                self.collector_git_sha,
            ]
            rows.append(base + [_canonical_hash(base)])
        rows.sort(key=lambda r: (str(r[5]), str(r[0])))
        return rows

    def pending_outcome_rows(self, rows_1m):
        if not rows_1m:
            return []
        by_available = self._one_minute_map(rows_1m)
        latest_available = max(by_available)
        rows = []

        for rec in self.state.get("events", {}).values():
            posted = {int(x) for x in rec.get("posted_horizons", [])}
            decision = int(rec["decision_time_ms"])
            ref = float(rec["reference_price"])

            for horizon in rec["horizons"]:
                horizon = int(horizon)
                if horizon in posted:
                    continue
                target = decision + horizon * 60_000
                if latest_available < target:
                    continue

                expected = [decision + k * 60_000 for k in range(1, horizon + 1)]
                future = [by_available.get(t) for t in expected]
                complete = all(x is not None for x in future)

                if complete:
                    target_row = future[-1]
                    fwd = float(target_row[4]) / ref - 1.0
                    up = max(float(x[2]) for x in future) / ref - 1.0
                    down = min(float(x[3]) for x in future) / ref - 1.0
                    source_last = str(target_row[6])
                    completeness = "COMPLETE"
                else:
                    if latest_available < target + OUTCOME_INCOMPLETE_GRACE_MS:
                        continue
                    fwd = ""
                    up = ""
                    down = ""
                    present = [x for x in future if x is not None]
                    source_last = str(present[-1][6]) if present else ""
                    completeness = "INCOMPLETE"

                # Record the finalized status before health is computed. This is
                # not an acknowledgement; it only makes same-cycle health accounting exact.
                rec.setdefault("outcome_status", {})[str(horizon)] = completeness

                base = [
                    self._outcome_id(rec["event_id"], horizon),
                    rec["event_id"],
                    rec["candidate_id"],
                    rec["decision_time"],
                    horizon,
                    "YES" if horizon == int(rec["primary_horizon"]) else "NO",
                    iso_ms(target),
                    fwd,
                    up,
                    down,
                    completeness,
                    OUTCOME_ENGINE_VERSION,
                    source_last,
                    REGISTRY_SHA256,
                    self.collector_version,
                    self.now_fn().isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                    "" if complete else "Exact 1m window incomplete; no interpolation/nearest fallback.",
                    self.collector_git_sha,
                ]
                rows.append(base + [_canonical_hash(base)])

        rows.sort(key=lambda r: (str(r[6]), str(r[0])))
        return rows

    def pending_health_rows(self):
        now_ms = int(self.now_fn().timestamp() * 1000)
        posted = set(self.state["coverage"].get("posted_health_ids") or [])
        rows = []
        events = self.state.get("events", {})

        for hour_iso, h in sorted(self.state["coverage"]["hours"].items()):
            hour_ms = parse_iso_ms(hour_iso)
            if hour_ms < FORWARD_START_MS:
                continue
            health_id = f"{PROTOCOL_VERSION}|{hour_iso}"
            if health_id in posted:
                continue
            if now_ms < hour_ms + 3_600_000 + HEALTH_FINALIZE_GRACE_MS:
                continue

            incomplete = 0
            for rec in events.values():
                decision = int(rec.get("decision_time_ms") or 0)
                for horizon, status in (rec.get("outcome_status") or {}).items():
                    target = decision + int(horizon) * 60_000
                    if _hour_start_ms(target) == hour_ms and status == "INCOMPLETE":
                        incomplete += 1

            pending = sum(
                1
                for rec in events.values()
                if set(map(int, rec.get("posted_horizons", [])))
                < set(map(int, rec.get("horizons", [])))
            )

            expected_1m = 60
            expected_15m = 4
            eval1 = int(h.get("evaluated_1m", 0))
            eval15 = int(h.get("evaluated_15m", 0))
            base = [
                health_id,
                PROTOCOL_VERSION,
                hour_iso,
                expected_1m,
                eval1,
                max(0, expected_1m - eval1),
                expected_15m,
                eval15,
                max(0, expected_15m - eval15),
                int(h.get("oi_checks", 0)),
                int(h.get("oi_failures", 0)),
                int(h.get("events_a", 0)),
                int(h.get("events_b", 0)),
                int(h.get("events_c", 0)),
                pending,
                incomplete,
                iso_ms(self.state["coverage"]["last_evaluated_1m_ms"])
                if self.state["coverage"].get("last_evaluated_1m_ms")
                else "",
                iso_ms(self.state["coverage"]["last_evaluated_15m_ms"])
                if self.state["coverage"].get("last_evaluated_15m_ms")
                else "",
                self.collector_version,
                self.collector_git_sha,
            ]
            rows.append(base + [_canonical_hash(base)])
        return rows

    def reconcile_remote(self, recovery):
        if not recovery:
            return

        outcome_ids = set(str(x) for x in (recovery.get("outcomeIds") or []))
        now_ms = int(self.now_fn().timestamp() * 1000)
        min_event_ms = now_ms - RECOVERY_LOOKBACK_HOURS * 3_600_000

        for row in recovery.get("events") or []:
            if not isinstance(row, list) or len(row) < 27:
                continue
            if str(row[1]) != PROTOCOL_VERSION:
                continue
            decision_ms = parse_iso_ms(row[5])
            if decision_ms is None or decision_ms < min_event_ms:
                continue
            cid = str(row[2])
            if cid not in CANDIDATES:
                continue
            eid = str(row[0])
            try:
                features = json.loads(str(row[14] or "{}"))
            except Exception:
                features = {}
            try:
                params = json.loads(str(row[13] or "{}"))
            except Exception:
                params = CANDIDATES[cid]["params"]

            posted_horizons = []
            outcome_status = {}
            for h in CANDIDATES[cid]["horizons"]:
                oid = self._outcome_id(eid, h)
                if oid in outcome_ids:
                    posted_horizons.append(int(h))

            self.state["events"][eid] = {
                "event_id": eid,
                "candidate_id": cid,
                "decision_grid": str(row[4]),
                "decision_time_ms": decision_ms,
                "decision_time": str(row[5]),
                "bar_open": str(row[6]),
                "direction": str(row[7]),
                "reference_price": float(row[8]),
                "features": features,
                "metrics_available_at": str(row[18] or ""),
                "rule_params": params,
                "horizons": list(CANDIDATES[cid]["horizons"]),
                "primary_horizon": int(CANDIDATES[cid]["primary"]),
                "event_posted": True,
                "posted_horizons": posted_horizons,
                "outcome_status": outcome_status,
                "created_utc": str(row[24] or ""),
            }

        health = recovery.get("latestHealth")
        if isinstance(health, list) and len(health) >= 21:
            if str(health[1]) == PROTOCOL_VERSION:
                last1 = parse_iso_ms(health[16])
                last15 = parse_iso_ms(health[17])
                if last1:
                    self.state["coverage"]["last_evaluated_1m_ms"] = max(
                        int(self.state["coverage"].get("last_evaluated_1m_ms") or 0),
                        last1,
                    )
                if last15:
                    self.state["coverage"]["last_evaluated_15m_ms"] = max(
                        int(self.state["coverage"].get("last_evaluated_15m_ms") or 0),
                        last15,
                    )
                self.state["coverage"].setdefault("posted_health_ids", []).append(str(health[0]))

        _save_state(self.state_path, self.state)

    def evaluate(self, session):
        if self.now_fn() < FORWARD_START_UTC:
            return [], [], []

        cov = self.state["coverage"]
        last1 = int(cov.get("last_evaluated_1m_ms") or (FORWARD_START_MS - 60_000))
        earliest_pending = None
        for rec in self.state.get("events", {}).values():
            if set(map(int, rec.get("posted_horizons", []))) < set(map(int, rec.get("horizons", []))):
                t = int(rec.get("decision_time_ms") or 0)
                earliest_pending = t if earliest_pending is None else min(earliest_pending, t)

        warmup_anchor = last1
        if earliest_pending is not None:
            warmup_anchor = min(warmup_anchor, earliest_pending)
        fetch_start = warmup_anchor - WARMUP_MINUTES * 60_000
        end_ms = int(self.now_fn().timestamp() * 1000)

        rows_1m = self._fetch_1m_window(session, fetch_start, end_ms)
        if not rows_1m:
            return self.pending_event_rows(), [], self.pending_health_rows()

        self._evaluate_1m_decisions(rows_1m)
        rows_15m = resample_15m_from_1m(rows_1m)
        self._evaluate_15m_decisions(rows_15m, session)

        events = self.pending_event_rows()
        outcomes = self.pending_outcome_rows(rows_1m)
        health = self.pending_health_rows()
        _save_state(self.state_path, self.state)
        return events, outcomes, health

    def ack(self, event_rows=None, outcome_rows=None, health_rows=None):
        changed = False
        events = self.state.get("events", {})

        for row in event_rows or []:
            event_id = str(row[0])
            if event_id in events and not events[event_id].get("event_posted"):
                events[event_id]["event_posted"] = True
                changed = True

        for row in outcome_rows or []:
            event_id = str(row[1])
            horizon = int(row[4])
            rec = events.get(event_id)
            if not rec:
                continue
            posted = {int(x) for x in rec.get("posted_horizons", [])}
            if horizon not in posted:
                posted.add(horizon)
                rec["posted_horizons"] = sorted(posted)
                rec.setdefault("outcome_status", {})[str(horizon)] = str(row[10])
                changed = True

        hp = set(self.state["coverage"].get("posted_health_ids") or [])
        for row in health_rows or []:
            hid = str(row[0])
            if hid and hid not in hp:
                hp.add(hid)
                changed = True
        self.state["coverage"]["posted_health_ids"] = sorted(hp)[-2000:]

        if changed:
            ordered = sorted(
                events.items(),
                key=lambda kv: int(kv[1].get("decision_time_ms", 0)),
            )
            active = {}
            completed = []
            for eid, rec in ordered:
                if set(map(int, rec.get("posted_horizons", []))) >= set(map(int, rec.get("horizons", []))):
                    completed.append((eid, rec))
                else:
                    active[eid] = rec
            for eid, rec in completed[-3000:]:
                active[eid] = rec
            self.state["events"] = active

            # Keep only recent hourly counters after they have been posted.
            cutoff = int(self.now_fn().timestamp() * 1000) - 72 * 3_600_000
            self.state["coverage"]["hours"] = {
                k: v
                for k, v in self.state["coverage"]["hours"].items()
                if parse_iso_ms(k) >= cutoff
                or f"{PROTOCOL_VERSION}|{k}"
                not in set(self.state["coverage"]["posted_health_ids"])
            }

            _save_state(self.state_path, self.state)
