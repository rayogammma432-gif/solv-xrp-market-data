#!/usr/bin/env python3
import unittest
from unittest.mock import patch

import market_collector as mc


class ExecutionMarketTelemetryTests(unittest.TestCase):
    def setUp(self):
        self.market = {
            "markPrice": 2.01,
            "indexPrice": 2.00,
            "fundingRate": 0.0001,
            "nextFundingTimeUtc": "2026-10-05T20:00:00.000Z",
            "openInterest": 1000.0,
        }

    def test_enriches_basis_book_and_depth(self):
        def fake_get_json(session, path, tries=3):
            if "bookTicker" in path:
                return {
                    "bidPrice": "2.0000", "askPrice": "2.0020",
                    "bidQty": "100", "askQty": "120",
                }
            if "/depth" in path:
                return {
                    "bids": [["2.0000", "10"]] * 20,
                    "asks": [["2.0020", "11"]] * 20,
                }
            raise AssertionError(path)

        with patch.object(mc, "get_json", side_effect=fake_get_json):
            out = mc.enrich_execution_market(object(), "XRPUSDT", self.market)

        self.assertAlmostEqual(out["basis"], 0.01)
        self.assertAlmostEqual(out["basisBps"], 50.0)
        self.assertEqual(out["bestBid"], 2.0)
        self.assertEqual(out["bestAsk"], 2.002)
        self.assertGreater(out["spreadBps"], 0)
        self.assertEqual(out["depthLevels"], 20)
        self.assertGreater(out["bidDepthTop20Usdt"], out["bidDepthTop5Usdt"])

    def test_microstructure_failure_is_nonfatal(self):
        with patch.object(mc, "get_json", side_effect=RuntimeError("unavailable")):
            out = mc.enrich_execution_market(object(), "XRPUSDT", self.market)

        self.assertAlmostEqual(out["basis"], 0.01)
        self.assertIsNone(out["bestBid"])
        self.assertIsNone(out["bestAsk"])
        self.assertIsNone(out["depthLevels"])

    def test_row_has_exact_schema_width_and_missing_as_blank(self):
        out = mc.enrich_execution_market.__name__  # module import smoke
        self.assertEqual(out, "enrich_execution_market")
        row = mc.execution_market_row(dict(self.market), "2026-10-05T19:00:00.000Z")
        self.assertEqual(len(row), 23)
        self.assertEqual(row[0], "2026-10-05T19:00:00.000Z")
        self.assertEqual(row[1], "XRP_EXECUTION_MARKET_V1")
        self.assertEqual(row[2], "XRPUSDT")
        self.assertEqual(row[10], "")
        self.assertEqual(row[11], "")


if __name__ == "__main__":
    unittest.main()
