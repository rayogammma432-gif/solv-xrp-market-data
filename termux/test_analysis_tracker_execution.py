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


def pad(rows, start_minute=5, count=242, price=100.0):
    base = datetime(2026, 10, 2, 10, 0, tzinfo=timezone.utc)
    for i in range(start_minute, count):
        dt = base + timedelta(minutes=i)
        rows.append(
            bar(
                dt.isoformat(timespec="seconds").replace("+00:00", "Z"),
                price, price + 0.1, price - 0.1, price
            )
        )
    return rows


class AnalysisExecutionAuditTests(unittest.TestCase):
    def setUp(self):
        self.tracker = AnalysisTracker()

    def test_long_tp1_first(self):
        item = {
            "analysisId": "A1",
            "analysisUtc": "2026-10-02T10:00:30Z",
            "markPrice": 100,
            "primaryBias": "LONG",
            "entry": 101,
            "stop": 99,
            "tp1": 104,
            "tp2": 106,
            "outcomeStatus": "PENDING",
        }
        rows = [
            bar("2026-10-02T10:01:00Z", 100, 100.5, 99.5, 100),
            bar("2026-10-02T10:02:00Z", 100, 101.2, 100.2, 101),
            bar("2026-10-02T10:03:00Z", 101, 103, 100.5, 102),
            bar("2026-10-02T10:04:00Z", 102, 104.5, 101.5, 104),
        ]
        update = self.tracker._evaluate_one(item, pad(rows))
        self.assertEqual(update["planDirection"], "LONG")
        self.assertEqual(update["geometryValid"], "YES")
        self.assertEqual(update["firstBarrier"], "TP1")
        self.assertEqual(update["realizedR"], 1.5)

    def test_short_stop_first(self):
        item = {
            "analysisId": "S1",
            "analysisUtc": "2026-10-02T10:00:30Z",
            "markPrice": 100,
            "primaryBias": "SHORT",
            "entry": 99,
            "stop": 101,
            "tp1": 96,
            "tp2": 94,
        }
        rows = [
            bar("2026-10-02T10:01:00Z", 100, 100.2, 98.8, 99.2),
            bar("2026-10-02T10:02:00Z", 99.2, 101.2, 98.5, 100.8),
        ]
        update = self.tracker._evaluate_one(item, pad(rows, start_minute=3))
        self.assertEqual(update["planDirection"], "SHORT")
        self.assertEqual(update["firstBarrier"], "STOP")
        self.assertEqual(update["realizedR"], -1.0)

    def test_same_bar_is_ambiguous(self):
        item = {
            "analysisId": "A2",
            "analysisUtc": "2026-10-02T10:00:30Z",
            "markPrice": 100,
            "primaryBias": "LONG",
            "entry": 101,
            "stop": 99,
            "tp1": 104,
            "tp2": 106,
        }
        rows = [bar("2026-10-02T10:01:00Z", 100, 104.5, 100, 103)]
        update = self.tracker._evaluate_one(item, pad(rows, start_minute=2))
        self.assertEqual(update["firstBarrier"], "AMBIGUOUS_ENTRY_BAR")
        self.assertNotIn("realizedR", update)

    def test_invalid_geometry_fails_closed(self):
        item = {
            "analysisId": "A3",
            "analysisUtc": "2026-10-02T10:00:30Z",
            "markPrice": 100,
            "primaryBias": "SHORT",
            "entry": 99,
            "stop": 98,
            "tp1": 96,
            "tp2": 94,
        }
        rows = [bar("2026-10-02T10:01:00Z", 100, 100.2, 98.8, 99.2)]
        update = self.tracker._evaluate_one(item, pad(rows, start_minute=2))
        self.assertEqual(update["planDirection"], "INVALID")
        self.assertEqual(update["geometryValid"], "NO")
        self.assertEqual(update["firstBarrier"], "INVALID_GEOMETRY")


if __name__ == "__main__":
    unittest.main()
