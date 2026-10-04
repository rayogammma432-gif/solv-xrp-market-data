#!/usr/bin/env python3
import unittest
from datetime import datetime, timedelta, timezone

from analysis_tracker import AnalysisTracker, _thesis_expiry


def bar(open_iso, o, h, l, c):
    dt = datetime.fromisoformat(open_iso.replace("Z", "+00:00"))
    close = (dt + timedelta(seconds=59, milliseconds=999)).isoformat(
        timespec="milliseconds"
    ).replace("+00:00", "Z")
    return [open_iso, o, h, l, c, 0, close]


class XRPV35ThesisExpiryTests(unittest.TestCase):
    def setUp(self):
        self.tracker = AnalysisTracker()

    def test_scalp_expiry_is_derived_from_thesis_created_utc(self):
        analysis_dt = datetime(2026, 10, 4, 20, 0, tzinfo=timezone.utc)
        item = {
            "analysisId": "XRP-V35-S1",
            "analysisUtc": "2026-10-04T20:00:00Z",
            "markPrice": 2.50,
            "primaryBias": "LONG",
            "entry": 2.55,
            "stop": 2.45,
            "tp1": 2.70,
            "tp2": 2.80,
            "thesisId": (
                "SCALP_15M_1M|LONG|PULLBACK|2.5000|"
                "2.5400-2.5600|2.4500|2026-10-04T20:00:00Z"
            ),
        }
        expiry = _thesis_expiry(item, analysis_dt)
        self.assertEqual(expiry, datetime(2026, 10, 4, 20, 45, tzinfo=timezone.utc))

    def test_primary_expiry_is_two_hours(self):
        analysis_dt = datetime(2026, 10, 4, 20, 0, tzinfo=timezone.utc)
        item = {
            "thesisId": (
                "PRIMARY_1H|SHORT|BREAKOUT_RETEST|2.5000|"
                "2.4900-2.5100|2.6000|2026-10-04T20:00:00Z"
            )
        }
        expiry = _thesis_expiry(item, analysis_dt)
        self.assertEqual(expiry, datetime(2026, 10, 4, 22, 0, tzinfo=timezone.utc))

    def test_entry_after_scalp_expiry_is_no_fill_expired(self):
        item = {
            "analysisId": "XRP-V35-S2",
            "analysisUtc": "2026-10-04T20:00:00Z",
            "markPrice": 2.50,
            "primaryBias": "LONG",
            "entry": 2.55,
            "stop": 2.45,
            "tp1": 2.70,
            "tp2": 2.80,
            "thesisId": (
                "SCALP_15M_1M|LONG|PULLBACK|2.5000|"
                "2.5400-2.5600|2.4500|2026-10-04T20:00:00Z"
            ),
        }
        rows = [
            bar("2026-10-04T20:01:00Z", 2.50, 2.52, 2.49, 2.51),
            bar("2026-10-04T20:44:00Z", 2.51, 2.54, 2.50, 2.53),
            # First Entry touch is after the 20:45 expiry.
            bar("2026-10-04T20:46:00Z", 2.53, 2.56, 2.52, 2.55),
            bar("2026-10-04T20:47:00Z", 2.55, 2.58, 2.54, 2.57),
        ]
        update = self.tracker._evaluate_one(item, rows, key="xrp")
        self.assertEqual(update["executionAuditStatus"], "COMPLETE")
        self.assertEqual(update["firstBarrier"], "NO_FILL_EXPIRED")
        self.assertIn("THESIS_EXPIRED_BEFORE_FILL", update["executionAuditNotes"])
        self.assertNotIn("entryFilledUtc", update)

    def test_explicit_expiry_takes_precedence_for_backward_compatibility(self):
        analysis_dt = datetime(2026, 10, 4, 20, 0, tzinfo=timezone.utc)
        item = {
            "thesisExpiresUtc": "2026-10-04T20:30:00Z",
            "thesisId": (
                "PRIMARY_1H|LONG|PULLBACK|2.5000|"
                "2.4900-2.5100|2.4000|2026-10-04T20:00:00Z"
            ),
        }
        expiry = _thesis_expiry(item, analysis_dt)
        self.assertEqual(expiry, datetime(2026, 10, 4, 20, 30, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
