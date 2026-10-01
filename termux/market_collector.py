#!/usr/bin/env python3
import argparse
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
import time
from datetime import datetime, timezone, timedelta
from statistics import mean

import requests

from alert_detector import AlertDetector
from signal_tracker import SignalTracker
from analysis_tracker import AnalysisTracker
from forward_v3_tracker import ForwardV3Tracker

BASE_URL = "https://fapi.binance.com"
HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "config.json"
OI_STATE_PATH = HERE / "oi_samples.json"
ALERT_RESEARCH_STATE_PATH = HERE / "alert_research_state.json"
ALERT_RESEARCH_VERSION = "ALERT_R1"
PAIRED_SNAPSHOT_VERSION = "XRP_PAIRED_SNAPSHOT_V1"
PAIRED_BENCHMARK_BATCH = "XRP_PAIR_POOL_V1"
PAIRED_BENCHMARK_ELIGIBILITY = "PRELAUNCH_POOL"
PAIRED_SNAPSHOT_BARS = 250
PAIRED_SNAPSHOT_CHUNK_BARS = 180
LOG_DIR = HERE / "logs"
LOG_DIR.mkdir(exist_ok=True)

CACHE_LIMIT = 500
OI_SAMPLE_LIMIT = 1440
TV_SHADOW_VERSION = "TV_SHADOW_V1"
TV_PATTERN_VERSION = "TV_PATTERN_R1"
SUPER_TREND_ATR_PERIOD = 10
SUPER_TREND_MULTIPLIER = 3.0
DONCHIAN_RIBBON_PERIOD = 20
BASE_TFS = ("1m", "15m", "1h", "4h", "1d")
SOLV_TFS = ("1m", "5m", "15m", "1h", "4h", "1d")  # incluye 1D como referencia macro para SOLV/XRP/BTC
TF_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}

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


def expected_last_close_utc(tf, now=None):
    """Último cierre que ya debería existir en UTC para una temporalidad."""
    if tf not in TF_MS:
        raise ValueError(f"Temporalidad no soportada: {tf}")
    now = utc_now() if now is None else now
    now_ms = int(now.timestamp() * 1000)
    interval_ms = TF_MS[tf]
    close_ms = (now_ms // interval_ms) * interval_ms - 1
    return utc_iso_ms(close_ms)


def cache_is_behind(cache, tf, now=None):
    if not cache:
        return True
    actual = str(cache[-1][6])
    expected = expected_last_close_utc(tf, now=now)
    return actual < expected

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


def _pine_rma_series(values, period):
    """TradingView-style RMA series: SMA seed, then Wilder recursion."""
    out = [None] * len(values)
    if period <= 0 or len(values) < period:
        return out
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    prev = seed
    for i in range(period, len(values)):
        prev = ((prev * (period - 1)) + values[i]) / period
        out[i] = prev
    return out


def supertrend_tv(rows, period=SUPER_TREND_ATR_PERIOD, multiplier=SUPER_TREND_MULTIPLIER):
    """
    Replica funcional del SuperTrend STRATEGY configurado por el usuario:
    ATR=RMA, source=hl2, period=10, multiplier=3.
    Investigación shadow; no genera órdenes ni señales operativas.
    """
    if not rows:
        return {}
    highs = [float(r[2]) for r in rows]
    lows = [float(r[3]) for r in rows]
    closes = [float(r[4]) for r in rows]
    trs = []
    for i in range(len(rows)):
        if i == 0:
            trs.append(highs[i] - lows[i])
        else:
            pc = closes[i - 1]
            trs.append(max(highs[i] - lows[i], abs(highs[i] - pc), abs(lows[i] - pc)))
    atrs = _pine_rma_series(trs, period)

    ups = [None] * len(rows)
    dns = [None] * len(rows)
    trends = [1] * len(rows)
    flips = ["NONE"] * len(rows)
    ages = [None] * len(rows)
    last_flip = None

    for i in range(len(rows)):
        av = atrs[i]
        prev_trend = trends[i - 1] if i else 1
        trends[i] = prev_trend
        if av is None:
            continue

        src = (highs[i] + lows[i]) / 2.0
        raw_up = src - multiplier * av
        raw_dn = src + multiplier * av
        prev_up = ups[i - 1] if i and ups[i - 1] is not None else raw_up
        prev_dn = dns[i - 1] if i and dns[i - 1] is not None else raw_dn

        if i and closes[i - 1] > prev_up:
            ups[i] = max(raw_up, prev_up)
        else:
            ups[i] = raw_up
        if i and closes[i - 1] < prev_dn:
            dns[i] = min(raw_dn, prev_dn)
        else:
            dns[i] = raw_dn

        cur = prev_trend
        if prev_trend == -1 and closes[i] > prev_dn:
            cur = 1
        elif prev_trend == 1 and closes[i] < prev_up:
            cur = -1
        trends[i] = cur

        if i and cur != prev_trend:
            flips[i] = "BUY" if cur == 1 else "SELL"
            last_flip = i
        if last_flip is not None:
            ages[i] = i - last_flip

    i = len(rows) - 1
    av = atrs[i]
    trend = trends[i]
    line = ups[i] if trend == 1 else dns[i]
    close = closes[i]
    dist_pct = ((close - line) / close) * 100.0 if line not in (None, 0) and close else None
    dist_atr = abs(close - line) / av if line is not None and av not in (None, 0) else None
    return {
        "direction": "LONG" if trend == 1 else "SHORT",
        "line": line,
        "flip": flips[i],
        "age": ages[i],
        "distance_pct": dist_pct,
        "distance_atr": dist_atr,
        "atr": av,
    }


def _donchian_trend_series(rows, length):
    highs = [float(r[2]) for r in rows]
    lows = [float(r[3]) for r in rows]
    closes = [float(r[4]) for r in rows]
    out = [0] * len(rows)
    for i in range(len(rows)):
        prev = out[i - 1] if i else 0
        if i < length:
            out[i] = prev
            continue
        hh_prev = max(highs[i - length:i])
        ll_prev = min(lows[i - length:i])
        if closes[i] > hh_prev:
            out[i] = 1
        elif closes[i] < ll_prev:
            out[i] = -1
        else:
            out[i] = prev
    return out


def donchian_ribbon_tv(rows, period=DONCHIAN_RIBBON_PERIOD):
    """
    Donchian Trend Ribbon period=20: main length 20 + lower lengths 19..11.
    Guarda tendencias crudas y consenso; el color visual no se usa como gate.
    """
    if not rows:
        return {}
    lengths = list(range(period, period - 10, -1))
    series = {length: _donchian_trend_series(rows, length) for length in lengths}
    idx = len(rows) - 1
    states = [series[length][idx] for length in lengths]
    main = states[0]
    bull = sum(1 for x in states if x == 1)
    bear = sum(1 for x in states if x == -1)
    neutral = len(states) - bull - bear
    match = sum(1 for x in states if main != 0 and x == main)
    consensus = (match / len(states)) * 100.0 if main != 0 else 0.0

    main_series = series[period]
    flip = "NONE"
    last_flip = None
    for i in range(1, len(main_series)):
        if main_series[i] != 0 and main_series[i] != main_series[i - 1]:
            last_flip = i
            if i == idx:
                flip = "BULL" if main_series[i] == 1 else "BEAR"
    age = idx - last_flip if last_flip is not None else None

    return {
        "main": "BULL" if main == 1 else "BEAR" if main == -1 else "NEUTRAL",
        "bull_count": bull,
        "bear_count": bear,
        "neutral_count": neutral,
        "match_count": match,
        "consensus_pct": consensus,
        "flip": flip,
        "age": age,
    }

def tv_pattern_shadow(rows_15m, rows_5m):
    """
    Shadow research pattern from retrospective SOLV/XRP study.
    It is intentionally bias-agnostic: returns a direction, never an entry signal.
    """
    st15 = supertrend_tv(rows_15m)
    d15 = donchian_ribbon_tv(rows_15m)
    st5 = supertrend_tv(rows_5m)
    d5 = donchian_ribbon_tv(rows_5m)

    def dtr_dir(x):
        main = str((x or {}).get("main") or "").upper()
        if main == "BULL":
            return "LONG"
        if main == "BEAR":
            return "SHORT"
        return "NONE"

    st15_dir = str(st15.get("direction") or "NONE").upper()
    d15_dir = dtr_dir(d15)
    st5_dir = str(st5.get("direction") or "NONE").upper()
    d5_dir = dtr_dir(d5)

    base_dir = st15_dir if st15_dir in ("LONG", "SHORT") and st15_dir == d15_dir else "NONE"
    five_fully_aligned = (
        base_dir in ("LONG", "SHORT")
        and st5_dir == base_dir
        and d5_dir == base_dir
    )

    pullback_dir = base_dir if base_dir != "NONE" and not five_fully_aligned else "NONE"
    dist15 = st15.get("distance_atr")
    extended = (
        five_fully_aligned
        and dist15 is not None
        and float(dist15) >= 2.0
    )
    extension_dir = base_dir if extended else "NONE"

    return {
        "pullback_window": "YES" if pullback_dir != "NONE" else "NO",
        "pullback_direction": pullback_dir,
        "extension_warning": "YES" if extended else "NO",
        "extension_direction": extension_dir,
        "st15_distance_atr": dist15,
        "version": TV_PATTERN_VERSION,
    }


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
    if tf in ("4h", "1d"):
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


def _parse_utc(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def load_alert_research_state():
    if not ALERT_RESEARCH_STATE_PATH.exists():
        return {"solv": {}, "xrp": {}}
    try:
        data = json.loads(ALERT_RESEARCH_STATE_PATH.read_text(encoding="utf-8"))
        return {
            "solv": dict(data.get("solv", {})),
            "xrp": dict(data.get("xrp", {})),
        }
    except Exception:
        return {"solv": {}, "xrp": {}}


def save_alert_research_state(state):
    clean = {}
    for key in ("solv", "xrp"):
        items = list((state.get(key) or {}).items())
        items.sort(key=lambda kv: str((kv[1].get("event") or {}).get("utc", "")))
        clean[key] = dict(items[-700:])
    tmp = ALERT_RESEARCH_STATE_PATH.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(clean, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    tmp.replace(ALERT_RESEARCH_STATE_PATH)


def _alert_snapshot_row(event):
    research = event.get("research") or {}
    event_id = str(event.get("id") or "")
    alert_utc = str(event.get("utc") or "")
    row_key = f"{alert_utc}|{event_id}"
    return [
        row_key,
        alert_utc,
        event_id,
        str(event.get("asset") or ""),
        str(event.get("type") or ""),
        str(event.get("direction") or ""),
        research.get("market.mark_price", ""),
        research.get("detector.primary_score", ""),
        research.get("detector.scalp_score", ""),
        json.dumps(research, ensure_ascii=False, separators=(",", ":")),
        ALERT_RESEARCH_VERSION,
    ]


def _sha256_text(value):
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _paired_snapshot_bundle(event, session):
    """Build a no-look-ahead market bundle for one XRP alert."""
    if str(event.get("asset") or "").upper() != "XRP":
        return None
    if not bool(event.get("telegramSent")):
        return None

    alert_dt = _parse_utc(event.get("utc"))
    if alert_dt is None:
        return None
    alert_ms = int(alert_dt.timestamp() * 1000)
    event_id = str(event.get("id") or "")
    if not event_id:
        return None

    research_row = _alert_snapshot_row(event)
    research_json = json.dumps(
        research_row, ensure_ascii=False, separators=(",", ":")
    )
    research_sha = _sha256_text(research_json)
    created = utc_iso_now()
    segments = []
    segment_shas = []
    all_full = True

    for symbol in ("XRPUSDT", "BTCUSDT"):
        for tf in SOLV_TFS:
            expected_bars = (
                360 if symbol == "XRPUSDT" and tf == "1m"
                else PAIRED_SNAPSHOT_BARS
            )
            resp = session.get(
                f"{BASE_URL}/fapi/v1/klines",
                params={
                    "symbol": symbol,
                    "interval": tf,
                    "endTime": alert_ms,
                    "limit": expected_bars + 5,
                },
                timeout=30,
            )
            resp.raise_for_status()
            raw = resp.json()
            rows = [
                [
                    int(k[0]), float(k[1]), float(k[2]), float(k[3]),
                    float(k[4]), float(k[5]), int(k[6]), float(k[7]),
                    int(k[8]), float(k[9]), float(k[10])
                ]
                for k in raw
                if int(k[6]) <= alert_ms
            ][-expected_bars:]
            expected_last_close = (alert_ms // TF_MS[tf]) * TF_MS[tf] - 1
            consecutive = (
                len(rows) == expected_bars
                and all(
                    int(rows[i][0]) - int(rows[i-1][0]) == TF_MS[tf]
                    for i in range(1, len(rows))
                )
            )
            latest_exact = bool(rows) and int(rows[-1][6]) == expected_last_close
            complete = bool(consecutive and latest_exact)
            all_full = all_full and complete
            cutoff = utc_iso_ms(rows[-1][6]) if rows else ""
            chunks = [
                rows[i:i + PAIRED_SNAPSHOT_CHUNK_BARS]
                for i in range(0, len(rows), PAIRED_SNAPSHOT_CHUNK_BARS)
            ] or [[]]
            chunk_count = len(chunks)
            for chunk_index, chunk in enumerate(chunks, start=1):
                bars_json = json.dumps(
                    chunk, ensure_ascii=False, separators=(",", ":")
                )
                seg_id = (
                    f"{event_id}|{symbol}|{tf}|"
                    f"C{chunk_index}of{chunk_count}"
                )
                seg_canonical = json.dumps(
                    [
                        seg_id, event_id, symbol, tf,
                        chunk_index, chunk_count,
                        str(event.get("utc") or ""), chunk
                    ],
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                seg_sha = _sha256_text(seg_canonical)
                segment_shas.append(seg_sha)
                segments.append([
                    seg_id,
                    event_id,
                    event_id,
                    symbol,
                    tf,
                    chunk_index,
                    chunk_count,
                    str(event.get("utc") or ""),
                    cutoff,
                    expected_bars,
                    len(chunk),
                    "FULL" if complete else "PARTIAL",
                    bars_json,
                    seg_sha,
                    PAIRED_SNAPSHOT_VERSION,
                    created,
                ])

    full_sha = _sha256_text(
        research_sha + "|" + "|".join(sorted(segment_shas))
    )
    research = event.get("research") or {}
    capture_row = [
        event_id,
        research_row[0],
        research_row[1],
        event_id,
        research_row[3],
        research_row[4],
        research_row[5],
        research.get("market.mark_price", ""),
        research.get("detector.primary_score", ""),
        research.get("detector.scalp_score", ""),
        research_row[9],
        ALERT_RESEARCH_VERSION,
        "ALERT_RESEARCH+MARKET_BARS",
        created,
        PAIRED_BENCHMARK_BATCH,
        PAIRED_BENCHMARK_ELIGIBILITY,
        research_sha,
        full_sha,
        "FULL" if all_full else "PARTIAL",
        PAIRED_SNAPSHOT_VERSION,
        "",
    ]
    return {"capture": capture_row, "segments": segments}


def _directional_pct(base, value, direction):
    if not base:
        return None
    raw = ((float(value) / float(base)) - 1.0) * 100.0
    return raw if str(direction).upper() == "LONG" else -raw


def _alert_outcome_rows(record, rows_1m):
    event = record.get("event") or {}
    research = event.get("research") or {}
    alert_dt = _parse_utc(event.get("utc"))
    base = research.get("market.mark_price")
    try:
        base = float(base)
    except Exception:
        return None, None
    if alert_dt is None or not base:
        return None, None

    candles = []
    for r in rows_1m or []:
        dt = _parse_utc(r[6] if len(r) > 6 else "")
        if dt and dt > alert_dt:
            candles.append((dt, r))
    if not candles:
        return None, None

    target240 = alert_dt + timedelta(minutes=240)
    if candles[-1][0] < target240:
        return None, None

    direction = str(event.get("direction") or "").upper()
    if direction not in ("LONG", "SHORT"):
        return None, None

    fwd = {}
    for minutes in (5, 15, 30, 60, 240):
        target = alert_dt + timedelta(minutes=minutes)
        eligible = [(dt, r) for dt, r in candles if dt <= target]
        if not eligible:
            return None, None
        close = float(eligible[-1][1][4])
        fwd[minutes] = round(_directional_pct(base, close, direction), 4)

    excursions = {}
    for minutes in (15, 60, 240):
        target = alert_dt + timedelta(minutes=minutes)
        eligible = [r for dt, r in candles if dt <= target]
        if not eligible:
            return None, None
        high = max(float(r[2]) for r in eligible)
        low = min(float(r[3]) for r in eligible)
        if direction == "LONG":
            mfe = max(0.0, ((high / base) - 1.0) * 100.0)
            mae = max(0.0, ((base - low) / base) * 100.0)
        else:
            mfe = max(0.0, ((base - low) / base) * 100.0)
            mae = max(0.0, ((high - base) / base) * 100.0)
        excursions[minutes] = (round(mfe, 4), round(mae, 4))

    event_id = str(event.get("id") or "")
    alert_utc = str(event.get("utc") or "")
    target_utc = target240.isoformat(timespec="seconds").replace("+00:00", "Z")
    row_key = f"{target_utc}|{event_id}"
    forward_row = [
        row_key,
        event_id,
        alert_utc,
        str(event.get("asset") or ""),
        str(event.get("type") or ""),
        direction,
        fwd[5],
        fwd[15],
        fwd[30],
        fwd[60],
        fwd[240],
    ]
    mfe_row = [
        row_key,
        event_id,
        alert_utc,
        str(event.get("asset") or ""),
        direction,
        excursions[15][0],
        excursions[15][1],
        excursions[60][0],
        excursions[60][1],
        excursions[240][0],
        excursions[240][1],
    ]
    return forward_row, mfe_row

class Collector:
    def __init__(self, config_path=DEFAULT_CONFIG):
        self.cfg = load_config(config_path)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "solv-xrp-termux-collector/2.0"})
        # SOLV, XRP y BTC usan 1m/5m/15m/1h/4h y 1d; 1d es referencia macro.
        self.caches = {
            "BTCUSDT": {tf: [] for tf in SOLV_TFS},
            "SOLVUSDT": {tf: [] for tf in SOLV_TFS},
            "XRPUSDT": {tf: [] for tf in SOLV_TFS},
        }
        self.oi_samples = load_oi_samples()
        self.alerts = AlertDetector(self.cfg, self.session)
        self.signal_tracker = SignalTracker(self.alerts)
        self.analysis_tracker = AnalysisTracker()
        self.forward_v3 = ForwardV3Tracker()
        self.open_signals = {"solv": [], "xrp": []}
        self.pending_analyses = {"solv": [], "xrp": []}
        self.alert_research_state = load_alert_research_state()
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

        active_tfs = SOLV_TFS

        sync_now = utc_now()
        for tf in active_tfs:
            actual = a[tf][-1][6] if a[tf] else ""
            expected = expected_last_close_utc(tf, now=sync_now)
            add(f"data.last_close_{tf}", actual, tf.upper())
            add(f"data.expected_last_close_{tf}", expected, tf.upper(), "Cierre que ya debería existir según UTC")
            add(f"data.sync_{tf}", "OK" if actual and str(actual) >= expected else "LAGGING", tf.upper())
            add(f"data.changed_{tf}", bool(changed.get(tf)), tf.upper())

        for tf in active_tfs:
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

            st = supertrend_tv(a[tf])
            dtr = donchian_ribbon_tv(a[tf])
            add(f"tv.st.{tf}.direction", st.get("direction"), tf.upper(), TV_SHADOW_VERSION)
            add(f"tv.st.{tf}.line", st.get("line"), tf.upper(), TV_SHADOW_VERSION)
            add(f"tv.st.{tf}.flip", st.get("flip"), tf.upper(), TV_SHADOW_VERSION)
            add(f"tv.st.{tf}.age", st.get("age"), tf.upper(), TV_SHADOW_VERSION)
            add(f"tv.st.{tf}.distance_pct", st.get("distance_pct"), tf.upper(), TV_SHADOW_VERSION)
            add(f"tv.st.{tf}.distance_atr", st.get("distance_atr"), tf.upper(), TV_SHADOW_VERSION)
            add(f"tv.dtr.{tf}.main", dtr.get("main"), tf.upper(), TV_SHADOW_VERSION)
            add(f"tv.dtr.{tf}.bull_count", dtr.get("bull_count"), tf.upper(), TV_SHADOW_VERSION)
            add(f"tv.dtr.{tf}.bear_count", dtr.get("bear_count"), tf.upper(), TV_SHADOW_VERSION)
            add(f"tv.dtr.{tf}.match_count", dtr.get("match_count"), tf.upper(), TV_SHADOW_VERSION)
            add(f"tv.dtr.{tf}.consensus_pct", dtr.get("consensus_pct"), tf.upper(), TV_SHADOW_VERSION)
            add(f"tv.dtr.{tf}.flip", dtr.get("flip"), tf.upper(), TV_SHADOW_VERSION)
            add(f"tv.dtr.{tf}.age", dtr.get("age"), tf.upper(), TV_SHADOW_VERSION)

        pattern = tv_pattern_shadow(a["15m"], a["5m"])
        add("tv.pattern.pullback_window", pattern.get("pullback_window"), "TV PATTERN", TV_PATTERN_VERSION)
        add("tv.pattern.pullback_direction", pattern.get("pullback_direction"), "TV PATTERN", TV_PATTERN_VERSION)
        add("tv.pattern.extension_warning", pattern.get("extension_warning"), "TV PATTERN", TV_PATTERN_VERSION)
        add("tv.pattern.extension_direction", pattern.get("extension_direction"), "TV PATTERN", TV_PATTERN_VERSION)
        add("tv.pattern.st15_distance_atr", pattern.get("st15_distance_atr"), "TV PATTERN", TV_PATTERN_VERSION)
        add("tv.pattern.version", pattern.get("version"), "SYSTEM")
        add("tv.shadow.version", TV_SHADOW_VERSION, "SYSTEM")
        add("tv.st.config", "ATR10|HL2|MULT3|RMA", "SYSTEM")
        add("tv.dtr.config", "PERIOD20|L20..11", "SYSTEM")
        add("vwap.daily_utc", avwap, "15M", "VWAP diario UTC calculado desde velas 15m")

        for tf in active_tfs:
            metrics = calc_tf(b[tf], tf)
            btc_actual = b[tf][-1][6] if b[tf] else ""
            expected = expected_last_close_utc(tf, now=sync_now)
            add(f"btc.data.last_close_{tf}", btc_actual, f"BTC {tf.upper()}")
            add(f"btc.data.sync_{tf}", "OK" if btc_actual and str(btc_actual) >= expected else "LAGGING", f"BTC {tf.upper()}")
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
            for tf in self.caches[symbol]:
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
                active_tfs = SOLV_TFS
                changed = {tf: True for tf in active_tfs}
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
                        f"{prefix}_5M": self.caches[symbol]["5m"],
                        f"{prefix}_15M": self.caches[symbol]["15m"],
                        f"{prefix}_1H": self.caches[symbol]["1h"],
                        f"{prefix}_4H": self.caches[symbol]["4h"],
                        f"{prefix}_1D": self.caches[symbol]["1d"],
                        "BTC_1M": self.caches["BTCUSDT"]["1m"],
                        "BTC_5M": self.caches["BTCUSDT"]["5m"],
                        "BTC_15M": self.caches["BTCUSDT"]["15m"],
                        "BTC_1H": self.caches["BTCUSDT"]["1h"],
                        "BTC_4H": self.caches["BTCUSDT"]["4h"],
                        "BTC_1D": self.caches["BTCUSDT"]["1d"],
                    },
                }
                if key == "xrp":
                    payload["forwardV3RecoveryRequest"] = True

                if dry_run:
                    logger.info("%s BOOTSTRAP DRY-RUN OK.", symbol)
                else:
                    response = post_json(self.session, self.cfg[key]["web_app_url"], payload)
                    self.open_signals[key] = list(response.get("openSignals", []))
                    self.pending_analyses[key] = list(response.get("pendingAnalyses", []))
                    if key == "xrp":
                        self.forward_v3.reconcile_remote(response.get("forwardV3Recovery"))
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
        changed = {tf: False for tf in SOLV_TFS}
        new_by_symbol = {
            symbol: {tf: [] for tf in self.caches[symbol]}
            for symbol in self.caches
        }

        # 1m: siempre se consulta; solo se envían velas nuevas.
        for symbol in self.caches:
            recent = get_recent_closed(self.session, symbol, "1m", limit=8)
            new_by_symbol[symbol]["1m"] = update_cache(self.caches[symbol]["1m"], recent)
            changed["1m"] = changed["1m"] or bool(new_by_symbol[symbol]["1m"])

        # SOLV + XRP + BTC: sincronización por estado, no por "caer en el minuto exacto".
        # Si una vela que ya debería existir falta, se vuelve a consultar en cada ciclo
        # hasta alcanzarla. Esto evita saltos por red/retrasos de procesamiento.
        for tf in ("5m", "15m", "1h", "4h", "1d"):
            for symbol in ("SOLVUSDT", "XRPUSDT", "BTCUSDT"):
                if cache_is_behind(self.caches[symbol][tf], tf, now=now):
                    recent = get_recent_closed(self.session, symbol, tf, limit=12)
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
                    f"{prefix}_5M": new_by_symbol[symbol]["5m"],
                    "BTC_5M": new_by_symbol["BTCUSDT"]["5m"],
                    f"{prefix}_15M": new_by_symbol[symbol]["15m"],
                    "BTC_15M": new_by_symbol["BTCUSDT"]["15m"],
                    f"{prefix}_1H": new_by_symbol[symbol]["1h"],
                    "BTC_1H": new_by_symbol["BTCUSDT"]["1h"],
                    f"{prefix}_4H": new_by_symbol[symbol]["4h"],
                    "BTC_4H": new_by_symbol["BTCUSDT"]["4h"],
                    f"{prefix}_1D": new_by_symbol[symbol]["1d"],
                    "BTC_1D": new_by_symbol["BTCUSDT"]["1d"],
                }
                for name, rows in mapping.items():
                    if rows:
                        sheets[name] = rows

                live_state = self._build_live_state(key, market, changed, generated)

                signal_updates = []
                analysis_updates = []
                alert_events = []
                forward_v3_events = []
                forward_v3_outcomes = []
                forward_v3_health = []
                new_research_events = []
                paired_capture_bundles = []
                completed_research_ids = []
                if not dry_run:
                    signal_updates = self.signal_tracker.evaluate(
                        key, self.open_signals.get(key, []), self.caches[symbol]
                    )
                    analysis_updates = self.analysis_tracker.evaluate(
                        key,
                        self.pending_analyses.get(key, []),
                        self.caches[symbol]["1m"],
                    )
                    alert_events = self.alerts.pending_events(key)

                    tracked = self.alert_research_state.setdefault(key, {})
                    for event in alert_events:
                        event_id = str(event.get("id") or "")
                        if (
                            event_id
                            and bool(event.get("telegramSent"))
                            and event_id not in tracked
                        ):
                            sheets.setdefault("ALERT_RESEARCH", []).append(
                                _alert_snapshot_row(event)
                            )
                            if key == "xrp":
                                bundle = _paired_snapshot_bundle(event, self.session)
                                if bundle:
                                    paired_capture_bundles.append(bundle)
                            new_research_events.append(event)

                    forward_rows = []
                    mfe_rows = []
                    for event_id, record in list(tracked.items()):
                        if record.get("outcomePosted"):
                            continue
                        fwd_row, mfe_row = _alert_outcome_rows(
                            record, self.caches[symbol]["1m"]
                        )
                        if fwd_row and mfe_row:
                            forward_rows.append(fwd_row)
                            mfe_rows.append(mfe_row)
                            completed_research_ids.append(event_id)
                    if forward_rows:
                        sheets["ALERT_FORWARD"] = forward_rows
                    if mfe_rows:
                        sheets["ALERT_MFE_MAE"] = mfe_rows

                    if key == "xrp":
                        (
                            forward_v3_events,
                            forward_v3_outcomes,
                            forward_v3_health,
                        ) = self.forward_v3.evaluate(self.session)

                payload = {
                    "secret": self.cfg[key]["shared_secret"],
                    "mode": "incremental",
                    "generatedAtUtc": generated,
                    "market": market,
                    "oi1m": [oi_row],
                    "liveState": live_state,
                    "sheets": sheets,
                }
                if bool(new_by_symbol[symbol]["15m"]):
                    payload["oiHistory"] = get_oi_history(self.session, symbol)
                if signal_updates:
                    payload["signalUpdates"] = signal_updates
                if analysis_updates:
                    payload["analysisUpdates"] = analysis_updates
                if alert_events:
                    payload["alertEvents"] = alert_events
                if paired_capture_bundles:
                    payload["pairedCaptureBundles"] = paired_capture_bundles
                if forward_v3_events:
                    payload["forwardV3Events"] = forward_v3_events
                if forward_v3_outcomes:
                    payload["forwardV3Outcomes"] = forward_v3_outcomes
                if forward_v3_health:
                    payload["forwardV3Health"] = forward_v3_health

                if dry_run:
                    logger.info(
                        "%s DELTA DRY-RUN: sheets=%s",
                        symbol, {k: len(v) for k, v in sheets.items()}
                    )
                else:
                    response = post_json(self.session, self.cfg[key]["web_app_url"], payload)
                    self.open_signals[key] = list(response.get("openSignals", []))
                    self.pending_analyses[key] = list(response.get("pendingAnalyses", []))
                    if alert_events:
                        self.alerts.ack_events([x.get("id") for x in alert_events])
                    if key == "xrp" and (
                        forward_v3_events or forward_v3_outcomes or forward_v3_health
                    ):
                        self.forward_v3.ack(
                            event_rows=forward_v3_events,
                            outcome_rows=forward_v3_outcomes,
                            health_rows=forward_v3_health,
                        )
                    if new_research_events or completed_research_ids:
                        tracked = self.alert_research_state.setdefault(key, {})
                        for event in new_research_events:
                            event_id = str(event.get("id") or "")
                            if event_id:
                                tracked[event_id] = {
                                    "event": event,
                                    "outcomePosted": False,
                                }
                        for event_id in completed_research_ids:
                            if event_id in tracked:
                                tracked[event_id]["outcomePosted"] = True
                        save_alert_research_state(self.alert_research_state)
                    logger.info(
                        "%s DELTA OK: sheets=%s response=%s",
                        symbol, {k: len(v) for k, v in sheets.items()}, response
                    )
                    try:
                        asset_flags = {
                            tf: bool(new_by_symbol[symbol].get(tf, []))
                            for tf in new_by_symbol[symbol]
                        }
                        self.alerts.evaluate(
                            key, self.caches[symbol], live_state, asset_flags
                        )
                    except Exception as alert_exc:
                        logger.exception("%s ALERTAS FALLARON: %s", symbol, alert_exc)
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
