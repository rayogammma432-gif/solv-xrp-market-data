import json
import sys
import requests

BASE = "https://fapi.binance.com"
TIMEOUT = 15

TESTS = [
    ("ping", "/fapi/v1/ping"),
    ("XRP premium", "/fapi/v1/premiumIndex?symbol=XRPUSDT"),
    ("SOLV premium", "/fapi/v1/premiumIndex?symbol=SOLVUSDT"),
    ("XRP open interest", "/fapi/v1/openInterest?symbol=XRPUSDT"),
    ("SOLV open interest", "/fapi/v1/openInterest?symbol=SOLVUSDT"),
    ("XRP 15m", "/fapi/v1/klines?symbol=XRPUSDT&interval=15m&limit=3"),
    ("XRP 1h", "/fapi/v1/klines?symbol=XRPUSDT&interval=1h&limit=3"),
    ("XRP 4h", "/fapi/v1/klines?symbol=XRPUSDT&interval=4h&limit=3"),
    ("SOLV 15m", "/fapi/v1/klines?symbol=SOLVUSDT&interval=15m&limit=3"),
    ("SOLV 1h", "/fapi/v1/klines?symbol=SOLVUSDT&interval=1h&limit=3"),
    ("SOLV 4h", "/fapi/v1/klines?symbol=SOLVUSDT&interval=4h&limit=3"),
    ("BTC 15m", "/fapi/v1/klines?symbol=BTCUSDT&interval=15m&limit=3"),
    ("BTC 1h", "/fapi/v1/klines?symbol=BTCUSDT&interval=1h&limit=3"),
    ("BTC 4h", "/fapi/v1/klines?symbol=BTCUSDT&interval=4h&limit=3"),
    ("XRP OI history", "/futures/data/openInterestHist?symbol=XRPUSDT&period=15m&limit=5"),
    ("SOLV OI history", "/futures/data/openInterestHist?symbol=SOLVUSDT&period=15m&limit=5"),
]

def check(name, path):
    url = BASE + path
    try:
        r = requests.get(
            url,
            timeout=TIMEOUT,
            headers={"User-Agent": "github-actions-binance-test/1.0"},
        )
        item = {"name": name, "status_code": r.status_code, "ok": r.ok}
        try:
            data = r.json()
            if isinstance(data, dict):
                item["sample"] = {
                    k: data[k]
                    for k in (
                        "symbol",
                        "markPrice",
                        "indexPrice",
                        "lastFundingRate",
                        "openInterest",
                        "code",
                        "msg",
                    )
                    if k in data
                }
            elif isinstance(data, list):
                item["items"] = len(data)
        except Exception:
            item["body_preview"] = r.text[:300]
        return item
    except Exception as e:
        return {"name": name, "ok": False, "error": f"{type(e).__name__}: {e}"}

results = [check(name, path) for name, path in TESTS]
all_ok = all(x.get("ok") is True for x in results)

print(json.dumps({"all_ok": all_ok, "results": results}, indent=2))

if not all_ok:
    sys.exit(1)
