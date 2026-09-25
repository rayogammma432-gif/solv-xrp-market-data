#!/usr/bin/env python3
import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
import time
from datetime import datetime, timezone
from statistics import mean

import requests

BASE_URL = "https://fapi.binance.com"
HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "config.json"
OI_STATE_PATH = HERE / "oi_samples.json"
LOG_DIR = HERE / "logs"
LOG_DIR.mkdir(exist_ok=True)

CACHE_LIMIT = 500
OI_SAMPLE_LIMIT = 1440
TFS = ("1m", "15m", "1h", "4h")

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

def utc_now():
    return datetime.now(timezone.utc)

def utc_iso_now():
    return utc_now().isoformat(timespec="milliseconds").replace("+00:00", "Z")

def utc_iso_ms(ms):
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).isoformat(
        timespec="milliseconds"
    ).replace("+00:00", "Z")

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

def kline_to_row(k):
    return [
        utc_iso_ms(k[0]),
        float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]),
        utc_iso_ms(k[6]),
        float(k[7]), int(k[8]), float(k[9]), float(k[10]),
    ]

def get_closed_klines(session, symbol, interval, limit=501, keep=CACHE_LIMIT):
    data = get_json(
        session,
        f"/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    )
    now_ms = int(time.time() * 1000)
    rows = [kline_to_row(k) for k in data if int(k[6]) < now_ms]
    if not rows:
        raise RuntimeError(f"{symbol} {interval} no devolvió velas cerradas.")
    return rows[-keep:]

def get_recent_closed(session, symbol, interval, limit=8):
    return get_closed_klines(session, symbol, interval, limit=limit, keep=limit)

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

def get_oi_history(session, symbol):
    data = get_json(
        session,
        f"/futures/data/openInterestHist?symbol={symbol}&period=15m&limit=96"
    )
    rows = []
    for i, item in enumerate(data):
        cur = float(item["sumOpenInterest"])
        value = float(item["sumOpenInterestValue"])
        def pct(back):
            if i < back:
                return None
            prev = float(data[i-back]["sumOpenInterest"])
            return round(((cur / prev) - 1) * 100, 4) if prev else None
        rows.append([
            utc_iso_ms(item["timestamp"]),
            cur,
            value,
            pct(1),
            pct(4),
            pct(16),
        ])
    return rows

def ema(values, period):
    if len(values) < period:
        return None
    alpha = 2.0 / (period + 1.0)
    value = mean(values[:period])
    for x in values[period:]:
        value = alpha * x + (1 - alpha) * value
    return value

def rma(values, period):
    if len(values) < period:
        return None
    value = mean(values[:period])
    for x in values[period:]:
        value = (value * (period - 1) + x) / period
    return value

def rsi(rows, period=14):
    closes = [float(r[4]) for r in rows]
    if len(closes) < period + 1:
        return None
    changes = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [max(x, 0.0) for x in changes]
    losses = [max(-x, 0.0) for x in changes]
    avg_gain = rma(gains, period)
    avg_loss = rma(losses, period)
    if avg_gain is None or avg_loss is None:
        return None
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

def atr(rows, period=14):
    if len(rows) < period + 1:
        return None
    trs = []
    for i in range(1, len(rows)):
        high = float(rows[i][2])
        low = float(rows[i][3])
        prev_close = float(rows[i-1][4])
        trs.append(max(high-low, abs(high-prev_close), abs(low-prev_close)))
    return rma(trs, period)

def volume_rel(rows, period=20):
    if len(rows) < period + 1:
        return None
    prior = [float(r[5]) for r in rows[-period-1:-1]]
    avg = mean(prior) if prior else 0.0
    return float(rows[-1][5]) / avg if avg else None

def daily_vwap_from_15m(rows):
    if not rows:
        return None
    today = utc_now().date().isoformat()
    selected = [r for r in rows if str(r[0])[:10] == today]
    if not selected:
        return None
    num = den = 0.0
    for r in selected:
        typical = (float(r[2]) + float(r[3]) + float(r[4])) / 3.0
        vol = float(r[5])
        num += typical * vol
        den += vol
    return num / den if den else None

def fmt_num(x, digits=10):
    if x is None:
        return ""
    if isinstance(x, bool):
        return "SI" if x else "NO"
    if isinstance(x, (int, float)):
        return round(float(x), digits)
    return x

def calc_tf(rows, tf):
    closes = [float(r[4]) for r in rows]
    result = {
        "close": closes[-1] if closes else None,
        "ema20": ema(closes, 20),
        "ema50": ema(closes, 50),
        "ema200": ema(closes, 200),
        "rsi14": rsi(rows, 14),
        "atr14": atr(rows, 14),
        "vol_rel20": volume_rel(rows, 20),
    }
    if tf == "4h":
        result.pop("ema20", None)
        result.pop("vol_rel20", None)
    return result

def update_cache(cache, incoming):
    if not incoming:
        return []
    last_ts = cache[-1][0] if cache else ""
    new_rows = [r for r in incoming if r[0] > last_ts]
    if new_rows:
        cache.extend(new_rows)
        del cache[:-CACHE_LIMIT]
    return new_rows

def load_oi_samples():
    if not OI_STATE_PATH.exists():
        return {"solv": [], "xrp": []}
    try:
        data = json.loads(OI_STATE_PATH.read_text(encoding="utf-8"))
        return {
            "solv": list(data.get("solv", []))[-OI_SAMPLE_LIMIT:],
            "xrp": list(data.get("xrp", []))[-OI_SAMPLE_LIMIT:],
        }
    except Exception:
        return {"solv": [], "xrp": []}

def save_oi_samples(data):
    tmp = OI_STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    tmp.replace(OI_STATE_PATH)

def pct_from_samples(samples, minutes):
    if not samples:
        return None
    current = samples[-1]
    target = current["ts_ms"] - minutes * 60_000
    candidates = [x for x in samples if x["ts_ms"] <= target]
    if not candidates:
        return None
    prev = candidates[-1]
    if not prev["oi"]:
        return None
    return round(((current["oi"] / prev["oi"]) - 1) * 100, 4)

def make_oi_sample(market, existing):
    now = utc_now()
    ts_ms = int(now.timestamp() * 1000)
    base = {
        "ts_ms": ts_ms,
        "timestamp": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "oi": float(market["openInterest"]),
        "oi_value": float(market["openInterest"]) * float(market["markPrice"]),
    }
    temp = (existing + [base])[-OI_SAMPLE_LIMIT:]
    base["d1"] = pct_from_samples(temp, 1)
    base["d5"] = pct_from_samples(temp, 5)
    base["d15"] = pct_from_samples(temp, 15)
    base["d60"] = pct_from_samples(temp, 60)
    base["d240"] = pct_from_samples(temp, 240)
    row = [
        base["timestamp"], base["oi"], base["oi_value"],
        base["d1"], base["d5"], base["d15"], base["d60"], base["d240"],
        "MUESTREO_LOCAL_OI_ACTUAL",
    ]
    return base, row

class Collector:
    def __init__(self, config_path=DEFAULT_CONFIG):
        self.cfg = load_config(config_path)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "solv-xrp-termux-collector/2.0"})
        self.caches = {
            "BTCUSDT": {tf: [] for tf in TFS},
            "SOLVUSDT": {tf: [] for tf in TFS},
            "XRPUSDT": {tf: [] for tf in TFS},
        }
        self.oi_samples = load_oi_samples()
        self.bootstrapped = False

    def _asset_spec(self, key):
        return ("SOLVUSDT", "SOLV") if key == "solv" else ("XRPUSDT", "XRP")

    def _build_live_state(self, key, market, changed, generated):
        symbol, _ = self._asset_spec(key)
        a = self.caches[symbol]
        b = self.caches["BTCUSDT"]
        avwap = daily_vwap_from_15m(a["15m"])
        bvwap = daily_vwap_from_15m(b["15m"])
        latest_oi = self.oi_samples[key][-1] if self.oi_samples[key] else {}

        rows = []
        def add(name, value, tf="", note=""):
            rows.append([name, fmt_num(value), tf, generated, note])

        add("system.generated_at_utc", generated, "SYSTEM")
        add("market.symbol", symbol, "MARKET")
        add("market.mark_price", market["markPrice"], "MARKET")
        add("market.index_price", market["indexPrice"], "MARKET")
        add("market.funding_rate", market["fundingRate"], "MARKET")
        add("market.next_funding_utc", market["nextFundingTimeUtc"], "MARKET")
        add("market.open_interest", market["openInterest"], "MARKET")

        for tf in TFS:
            add(f"data.last_close_{tf}", a[tf][-1][6] if a[tf] else "", tf.upper())
            add(f"data.changed_{tf}", bool(changed.get(tf)), tf.upper())

        for tf in TFS:
            metrics = calc_tf(a[tf], tf)
            add(f"{tf}.close", metrics.get("close"), tf.upper())
            if "ema20" in metrics:
                add(f"{tf}.ema20", metrics.get("ema20"), tf.upper())
            add(f"{tf}.ema50", metrics.get("ema50"), tf.upper())
            add(f"{tf}.ema200", metrics.get("ema200"), tf.upper())
            add(f"{tf}.rsi14", metrics.get("rsi14"), tf.upper())
            add(f"{tf}.atr14", metrics.get("atr14"), tf.upper())
            if "vol_rel20" in metrics:
                add(f"{tf}.volume_rel20", metrics.get("vol_rel20"), tf.upper())

        add("vwap.daily_utc", avwap, "15M", "VWAP diario UTC calculado desde velas 15m")

        for tf in TFS:
            metrics = calc_tf(b[tf], tf)
            add(f"btc.{tf}.close", metrics.get("close"), f"BTC {tf.upper()}")
            add(f"btc.{tf}.ema50", metrics.get("ema50"), f"BTC {tf.upper()}")
            add(f"btc.{tf}.ema200", metrics.get("ema200"), f"BTC {tf.upper()}")
            add(f"btc.{tf}.rsi14", metrics.get("rsi14"), f"BTC {tf.upper()}")
        add("btc.vwap.daily_utc", bvwap, "BTC 15M")

        add("oi.change_1m_pct", latest_oi.get("d1"), "OI 1M", "Muestreo local del OI actual")
        add("oi.change_5m_pct", latest_oi.get("d5"), "OI 5M", "Muestreo local del OI actual")
        add("oi.change_15m_pct", latest_oi.get("d15"), "OI 15M", "Muestreo local del OI actual")
        add("oi.change_1h_pct", latest_oi.get("d60"), "OI 1H", "Muestreo local del OI actual")
        add("oi.change_4h_pct", latest_oi.get("d240"), "OI 4H", "Muestreo local del OI actual")
        return rows

    def bootstrap(self, dry_run=False):
        logger.info("BOOTSTRAP: cargando %d velas cerradas por temporalidad.", CACHE_LIMIT)
        for symbol in self.caches:
            for tf in TFS:
                self.caches[symbol][tf] = get_closed_klines(
                    self.session, symbol, tf, limit=CACHE_LIMIT + 1, keep=CACHE_LIMIT
                )
                logger.info("%s %s: %d velas.", symbol, tf, len(self.caches[symbol][tf]))

        failures = []
        for key in ("solv", "xrp"):
            symbol, prefix = self._asset_spec(key)
            try:
                market = get_market(self.session, symbol)
                sample, oi_row = make_oi_sample(market, self.oi_samples[key])
                self.oi_samples[key].append(sample)
                self.oi_samples[key] = self.oi_samples[key][-OI_SAMPLE_LIMIT:]
                generated = utc_iso_now()
                changed = {tf: True for tf in TFS}
                payload = {
                    "secret": self.cfg[key]["shared_secret"],
                    "mode": "bootstrap",
                    "generatedAtUtc": generated,
                    "market": market,
                    "oiHistory": get_oi_history(self.session, symbol),
                    "oi1m": [[
                        x["timestamp"], x["oi"], x["oi_value"],
                        x.get("d1"), x.get("d5"), x.get("d15"), x.get("d60"), x.get("d240"),
                        "MUESTREO_LOCAL_OI_ACTUAL"
                    ] for x in self.oi_samples[key]],
                    "liveState": self._build_live_state(key, market, changed, generated),
                    "sheets": {
                        f"{prefix}_1M": self.caches[symbol]["1m"],
                        f"{prefix}_15M": self.caches[symbol]["15m"],
                        f"{prefix}_1H": self.caches[symbol]["1h"],
                        f"{prefix}_4H": self.caches[symbol]["4h"],
                        "BTC_1M": self.caches["BTCUSDT"]["1m"],
                        "BTC_15M": self.caches["BTCUSDT"]["15m"],
                        "BTC_1H": self.caches["BTCUSDT"]["1h"],
                        "BTC_4H": self.caches["BTCUSDT"]["4h"],
                    },
                }
                if dry_run:
                    logger.info("%s BOOTSTRAP DRY-RUN OK.", symbol)
                else:
                    response = post_json(self.session, self.cfg[key]["web_app_url"], payload)
                    logger.info("%s BOOTSTRAP OK: %s", symbol, response)
            except Exception as exc:
                failures.append((symbol, str(exc)))
                logger.exception("%s BOOTSTRAP FALLÓ: %s", symbol, exc)

        save_oi_samples(self.oi_samples)
        if failures:
            raise RuntimeError(f"Bootstrap con fallos: {failures}")
        self.bootstrapped = True
        logger.info("BOOTSTRAP completo SOLV + XRP.")

    def incremental_cycle(self, dry_run=False):
        if not self.bootstrapped:
            self.bootstrap(dry_run=dry_run)
            return

        now = utc_now()
        changed = {tf: False for tf in TFS}
        new_by_symbol = {s: {tf: [] for tf in TFS} for s in self.caches}

        # 1m: siempre se consulta; solo se envían velas nuevas.
        for symbol in self.caches:
            recent = get_recent_closed(self.session, symbol, "1m", limit=8)
            new_by_symbol[symbol]["1m"] = update_cache(self.caches[symbol]["1m"], recent)
            changed["1m"] = changed["1m"] or bool(new_by_symbol[symbol]["1m"])

        # Temporalidades mayores: solo en sus cierres UTC.
        due = []
        if now.minute % 15 == 0:
            due.append("15m")
        if now.minute == 0:
            due.append("1h")
        if now.minute == 0 and now.hour % 4 == 0:
            due.append("4h")

        for tf in due:
            for symbol in self.caches:
                recent = get_recent_closed(self.session, symbol, tf, limit=5)
                new_by_symbol[symbol][tf] = update_cache(self.caches[symbol][tf], recent)
                changed[tf] = changed[tf] or bool(new_by_symbol[symbol][tf])

        failures = []
        for key in ("solv", "xrp"):
            symbol, prefix = self._asset_spec(key)
            try:
                market = get_market(self.session, symbol)
                sample, oi_row = make_oi_sample(market, self.oi_samples[key])
                self.oi_samples[key].append(sample)
                self.oi_samples[key] = self.oi_samples[key][-OI_SAMPLE_LIMIT:]
                generated = utc_iso_now()

                sheets = {}
                mapping = {
                    f"{prefix}_1M": new_by_symbol[symbol]["1m"],
                    "BTC_1M": new_by_symbol["BTCUSDT"]["1m"],
                    f"{prefix}_15M": new_by_symbol[symbol]["15m"],
                    "BTC_15M": new_by_symbol["BTCUSDT"]["15m"],
                    f"{prefix}_1H": new_by_symbol[symbol]["1h"],
                    "BTC_1H": new_by_symbol["BTCUSDT"]["1h"],
                    f"{prefix}_4H": new_by_symbol[symbol]["4h"],
                    "BTC_4H": new_by_symbol["BTCUSDT"]["4h"],
                }
                for name, rows in mapping.items():
                    if rows:
                        sheets[name] = rows

                payload = {
                    "secret": self.cfg[key]["shared_secret"],
                    "mode": "incremental",
                    "generatedAtUtc": generated,
                    "market": market,
                    "oi1m": [oi_row],
                    "liveState": self._build_live_state(key, market, changed, generated),
                    "sheets": sheets,
                }
                if "15m" in due:
                    payload["oiHistory"] = get_oi_history(self.session, symbol)

                if dry_run:
                    logger.info(
                        "%s DELTA DRY-RUN: sheets=%s",
                        symbol, {k: len(v) for k, v in sheets.items()}
                    )
                else:
                    response = post_json(self.session, self.cfg[key]["web_app_url"], payload)
                    logger.info(
                        "%s DELTA OK: sheets=%s response=%s",
                        symbol, {k: len(v) for k, v in sheets.items()}, response
                    )
            except Exception as exc:
                failures.append((symbol, str(exc)))
                logger.exception("%s DELTA FALLÓ: %s", symbol, exc)

        save_oi_samples(self.oi_samples)
        if failures:
            raise RuntimeError(f"Delta con fallos: {failures}")

def main():
    ap = argparse.ArgumentParser(description="Recolector incremental SOLV/XRP/BTC para Termux")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--incremental-once",
        action="store_true",
        help="Bootstrap en memoria y ejecuta un ciclo incremental de prueba."
    )
    args = ap.parse_args()
    try:
        c = Collector(args.config)
        c.bootstrap(dry_run=args.dry_run)
        if args.incremental_once:
            c.incremental_cycle(dry_run=args.dry_run)
        return 0
    except Exception as exc:
        logger.exception("Fallo global: %s", exc)
        return 1

if __name__ == "__main__":
    sys.exit(main())
