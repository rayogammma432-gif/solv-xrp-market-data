import os
from datetime import datetime, timezone
import requests
from flask import Flask, jsonify

app = Flask(__name__)
BASE = "https://fapi.binance.com"
TIMEOUT = 12

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
    try:
        r = requests.get(
            BASE + path,
            timeout=TIMEOUT,
            headers={"User-Agent": "render-binance-connectivity-test/1.0"},
        )
        item = {"name": name, "status_code": r.status_code, "ok": r.ok}
        try:
            data = r.json()
            if isinstance(data, dict):
                item["sample"] = {
                    k: data[k]
                    for k in ("symbol", "markPrice", "indexPrice", "lastFundingRate",
                              "openInterest", "code", "msg")
                    if k in data
                }
            elif isinstance(data, list):
                item["items"] = len(data)
        except Exception:
            item["body_preview"] = r.text[:300]
        return item
    except Exception as exc:
        return {"name": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"}

@app.get("/")
def home():
    return jsonify({
        "service": "Render -> Binance Futures connectivity test",
        "status": "ready",
        "utc": datetime.now(timezone.utc).isoformat(),
        "writes_google_sheets": False,
        "next": "/test-binance",
    })

@app.get("/health")
def health():
    return jsonify({"ok": True, "utc": datetime.now(timezone.utc).isoformat()})

@app.get("/test-binance")
def test_binance():
    results = [check(name, path) for name, path in TESTS]
    all_ok = all(item.get("ok") is True for item in results)
    return jsonify({
        "all_ok": all_ok,
        "utc": datetime.now(timezone.utc).isoformat(),
        "writes_google_sheets": False,
        "results": results,
    }), (200 if all_ok else 502)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
