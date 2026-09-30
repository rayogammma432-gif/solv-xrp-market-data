#!/usr/bin/env python3
import json
import logging
import time
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
STATE_PATH = HERE / "alert_state.json"
EVENTS_PATH = HERE / "alert_events.json"
logger = logging.getLogger("market_collector")


def _num(v):
    try:
        if v in ("", None):
            return None
        return float(v)
    except Exception:
        return None


def _load_state():
    if not STATE_PATH.exists():
        return {"solv": {}, "xrp": {}}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return {"solv": dict(data.get("solv", {})), "xrp": dict(data.get("xrp", {}))}
    except Exception:
        return {"solv": {}, "xrp": {}}


def _save_state(state):
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, separators=(",", ":")), encoding="utf-8")
    tmp.replace(STATE_PATH)


def _load_events():
    if not EVENTS_PATH.exists():
        return []
    try:
        return list(json.loads(EVENTS_PATH.read_text(encoding="utf-8")))[-500:]
    except Exception:
        return []


def _save_events(events):
    tmp = EVENTS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(events[-500:], ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(EVENTS_PATH)


class TelegramNotifier:
    def __init__(self, config, session):
        cfg = config.get("telegram") or {}
        self.enabled = bool(cfg.get("enabled", False))
        self.token = str(cfg.get("bot_token", "")).strip()
        self.chat_id = str(cfg.get("chat_id", "")).strip()
        self.session = session
        if self.enabled and (not self.token or not self.chat_id):
            logger.warning("Telegram está enabled pero falta bot_token o chat_id; alertas desactivadas.")
            self.enabled = False

    def send(self, text):
        if not self.enabled:
            return False
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            r = self.session.post(
                url,
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "disable_web_page_preview": True,
                },
                timeout=20,
            )
            r.raise_for_status()
            data = r.json()
            if not data.get("ok"):
                raise RuntimeError(data.get("description", data))
            return True
        except Exception as exc:
            logger.error("Telegram sendMessage falló: %s", exc)
            return False


class AlertDetector:
    """
    Detector preliminar, determinista y barato.
    NO sustituye el análisis final del agente ChatGPT.

    Flujo:
      1H -> candidato PRIMARY/VIGILAR
      15m -> trigger PRIMARY y/o candidato SCALP
      1m -> timing SCALP
    """

    def __init__(self, config, session):
        self.notifier = TelegramNotifier(config, session)
        tcfg = config.get("telegram") or {}
        self.assets = {str(x).lower() for x in tcfg.get("assets", ["solv"])}
        self.state = _load_state()
        self._current_live = {}

    @property
    def enabled(self):
        return self.notifier.enabled

    def _live_map(self, live_rows):
        return {str(r[0]): r[1] if len(r) > 1 else "" for r in live_rows}

    def _score_primary(self, live, direction):
        sign = 1 if direction == "LONG" else -1
        checks = []

        c4 = _num(live.get("4h.close"))
        e4_50 = _num(live.get("4h.ema50"))
        e4_200 = _num(live.get("4h.ema200"))
        r4 = _num(live.get("4h.rsi14"))

        c1 = _num(live.get("1h.close"))
        e1_20 = _num(live.get("1h.ema20"))
        e1_50 = _num(live.get("1h.ema50"))
        r1 = _num(live.get("1h.rsi14"))
        vol1 = _num(live.get("1h.volume_rel20"))
        vwap = _num(live.get("vwap.daily_utc"))

        bc1 = _num(live.get("btc.1h.close"))
        be1 = _num(live.get("btc.1h.ema50"))
        br1 = _num(live.get("btc.1h.rsi14"))

        if None not in (c4, e4_200, r4):
            checks.append((sign * (c4 - e4_200) >= 0) or (r4 >= 45 if sign > 0 else r4 <= 55))
        if None not in (c4, e4_50):
            checks.append(sign * (c4 - e4_50) >= 0)
        if None not in (c1, e1_20):
            checks.append(sign * (c1 - e1_20) >= 0)
        if None not in (c1, e1_50):
            checks.append(sign * (c1 - e1_50) >= 0)
        if r1 is not None:
            checks.append(r1 >= 50 if sign > 0 else r1 <= 50)
        if None not in (c1, vwap):
            checks.append(sign * (c1 - vwap) >= 0)
        if vol1 is not None:
            checks.append(vol1 >= 0.75)
        if None not in (bc1, be1, br1):
            strongly_against = (
                (sign > 0 and bc1 < be1 and br1 < 40)
                or (sign < 0 and bc1 > be1 and br1 > 60)
            )
            checks.append(not strongly_against)

        return sum(1 for x in checks if x), len(checks)

    def _score_scalp(self, live, direction):
        sign = 1 if direction == "LONG" else -1
        checks = []

        c1 = _num(live.get("1h.close"))
        e1 = _num(live.get("1h.ema50"))
        r1 = _num(live.get("1h.rsi14"))

        c15 = _num(live.get("15m.close"))
        e15_20 = _num(live.get("15m.ema20"))
        e15_50 = _num(live.get("15m.ema50"))
        r15 = _num(live.get("15m.rsi14"))
        vol15 = _num(live.get("15m.volume_rel20"))
        vwap = _num(live.get("vwap.daily_utc"))

        bc15 = _num(live.get("btc.15m.close"))
        be15 = _num(live.get("btc.15m.ema50"))
        br15 = _num(live.get("btc.15m.rsi14"))

        if None not in (c1, e1, r1):
            strongly_against = (
                (sign > 0 and c1 < e1 and r1 < 40)
                or (sign < 0 and c1 > e1 and r1 > 60)
            )
            checks.append(not strongly_against)
        if None not in (c15, e15_20):
            checks.append(sign * (c15 - e15_20) >= 0)
        if None not in (c15, e15_50):
            checks.append(sign * (c15 - e15_50) >= 0)
        if r15 is not None:
            checks.append(r15 >= 50 if sign > 0 else r15 <= 50)
        if None not in (c15, vwap):
            checks.append(sign * (c15 - vwap) >= 0)
        if vol15 is not None:
            checks.append(vol15 >= 0.70)
        if None not in (bc15, be15, br15):
            strongly_against = (
                (sign > 0 and bc15 < be15 and br15 < 40)
                or (sign < 0 and bc15 > be15 and br15 > 60)
            )
            checks.append(not strongly_against)

        return sum(1 for x in checks if x), len(checks)

    def _choose_direction(self, scorer, live, minimum):
        ls, ln = scorer(live, "LONG")
        ss, sn = scorer(live, "SHORT")
        if ls >= minimum and ls >= ss + 2:
            return "LONG", ls, ln
        if ss >= minimum and ss >= ls + 2:
            return "SHORT", ss, sn
        return None, max(ls, ss), max(ln, sn)

    def _trigger_15m_legacy(self, rows, live, direction):
        if len(rows) < 5:
            return None
        last = rows[-1]
        prev = rows[-2]
        close = float(last[4])
        high = float(last[2])
        low = float(last[3])
        prev_close = float(prev[4])
        prev_high = float(prev[2])
        prev_low = float(prev[3])
        ema20 = _num(live.get("15m.ema20"))

        prior3_high = max(float(r[2]) for r in rows[-4:-1])
        prior3_low = min(float(r[3]) for r in rows[-4:-1])

        if direction == "LONG":
            if close > prior3_high:
                return "break de micro-swing 15m"
            if ema20 is not None and prev_close <= ema20 < close:
                return "reclaim EMA20 15m"
            if low < prior3_low and close > prev_close and close > prev_low:
                return "sweep/reclaim 15m"
            if close > prev_high and close > prev_close:
                return "break + continuación 15m"
        else:
            if close < prior3_low:
                return "break de micro-swing 15m"
            if ema20 is not None and prev_close >= ema20 > close:
                return "lose EMA20 15m"
            if high > prior3_high and close < prev_close and close < prev_high:
                return "sweep/lose 15m"
            if close < prev_low and close < prev_close:
                return "break + continuación 15m"
        return None

    def _trigger_1m_legacy(self, rows, live, direction):
        if len(rows) < 4:
            return None
        last = rows[-1]
        prev = rows[-2]
        close = float(last[4])
        prev_close = float(prev[4])
        prev_high = float(prev[2])
        prev_low = float(prev[3])
        ema20 = _num(live.get("1m.ema20"))
        rsi = _num(live.get("1m.rsi14"))

        if direction == "LONG":
            if close > prev_high and (rsi is None or rsi >= 50):
                return "ruptura micro-swing 1m"
            if ema20 is not None and prev_close <= ema20 < close:
                return "reclaim EMA20 1m"
        else:
            if close < prev_low and (rsi is None or rsi <= 50):
                return "ruptura micro-swing 1m"
            if ema20 is not None and prev_close >= ema20 > close:
                return "lose EMA20 1m"
        return None

    def _trigger_15m_solv(self, rows, live, direction):
        """
        SOLV/XRP: reclaims/sweeps pueden confirmar de inmediato.
        Una ruptura directa solo crea PRE-TRIGGER; requiere otra vela cerrada
        sosteniendo/retesteando el nivel antes de alertar como trigger.
        """
        if len(rows) < 5:
            return None
        last = rows[-1]
        prev = rows[-2]
        close = float(last[4])
        high = float(last[2])
        low = float(last[3])
        prev_close = float(prev[4])
        prev_high = float(prev[2])
        prev_low = float(prev[3])
        ema20 = _num(live.get("15m.ema20"))

        prior3_high = max(float(r[2]) for r in rows[-4:-1])
        prior3_low = min(float(r[3]) for r in rows[-4:-1])

        if direction == "LONG":
            # Triggers de aceptación/reclaim conservan alerta inmediata.
            if ema20 is not None and prev_close <= ema20 < close:
                return {"status": "TRIGGER", "reason": "reclaim EMA20 15m"}
            if low < prior3_low and close > prev_close and close > prev_low:
                return {"status": "TRIGGER", "reason": "sweep/reclaim 15m"}

            # Rupturas directas: PRE-TRIGGER hasta otra vela cerrada.
            if close > prior3_high:
                return {
                    "status": "PRE",
                    "reason": "break de micro-swing 15m",
                    "level": prior3_high,
                }
            if close > prev_high and close > prev_close:
                return {
                    "status": "PRE",
                    "reason": "break + continuación 15m",
                    "level": prev_high,
                }
        else:
            if ema20 is not None and prev_close >= ema20 > close:
                return {"status": "TRIGGER", "reason": "lose EMA20 15m"}
            if high > prior3_high and close < prev_close and close < prev_high:
                return {"status": "TRIGGER", "reason": "sweep/lose 15m"}

            if close < prior3_low:
                return {
                    "status": "PRE",
                    "reason": "break de micro-swing 15m",
                    "level": prior3_low,
                }
            if close < prev_low and close < prev_close:
                return {
                    "status": "PRE",
                    "reason": "break + continuación 15m",
                    "level": prev_low,
                }
        return None

    def _trigger_1m_solv(self, rows, live, direction):
        """
        SOLV/XRP: reclaim/lose EMA20 puede confirmar de inmediato.
        Ruptura micro-swing 1m = PRE-TRIGGER hasta el siguiente cierre.
        """
        if len(rows) < 4:
            return None
        last = rows[-1]
        prev = rows[-2]
        close = float(last[4])
        prev_close = float(prev[4])
        prev_high = float(prev[2])
        prev_low = float(prev[3])
        ema20 = _num(live.get("1m.ema20"))
        rsi = _num(live.get("1m.rsi14"))

        if direction == "LONG":
            if ema20 is not None and prev_close <= ema20 < close:
                return {"status": "TRIGGER", "reason": "reclaim EMA20 1m"}
            if close > prev_high and (rsi is None or rsi >= 50):
                return {
                    "status": "PRE",
                    "reason": "ruptura micro-swing 1m",
                    "level": prev_high,
                }
        else:
            if ema20 is not None and prev_close >= ema20 > close:
                return {"status": "TRIGGER", "reason": "lose EMA20 1m"}
            if close < prev_low and (rsi is None or rsi <= 50):
                return {
                    "status": "PRE",
                    "reason": "ruptura micro-swing 1m",
                    "level": prev_low,
                }
        return None

    def _confirm_pretrigger(self, rows, watch, direction):
        """
        Confirma solo en una vela posterior a la ruptura.
        LONG: cierre posterior >= nivel roto.
        SHORT: cierre posterior <= nivel roto.
        Si cierra al otro lado, el PRE-TRIGGER queda invalidado.
        """
        if not watch or not rows:
            return None
        last = rows[-1]
        close_ts = str(last[6])
        if close_ts == str(watch.get("source_close", "")):
            return None

        level = _num(watch.get("level"))
        if level is None:
            return {"status": "INVALID"}

        close = float(last[4])
        low = float(last[3])
        high = float(last[2])

        if direction == "LONG":
            if close >= level:
                mode = "retest defendido" if low <= level else "hold/aceptación"
                return {
                    "status": "TRIGGER",
                    "reason": f"{watch.get('reason', 'break')} + {mode}",
                    "level": level,
                }
            return {"status": "INVALID"}

        if close <= level:
            mode = "retest defendido" if high >= level else "hold/aceptación"
            return {
                "status": "TRIGGER",
                "reason": f"{watch.get('reason', 'break')} + {mode}",
                "level": level,
            }
        return {"status": "INVALID"}

    def _research_snapshot(self, live):
        return (
            f"mark={live.get('market.mark_price', '')};"
            f"5m_close={live.get('5m.close', '')};"
            f"5m_ema20={live.get('5m.ema20', '')};"
            f"5m_ema50={live.get('5m.ema50', '')};"
            f"5m_rsi={live.get('5m.rsi14', '')};"
            f"5m_atr={live.get('5m.atr14', '')};"
            f"5m_volrel={live.get('5m.volume_rel20', '')};"
            f"btc5m_close={live.get('btc.5m.close', '')};"
            f"btc5m_ema50={live.get('btc.5m.ema50', '')};"
            f"btc5m_rsi={live.get('btc.5m.rsi14', '')}"
        )

    def _research_payload(self, live, direction=""):
        keys = [
            "market.mark_price",
            "market.index_price",
            "market.funding_rate",
            "market.open_interest",
            "data.last_close_1m",
            "data.last_close_5m",
            "data.last_close_15m",
            "data.last_close_1h",
            "data.last_close_4h",
            "data.last_close_1d",
            "1m.close", "1m.ema20", "1m.ema50", "1m.ema200", "1m.rsi14", "1m.atr14", "1m.volume_rel20",
            "5m.close", "5m.ema20", "5m.ema50", "5m.ema200", "5m.rsi14", "5m.atr14", "5m.volume_rel20",
            "15m.close", "15m.ema20", "15m.ema50", "15m.ema200", "15m.rsi14", "15m.atr14", "15m.volume_rel20",
            "1h.close", "1h.ema20", "1h.ema50", "1h.ema200", "1h.rsi14", "1h.atr14", "1h.volume_rel20",
            "4h.close", "4h.ema50", "4h.ema200", "4h.rsi14", "4h.atr14",
            "1d.close", "1d.ema50", "1d.ema200", "1d.rsi14", "1d.atr14",
            "vwap.daily_utc",
            "btc.1m.close", "btc.1m.ema50", "btc.1m.ema200", "btc.1m.rsi14",
            "btc.5m.close", "btc.5m.ema50", "btc.5m.ema200", "btc.5m.rsi14",
            "btc.15m.close", "btc.15m.ema50", "btc.15m.ema200", "btc.15m.rsi14",
            "btc.1h.close", "btc.1h.ema50", "btc.1h.ema200", "btc.1h.rsi14",
            "btc.4h.close", "btc.4h.ema50", "btc.4h.ema200", "btc.4h.rsi14",
            "btc.1d.close", "btc.1d.ema50", "btc.1d.ema200", "btc.1d.rsi14",
            "btc.vwap.daily_utc",
            "oi.change_1m_pct", "oi.change_5m_pct", "oi.change_15m_pct", "oi.change_1h_pct", "oi.change_4h_pct",
        ]
        out = {k: live.get(k, "") for k in keys}
        if direction in ("LONG", "SHORT"):
            ps, pn = self._score_primary(live, direction)
            ss, sn = self._score_scalp(live, direction)
            out["detector.primary_score"] = f"{ps}/{pn}"
            out["detector.scalp_score"] = f"{ss}/{sn}"
        return out

    def _record_event(self, key, kind, signature, message, telegram_sent=False):
        events = _load_events()
        event_id = f"{key}:{kind}:{signature}"
        if any(str(x.get("id")) == event_id for x in events):
            return False
        direction = str(signature).split(":", 1)[0] if ":" in str(signature) else ""
        events.append({
            "id": event_id,
            "utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "asset": key.upper(),
            "type": kind.upper(),
            "signature": str(signature),
            "telegramSent": bool(telegram_sent),
            "message": str(message),
            "direction": direction,
            "research": self._research_payload(self._current_live, direction) if self._current_live else {},
        })
        _save_events(events)
        return True

    def _send_once(self, key, kind, signature, text):
        st = self.state.setdefault(key, {})
        sent = st.setdefault("last_sent", {})
        if sent.get(kind) == signature:
            return False
        if self.notifier.send(text):
            sent[kind] = signature
            _save_state(self.state)
            self._record_event(key, kind, signature, text, telegram_sent=True)
            return True
        return False

    def pending_events(self, key=None):
        events = _load_events()
        if key is None:
            return events
        asset = str(key).upper()
        return [e for e in events if str(e.get("asset", "")).upper() == asset]

    def ack_events(self, ids):
        ids = {str(x) for x in (ids or [])}
        if not ids:
            return
        events = [e for e in _load_events() if str(e.get("id")) not in ids]
        _save_events(events)

    def evaluate(self, key, asset_rows, live_rows, new_flags):
        if not self.enabled or key.lower() not in self.assets:
            return

        live = self._live_map(live_rows)
        self._current_live = live
        st = self.state.setdefault(key, {})
        symbol = str(live.get("market.symbol", key.upper()))
        now = time.time()

        # Limpiar watches vencidos.
        for watch_name in ("primary_watch", "scalp_watch", "primary_pretrigger", "scalp_pretrigger"):
            w = st.get(watch_name)
            if w and float(w.get("expires", 0)) < now:
                st.pop(watch_name, None)

        # 1H: detectar candidato PRIMARY.
        if new_flags.get("1h"):
            direction, score, total = self._choose_direction(self._score_primary, live, minimum=5)
            close_ts = str(live.get("data.last_close_1h", ""))
            if direction:
                st["primary_watch"] = {
                    "direction": direction,
                    "expires": now + 3 * 3600,
                    "source_close": close_ts,
                }
                oi = live.get("oi.change_1h_pct", "")
                msg = (
                    f"🔎 {symbol} — CANDIDATO PRIMARY 1H\n"
                    f"Dirección preliminar: {direction}\n"
                    f"Pre-score técnico: {score}/{total}\n"
                    f"Cierre 1H: {close_ts}\n"
                    f"Precio: {live.get('1h.close', '')}\n"
                    f"RSI 1H: {live.get('1h.rsi14', '')}\n"
                    f"OI 1H: {oi if oi != '' else 'en maduración/fallback'}\n"
                    f"Estado: VIGILAR — esperar trigger 15m.\n"
                    f"No es señal final; validar con el agente."
                )
                self._send_once(key, "primary", f"{direction}:{close_ts}", msg)

        # 15m: confirmar PRIMARY si hay watch y detectar setup SCALP.
        if new_flags.get("15m"):
            close15 = str(live.get("data.last_close_15m", ""))

            pw = st.get("primary_watch")
            if pw:
                direction = pw.get("direction")
                trigger = None

                if key.lower() in ("solv", "xrp"):
                    pre = st.get("primary_pretrigger")
                    if pre and pre.get("direction") != direction:
                        st.pop("primary_pretrigger", None)
                        pre = None

                    if pre:
                        confirmed = self._confirm_pretrigger(asset_rows["15m"], pre, direction)
                        if confirmed and confirmed.get("status") == "TRIGGER":
                            trigger = confirmed.get("reason")
                            level = pre.get("level")
                            source_close = str(pre.get("source_close", ""))
                            self._record_event(
                                key,
                                "primary_pretrigger_confirmed",
                                f"{direction}:{source_close}:{close15}:{level}",
                                (
                                    f"stage=CONFIRMED;tf=15m;reason={trigger};"
                                    f"level={level};source_close={source_close};confirm_close={close15};"
                                    + self._research_snapshot(live)
                                ),
                                telegram_sent=False,
                            )
                            st.pop("primary_pretrigger", None)
                        elif confirmed and confirmed.get("status") == "INVALID":
                            level = pre.get("level")
                            source_close = str(pre.get("source_close", ""))
                            self._record_event(
                                key,
                                "primary_pretrigger_invalid",
                                f"{direction}:{source_close}:{close15}:{level}",
                                (
                                    f"stage=INVALID;tf=15m;reason={pre.get('reason', '')};"
                                    f"level={level};source_close={source_close};invalid_close={close15};"
                                    + self._research_snapshot(live)
                                ),
                                telegram_sent=False,
                            )
                            st.pop("primary_pretrigger", None)

                    if not trigger:
                        candidate = self._trigger_15m_solv(asset_rows["15m"], live, direction)
                        if candidate and candidate.get("status") == "TRIGGER":
                            trigger = candidate.get("reason")
                            st.pop("primary_pretrigger", None)
                        elif candidate and candidate.get("status") == "PRE":
                            level = candidate.get("level")
                            reason = candidate.get("reason")
                            st["primary_pretrigger"] = {
                                "direction": direction,
                                "reason": reason,
                                "level": level,
                                "source_close": close15,
                                "expires": now + 45 * 60,
                            }
                            self._record_event(
                                key,
                                "primary_pretrigger",
                                f"{direction}:{close15}:{level}",
                                (
                                    f"stage=PRE;tf=15m;reason={reason};level={level};"
                                    f"source_close={close15};"
                                    + self._research_snapshot(live)
                                ),
                                telegram_sent=False,
                            )
                else:
                    # Ruta legacy solo para activos futuros que no usen PRE-TRIGGER.
                    trigger = self._trigger_15m_legacy(asset_rows["15m"], live, direction)

                if trigger:
                    msg = (
                        f"⚡ {symbol} — TRIGGER 15M CANDIDATO\n"
                        f"PRIMARY preliminar: {direction}\n"
                        f"Trigger: {trigger}\n"
                        f"Cierre 15m: {close15}\n"
                        f"Precio: {live.get('15m.close', '')}\n"
                        f"Vol rel 15m: {live.get('15m.volume_rel20', '')}\n"
                        f"Acción: abre el agente y usa ANALIZA {key.upper()} AHORA.\n"
                        f"Requiere validación final de estructura, stop y R:R."
                    )
                    self._send_once(key, "primary_trigger", f"{direction}:{close15}", msg)

            direction, score, total = self._choose_direction(self._score_scalp, live, minimum=5)
            if direction:
                existing_pre = st.get("scalp_pretrigger")
                if existing_pre and existing_pre.get("direction") != direction:
                    st.pop("scalp_pretrigger", None)
                st["scalp_watch"] = {
                    "direction": direction,
                    "expires": now + 45 * 60,
                    "source_close": close15,
                }

        # 1m: timing para SCALP solo cuando un setup 15m está en vigilancia.
        if new_flags.get("1m"):
            sw = st.get("scalp_watch")
            if sw:
                direction = sw.get("direction")
                close1 = str(live.get("data.last_close_1m", ""))
                trigger = None

                if key.lower() in ("solv", "xrp"):
                    pre = st.get("scalp_pretrigger")
                    if pre and pre.get("direction") != direction:
                        st.pop("scalp_pretrigger", None)
                        pre = None

                    if pre:
                        confirmed = self._confirm_pretrigger(asset_rows["1m"], pre, direction)
                        if confirmed and confirmed.get("status") == "TRIGGER":
                            trigger = confirmed.get("reason")
                            level = pre.get("level")
                            source_close = str(pre.get("source_close", ""))
                            self._record_event(
                                key,
                                "scalp_pretrigger_confirmed",
                                f"{direction}:{source_close}:{close1}:{level}",
                                (
                                    f"stage=CONFIRMED;tf=1m;reason={trigger};"
                                    f"level={level};source_close={source_close};confirm_close={close1};"
                                    + self._research_snapshot(live)
                                ),
                                telegram_sent=False,
                            )
                            st.pop("scalp_pretrigger", None)
                        elif confirmed and confirmed.get("status") == "INVALID":
                            level = pre.get("level")
                            source_close = str(pre.get("source_close", ""))
                            self._record_event(
                                key,
                                "scalp_pretrigger_invalid",
                                f"{direction}:{source_close}:{close1}:{level}",
                                (
                                    f"stage=INVALID;tf=1m;reason={pre.get('reason', '')};"
                                    f"level={level};source_close={source_close};invalid_close={close1};"
                                    + self._research_snapshot(live)
                                ),
                                telegram_sent=False,
                            )
                            st.pop("scalp_pretrigger", None)

                    if not trigger:
                        candidate = self._trigger_1m_solv(asset_rows["1m"], live, direction)
                        if candidate and candidate.get("status") == "TRIGGER":
                            trigger = candidate.get("reason")
                            st.pop("scalp_pretrigger", None)
                        elif candidate and candidate.get("status") == "PRE":
                            level = candidate.get("level")
                            reason = candidate.get("reason")
                            st["scalp_pretrigger"] = {
                                "direction": direction,
                                "reason": reason,
                                "level": level,
                                "source_close": close1,
                                "expires": now + 5 * 60,
                            }
                            self._record_event(
                                key,
                                "scalp_pretrigger",
                                f"{direction}:{close1}:{level}",
                                (
                                    f"stage=PRE;tf=1m;reason={reason};level={level};"
                                    f"source_close={close1};"
                                    + self._research_snapshot(live)
                                ),
                                telegram_sent=False,
                            )
                else:
                    # Ruta legacy solo para activos futuros que no usen PRE-TRIGGER.
                    trigger = self._trigger_1m_legacy(asset_rows["1m"], live, direction)

                if trigger:
                    msg = (
                        f"🚨 {symbol} — TIMING SCALP 1M CANDIDATO\n"
                        f"Dirección preliminar: {direction}\n"
                        f"Trigger: {trigger}\n"
                        f"Cierre 1m: {close1}\n"
                        f"Precio: {live.get('1m.close', '')}\n"
                        f"RSI 1m: {live.get('1m.rsi14', '')}\n"
                        f"Vol rel 1m: {live.get('1m.volume_rel20', '')}\n"
                        f"Acción: abre el agente y usa ANALIZA {key.upper()} AHORA.\n"
                        f"No es entrada automática; el agente debe validar el setup."
                    )
                    if self._send_once(key, "scalp_trigger", f"{direction}:{close1}", msg):
                        st.pop("scalp_watch", None)
                        st.pop("scalp_pretrigger", None)

        _save_state(self.state)
