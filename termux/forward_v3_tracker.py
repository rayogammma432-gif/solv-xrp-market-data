#!/usr/bin/env python3
"""
Forward-only shadow tracker for XRP_FORWARD_V3.

Design goals:
- starts no earlier than 2026-10-01T00:00:00Z
- does not read CURRENT-agent decisions
- emits append-only event rows and direction-neutral outcome rows
- deterministic IDs + local durable state make retries idempotent
- no SIGNALS, orders, TP/SL, or trading actions
"""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

FORWARD_START_UTC = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
PROTOCOL_VERSION = "XRP_FORWARD_V3"
PROTOCOL_FILE = "research/XRP_FORWARD_RESEARCH_PROTOCOL_V3.md"
PROTOCOL_COMMIT_SHA = "69895b7c110deb838b62e3bf70a5b84455f09ca9"
REGISTRY_FILE = "research/experiments/XRP_FORWARD_REGISTRY_V3.jsonl"
REGISTRY_SHA256 = "559728efd47599b629ecaca7b8cdc2191f5b21a6ee344c89490839ab7a532a7f"
FEATURE_SET_VERSION = "FEATURES_V1"
NORMALIZATION_VERSION = "HIST_NORM_V1"
COLLECTOR_VERSION = "XRP_FORWARD_V3_COLLECTOR_V1"
OUTCOME_ENGINE_VERSION = "XRP_FORWARD_V3_OUTCOME_V1"

HERE = Path(__file__).resolve().parent
DEFAULT_STATE_PATH = HERE / "forward_v3_state.json"

CANDIDATES = {
    "XRP-FWD-V3-A-TAKER-EXHAUSTION": {
        "grid": "SCALP_1M",
        "horizons": [5, 15, 30],
        "primary": 15,
        "params": {"abs_taker_imbalance_min": 0.30, "rel_volume20_min": 1.5},
    },
    "XRP-FWD-V3-B-OI-MODERATOR": {
        "grid": "PRIMARY_15M",
        "horizons": [60],
        "primary": 60,
        "params": {"abs_ret_12_min": 0.005, "abs_oi_chg_15m": 0.005},
    },
    "XRP-FWD-V3-C-MOMENTUM-EXHAUSTION": {
        "grid": "PRIMARY_15M",
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
    return int(
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        .astimezone(timezone.utc)
        .timestamp()
        * 1000
    )


def row_available_at_ms(row):
    # Binance closed kline row: close time is index 6 and availability begins 1 ms later.
    return parse_iso_ms(row[6]) + 1


def row_open_ms(row):
    return parse_iso_ms(row[0])


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
    # Fail closed on internally impossible kline flow.
    if ratio < 0 or ratio > 1:
        return None
    return 2.0 * ratio - 1.0


def _load_state(path):
    p = Path(path)
    if not p.exists():
        return {"events": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return {"events": dict(data.get("events") or {})}
    except Exception:
        return {"events": {}}


def _save_state(path, state):
    p = Path(path)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(state, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )
    tmp.replace(p)


class ForwardV3Tracker:
    def __init__(self, state_path=DEFAULT_STATE_PATH, now_fn=utc_now, oi_feature_fetcher=None):
        self.state_path = Path(state_path)
        self.state = _load_state(self.state_path)
        self.now_fn = now_fn
        self.oi_feature_fetcher = oi_feature_fetcher

    @staticmethod
    def _event_id(candidate_id, decision_time_ms):
        return f"{candidate_id}|{iso_ms(decision_time_ms)}"

    @staticmethod
    def _outcome_id(event_id, horizon):
        return f"{event_id}|H{int(horizon)}"

    @staticmethod
    def _get_oi_feature(session, decision_time_ms):
        """
        Live analogue of historical metrics availability:
        a 5m OI observation timestamp t becomes usable at t+5m.
        oi_chg_15m requires the exact observation at t-15m.
        """
        url = (
            "https://fapi.binance.com/futures/data/openInterestHist"
            "?symbol=XRPUSDT&period=5m&limit=20"
        )
        r = session.get(url, timeout=30)
        r.raise_for_status()
        raw = r.json()
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
        if datetime.fromtimestamp(decision_ms / 1000, tz=timezone.utc) < FORWARD_START_UTC:
            return None

        event_id = self._event_id(candidate_id, decision_ms)
        events = self.state.setdefault("events", {})
        if event_id in events:
            return event_id

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
            "created_utc": self.now_fn().isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        }
        events[event_id] = record
        _save_state(self.state_path, self.state)
        return event_id

    def detect_new_events(self, xrp_caches, new_flags, session):
        if self.now_fn() < FORWARD_START_UTC:
            return []

        created = []

        if bool(new_flags.get("1m")) and xrp_caches.get("1m"):
            rows = xrp_caches["1m"]
            row = rows[-1]
            ti = taker_imbalance(row)
            rv = rel_volume20(rows)
            if ti is not None and rv is not None and abs(ti) >= 0.30 and rv >= 1.5:
                direction = "SHORT" if ti > 0 else "LONG"
                eid = self._register_event(
                    "XRP-FWD-V3-A-TAKER-EXHAUSTION",
                    row,
                    direction,
                    {
                        "xrp_taker_imbalance": ti,
                        "xrp_rel_volume20": rv,
                    },
                )
                if eid:
                    created.append(eid)

        if bool(new_flags.get("15m")) and xrp_caches.get("15m"):
            rows = xrp_caches["15m"]
            row = rows[-1]
            r12 = ret_12(rows)
            rv = rel_volume20(rows)
            decision_ms = row_available_at_ms(row)

            oi15 = None
            oi_available = ""
            try:
                if self.oi_feature_fetcher is not None:
                    oi15, oi_available = self.oi_feature_fetcher(session, decision_ms)
                else:
                    oi15, oi_available = self._get_oi_feature(session, decision_ms)
            except Exception:
                # OI candidate fails closed; other candidate can still be evaluated.
                oi15, oi_available = None, ""

            if r12 is not None and oi15 is not None and abs(r12) >= 0.005 and abs(oi15) >= 0.005:
                direction = "LONG" if r12 > 0 else "SHORT"
                group = "EXPANSION" if oi15 > 0 else "CONTRACTION"
                eid = self._register_event(
                    "XRP-FWD-V3-B-OI-MODERATOR",
                    row,
                    direction,
                    {
                        "xrp_ret_12": r12,
                        "xrp_oi_chg_15m": oi15,
                    },
                    metrics_available_at=oi_available,
                    extra_snapshot={"oi_group": group},
                )
                if eid:
                    created.append(eid)

            if r12 is not None and rv is not None and abs(r12) >= 0.010 and rv >= 1.5:
                direction = "SHORT" if r12 > 0 else "LONG"
                eid = self._register_event(
                    "XRP-FWD-V3-C-MOMENTUM-EXHAUSTION",
                    row,
                    direction,
                    {
                        "xrp_ret_12": r12,
                        "xrp_rel_volume20": rv,
                    },
                )
                if eid:
                    created.append(eid)

        return created

    @staticmethod
    def _one_minute_map(rows_1m):
        return {row_available_at_ms(r): r for r in rows_1m or []}

    def pending_event_rows(self):
        rows = []
        for rec in self.state.get("events", {}).values():
            if rec.get("event_posted"):
                continue
            f = rec.get("features") or {}
            rows.append(
                [
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
                    COLLECTOR_VERSION,
                    rec["created_utc"],
                ]
            )
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
                    fwd = ""
                    up = ""
                    down = ""
                    present = [x for x in future if x is not None]
                    source_last = str(present[-1][6]) if present else ""
                    completeness = "INCOMPLETE"

                outcome_id = self._outcome_id(rec["event_id"], horizon)
                rows.append(
                    [
                        outcome_id,
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
                        COLLECTOR_VERSION,
                        self.now_fn().isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                        "" if complete else "Exact 1m window incomplete; no interpolation/nearest fallback.",
                    ]
                )

        rows.sort(key=lambda r: (str(r[6]), str(r[0])))
        return rows

    def evaluate(self, xrp_caches, new_flags, session):
        self.detect_new_events(xrp_caches, new_flags, session)
        return self.pending_event_rows(), self.pending_outcome_rows(xrp_caches.get("1m", []))

    def ack(self, event_rows=None, outcome_rows=None):
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
                changed = True

        if changed:
            # Keep only events that may still need an outcome plus a compact recent audit tail.
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
            for eid, rec in completed[-500:]:
                active[eid] = rec
            self.state["events"] = active
            _save_state(self.state_path, self.state)
