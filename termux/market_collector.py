#!/usr/bin/env python3
import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
import time
from datetime import datetime, timezone

import requests

BASE_URL = "https://fapi.binance.com"
HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "config.json"
LOG_DIR = HERE / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("market_collector")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fmt = logging.Formatter("%(asctime)sZ %(levelname)s %(message)s", "%Y-%m-%dT%H:%M:%S")
    fh = RotatingFileHandler(LOG_DIR / "collector.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

def utc_iso_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def utc_iso_ms(ms):
    dt = datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc)
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")

def load_config(path):
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise RuntimeError(f"No existe el archivo de configuración: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    for key in ("solv", "xrp"):
        item = data.get(key) or {}
        url = str(item.get("web_app_url", "")).strip()
        secret = str(item.get("shared_secret", "")).strip()
        if not url.startswith("https://") or "/exec" not in url:
            raise RuntimeError(f"{key}: web_app_url inválida o ausente.")
        if not secret:
            raise RuntimeError(f"{key}: shared_secret ausente.")
    return data

def get_json(session, path, tries=3):
    url = path if path.startswith("http") else BASE_URL + path
    last = None
    for attempt in range(1, tries + 1):
        try:
            r = session.get(url, timeout=30)
            if r.status_code == 451:
                raise RuntimeError(f"Binance HTTP 451: {r.text[:250]}")
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            last = exc
            if attempt < tries:
                time.sleep(2 * attempt)
    raise RuntimeError(f"GET falló tras {tries} intentos: {url} :: {last}")

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

def get_klines(session, symbol, interval):
    data = get_json(session, f"/fapi/v1/klines?symbol={symbol}&interval={interval}&limit=251")
    now_ms = int(time.time() * 1000)
    closed = [k for k in data if int(k[6]) < now_ms]
    if len(closed) < 250:
        raise RuntimeError(f"{symbol} {interval} devolvió solo {len(closed)} velas cerradas.")
    closed = closed[-250:]
    rows = []
    for k in closed:
        rows.append([
            utc_iso_ms(k[0]),
            float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]),
            utc_iso_ms(k[6]),
            float(k[7]), int(k[8]), float(k[9]), float(k[10]),
        ])
    return rows

def get_oi_history(session, symbol):
    data = get_json(session, f"/futures/data/openInterestHist?symbol={symbol}&period=15m&limit=96")
    if not isinstance(data, list) or len(data) < 20:
        raise RuntimeError(f"{symbol} OI histórico devolvió solo {len(data) if isinstance(data, list) else 0} registros.")
    rows = []
    for i, item in enumerate(data):
        cur = float(item["sumOpenInterest"])
        val = float(item["sumOpenInterestValue"])
        c15 = c1h = c4h = None
        if i >= 1:
            prev = float(data[i-1]["sumOpenInterest"])
            if prev:
                c15 = round(((cur / prev) - 1) * 100, 4)
        if i >= 4:
            prev = float(data[i-4]["sumOpenInterest"])
            if prev:
                c1h = round(((cur / prev) - 1) * 100, 4)
        if i >= 16:
            prev = float(data[i-16]["sumOpenInterest"])
            if prev:
                c4h = round(((cur / prev) - 1) * 100, 4)
        rows.append([utc_iso_ms(item["timestamp"]), cur, val, c15, c1h, c4h])
    return rows

def get_market(session, symbol):
    premium = get_json(session, f"/fapi/v1/premiumIndex?symbol={symbol}")
    oi = get_json(session, f"/fapi/v1/openInterest?symbol={symbol}")
    return {
        "markPrice": float(premium["markPrice"]),
        "indexPrice": float(premium["indexPrice"]),
        "fundingRate": float(premium["lastFundingRate"]),
        "nextFundingTimeUtc": utc_iso_ms(premium["nextFundingTime"]),
        "openInterest": float(oi["openInterest"]),
    }

def build_asset_payload(session, symbol, prefix, secret, btc):
    logger.info("Descargando %s 15m/1h/4h...", symbol)
    a15 = get_klines(session, symbol, "15m")
    a1h = get_klines(session, symbol, "1h")
    a4h = get_klines(session, symbol, "4h")
    market = get_market(session, symbol)
    oi_hist = get_oi_history(session, symbol)
    generated = utc_iso_now()
    return {
        "secret": secret,
        "generatedAtUtc": generated,
        "market": market,
        "oiHistory": oi_hist,
        "sheets": {
            f"{prefix}_15M": a15,
            f"{prefix}_1H": a1h,
            f"{prefix}_4H": a4h,
            "BTC_15M": btc["15m"],
            "BTC_1H": btc["1h"],
            "BTC_4H": btc["4h"],
        },
    }

def run_once(config_path=DEFAULT_CONFIG, dry_run=False):
    cfg = load_config(config_path)
    session = requests.Session()
    session.headers.update({"User-Agent": "solv-xrp-termux-collector/1.0"})

    logger.info("Inicio de actualización. dry_run=%s", dry_run)
    logger.info("Descargando BTCUSDT 15m/1h/4h...")
    btc = {
        "15m": get_klines(session, "BTCUSDT", "15m"),
        "1h": get_klines(session, "BTCUSDT", "1h"),
        "4h": get_klines(session, "BTCUSDT", "4h"),
    }

    specs = [
        ("solv", "SOLVUSDT", "SOLV"),
        ("xrp", "XRPUSDT", "XRP"),
    ]
    failures = []
    for key, symbol, prefix in specs:
        try:
            item = cfg[key]
            payload = build_asset_payload(session, symbol, prefix, item["shared_secret"], btc)
            if dry_run:
                logger.info("%s DRY-RUN OK: payload construido; no se escribió en Google Sheets.", symbol)
            else:
                response = post_json(session, item["web_app_url"], payload)
                logger.info(
                    "%s OK: status=%s rows=%s oiRows=%s updatedAtUtc=%s",
                    symbol,
                    response.get("status"), response.get("rows"), response.get("oiRows"), response.get("updatedAtUtc")
                )
        except Exception as exc:
            failures.append((symbol, str(exc)))
            logger.exception("%s FALLÓ: %s", symbol, exc)

    if failures:
        logger.error("Actualización terminó con %d fallo(s): %s", len(failures), failures)
        return 1
    logger.info("Actualización completa SOLV + XRP sin errores.")
    return 0

def main():
    ap = argparse.ArgumentParser(description="Recolector SOLV/XRP/BTC para Termux")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--dry-run", action="store_true", help="Descarga y valida, pero no escribe en Google Sheets")
    args = ap.parse_args()
    try:
        return run_once(args.config, args.dry_run)
    except Exception as exc:
        logger.exception("Fallo global: %s", exc)
        return 1

if __name__ == "__main__":
    sys.exit(main())
