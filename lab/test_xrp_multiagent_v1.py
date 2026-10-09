"""Offline, no-credential lab smoke tests. Never touches user files or exchange."""
import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
P=ROOT/"lab/xrp_multiagent_v1.py"
spec=importlib.util.spec_from_file_location("xrp_lab_engine",P)
lab=importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)


class LabTests(unittest.TestCase):
    def test_manifest_blob_pins(self):
        m=lab.load_manifest()
        self.assertEqual(m["source"]["read_only"],True)
        self.assertNotEqual(m["agents"]["A"]["destination_sheet_id"],m["source"]["spreadsheet_id"])
        self.assertNotEqual(m["agents"]["B"]["destination_sheet_id"],m["source"]["spreadsheet_id"])
        self.assertNotEqual(m["agents"]["A"]["destination_sheet_id"],m["agents"]["B"]["destination_sheet_id"])
        for key in ("A","B"):
            self.assertFalse(m["agents"][key]["trading_enabled"])

    def test_trend_long(self):
        s={"4h.close":"102","4h.ema50":"100","1h.close":"105","1h.ema20":"104",
           "1h.ema50":"103","15m.close":"107","15m.ema20":"106","15m.ema50":"105",
           "15m.rsi14":"60","15m.volume_rel20":"1,20",
           "btc.1h.close":"90","btc.1h.ema50":"80"}
        self.assertEqual(lab.assess("A",s)[1],"SHADOW_LONG")

    def test_trend_no_setup(self):
        s={"4h.close":"99","4h.ema50":"100","1h.close":"105","1h.ema20":"104",
           "1h.ema50":"103","15m.close":"107","15m.ema20":"106","15m.ema50":"105",
           "15m.rsi14":"60","15m.volume_rel20":"1.2",
           "btc.1h.close":"90","btc.1h.ema50":"80"}
        self.assertEqual(lab.assess("A",s)[1],"NO_TRADE")

    def test_reversal_long(self):
        s={"15m.rsi14":"29","15m.close":"98","15m.ema20":"100",
           "15m.atr14":"1","1m.rsi14":"30","1h.rsi14":"45","btc.1h.rsi14":"48"}
        self.assertEqual(lab.assess("B",s)[1],"SHADOW_LONG")

    def test_reversal_no_setup(self):
        s={"15m.rsi14":"54","15m.close":"98","15m.ema20":"100",
           "15m.atr14":"1","1m.rsi14":"50","1h.rsi14":"45","btc.1h.rsi14":"48"}
        self.assertEqual(lab.assess("B",s)[1],"NO_TRADE")

    def test_missing_data_fails_closed(self):
        self.assertEqual(lab.assess("A",{})[1],"DATA_INSUFFICIENT")
        self.assertEqual(lab.assess("B",{})[1],"DATA_INSUFFICIENT")
        self.assertEqual(lab.assess("B",{"15m.atr14":"0"})[1],"DATA_INSUFFICIENT")

    def test_no_trade_apis_in_runner(self):
        source=P.read_text(encoding="utf-8")
        for forbidden in ("create_order(", "place_order(", "futures_create_order(", "SIGNALS!"):
            self.assertNotIn(forbidden,source)

if __name__=="__main__":
    unittest.main()
