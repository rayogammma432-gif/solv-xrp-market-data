#!/usr/bin/env python3
import unittest
from datetime import datetime, timedelta, timezone

from analysis_tracker import AnalysisTracker


def bar(open_iso, o, h, l, c):
    dt = datetime.fromisoformat(open_iso.replace("Z", "+00:00"))
    close = (dt + timedelta(seconds=59, milliseconds=999)).isoformat(
        timespec="milliseconds"
    ).replace("+00:00", "Z")
    return [open_iso, o, h, l, c, 0, close]


def pad(rows, start_minute=6, count=242, price=100.0):
    base = datetime(2026, 10, 3, 10, 0, tzinfo=timezone.utc)
    for i in range(start_minute, count):
        dt = base + timedelta(minutes=i)
        rows.append(
            bar(
                dt.isoformat(timespec="seconds").replace("+00:00", "Z"),
                price, price + 0.05, price - 0.05, price
            )
        )
    return rows


class SolvV34ShadowOneRTests(unittest.TestCase):
    def setUp(self):
        self.tracker = AnalysisTracker()

    def test_long_shadow_one_r_hits_first(self):
        item = {
            "analysisId": "SOLV-L1",
            "analysisUtc": "2026-10-03T10:00:30Z",
            "markPrice": 100,
            "primaryBias": "LONG",
            "entry": 101,
            "stop": 99,
            "tp1": 105,
            "tp2": 107,
        }
        rows = [
            bar("2026-10-03T10:01:00Z", 100, 100.5, 99.8, 100.2),
            bar("2026-10-03T10:02:00Z", 100.2, 101.2, 100.1, 101.0),
            bar("2026-10-03T10:03:00Z", 101.0, 103.2, 100.8, 103.0),
        ]
        update = self.tracker._evaluate_one(item, pad(rows), key="solv")
        self.assertEqual(update["shadowTp1OneR"], 103.0)
        self.assertEqual(update["shadowTp1FirstBarrier"], "TP1_1R")
        self.assertEqual(update["shadowTp1RealizedR"], 1.0)

    def test_short_shadow_one_r_stop_first(self):
        item = {
            "analysisId": "SOLV-S1",
            "analysisUtc": "2026-10-03T10:00:30Z",
            "markPrice": 100,
            "primaryBias": "SHORT",
            "entry": 99,
            "stop": 101,
            "tp1": 95,
            "tp2": 93,
        }
        rows = [
            bar("2026-10-03T10:01:00Z", 100, 100.2, 98.8, 99.2),
            bar("2026-10-03T10:02:00Z", 99.2, 101.2, 98.9, 100.8),
        ]
        update = self.tracker._evaluate_one(item, pad(rows, start_minute=3), key="solv")
        self.assertEqual(update["shadowTp1OneR"], 97.0)
        self.assertEqual(update["shadowTp1FirstBarrier"], "STOP")
        self.assertEqual(update["shadowTp1RealizedR"], -1.0)

    def test_xrp_does_not_emit_solv_shadow_fields(self):
        item = {
            "analysisId": "XRP-X1",
            "analysisUtc": "2026-10-03T10:00:30Z",
            "markPrice": 100,
            "primaryBias": "LONG",
            "entry": 101,
            "stop": 99,
            "tp1": 104,
            "tp2": 106,
        }
        rows = [
            bar("2026-10-03T10:01:00Z", 100, 100.5, 99.8, 100.2),
            bar("2026-10-03T10:02:00Z", 100.2, 101.2, 100.1, 101.0),
        ]
        update = self.tracker._evaluate_one(item, pad(rows, start_minute=3), key="xrp")
        self.assertNotIn("shadowTp1OneR", update)
        self.assertNotIn("shadowTp1FirstBarrier", update)


if __name__ == "__main__":
    unittest.main()
