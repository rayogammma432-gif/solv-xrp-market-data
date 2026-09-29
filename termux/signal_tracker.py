#!/usr/bin/env python3
from datetime import datetime, timezone, timedelta
from statistics import mean


def _dt(value):
    if not value:
        return None
    s = str(value).strip()
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def _num(value):
    try:
        if value in ("", None):
            return None
        return float(value)
    except Exception:
        return None


def _ceil_minute(dt):
    if dt.second == 0 and dt.microsecond == 0:
        return dt
    return (dt + timedelta(minutes=1)).replace(second=0, microsecond=0)


def _ema(values, period):
    if len(values) < period:
        return None
    alpha = 2.0 / (period + 1.0)
    value = mean(values[:period])
    for x in values[period:]:
        value = alpha * x + (1.0 - alpha) * value
    return value


def _rma(values, period):
    if len(values) < period:
        return None
    value = mean(values[:period])
    for x in values[period:]:
        value = (value * (period - 1) + x) / period
    return value


def _rsi(rows, period=14):
    closes = [float(r[4]) for r in rows]
    if len(closes) < period + 1:
        return None
    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(x, 0.0) for x in changes]
    losses = [max(-x, 0.0) for x in changes]
    avg_gain = _rma(gains, period)
    avg_loss = _rma(losses, period)
    if avg_gain is None or avg_loss is None:
        return None
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _micro_state(rows):
    if len(rows) < 3:
        return "NEUTRAL"
    a, b = rows[-2], rows[-1]
    ah, al, ac = float(a[2]), float(a[3]), float(a[4])
    bh, bl, bc = float(b[2]), float(b[3]), float(b[4])
    if bh > ah and bl >= al and bc > ac:
        return "BULL"
    if bh <= ah and bl < al and bc < ac:
        return "BEAR"
    return "NEUTRAL"


def _bars_until(rows, signal_dt, until_dt):
    return sum(
        1
        for r in rows
        if (_dt(r[6]) is not None and _dt(r[6]) > signal_dt and _dt(r[6]) <= until_dt)
    )


class SignalTracker:
    """
    Forward tracker determinista de señales SOLV.

    - Rastrea señales OPEN registradas en SIGNALS.
    - Usa velas cerradas 1m para TP/SL/MFE/MAE.
    - SCALP: guarda telemetría PASIVA a 5/10/15 velas 1m completas.
    - La telemetría 1m NO modifica la lógica activa de TIME STOP.
    - Usa 15m para Bars elapsed de SCALP y 1H para PRIMARY.
    - 50% TP1 + 50% TP2; tras TP1, stop del 50% restante a BE.
    - Si TP y stop/BE ocurren en la misma vela 1m y no puede conocerse
      el orden, cierra como AMBIGUOUS y no inventa Result R.
    - TIME STOP es tracking/gestión analítica; nunca ejecuta órdenes.
    """

    SNAP_MINUTES = (5, 10, 15)

    def __init__(self, alerts=None):
        self.alerts = alerts

    def _can_alert(self, key):
        if not self.alerts or not getattr(self.alerts, "enabled", False):
            return False
        assets = getattr(self.alerts, "assets", set())
        return key.lower() in assets

    def _notify(self, key, text):
        if self._can_alert(key):
            try:
                self.alerts.notifier.send(text)
            except Exception:
                pass

    def _r_at(self, direction, entry, risk, price):
        if direction == "LONG":
            return (price - entry) / risk
        return (entry - price) / risk

    def _snapshot(self, sig, direction, entry, risk, one_min_prefix, all_1m):
        n = len(one_min_prefix)
        if n not in self.SNAP_MINUTES:
            return {}

        suffix = f"{n}m"
        existing_key = f"mfe{n}mR"
        if sig.get(existing_key) not in ("", None):
            return {}

        snap_row = one_min_prefix[-1]
        snap_open = str(snap_row[0])
        idx = None
        for i, r in enumerate(all_1m):
            if str(r[0]) == snap_open:
                idx = i
                break
        if idx is None:
            return {}

        prefix = all_1m[: idx + 1]
        highs = [float(r[2]) for r in one_min_prefix]
        lows = [float(r[3]) for r in one_min_prefix]

        if direction == "LONG":
            mfe = (max(highs) - entry) / risk
            mae = (entry - min(lows)) / risk
        else:
            mfe = (entry - min(lows)) / risk
            mae = (max(highs) - entry) / risk

        closes = [float(r[4]) for r in prefix]
        ema20 = _ema(closes, 20)
        close = float(snap_row[4])
        if ema20 is None:
            ema_side = ""
        elif close > ema20:
            ema_side = "ABOVE"
        elif close < ema20:
            ema_side = "BELOW"
        else:
            ema_side = "AT"

        rsi14 = _rsi(prefix, 14)
        return {
            f"mfe{n}mR": round(max(0.0, mfe), 4),
            f"mae{n}mR": round(max(0.0, mae), 4),
            f"rsi{n}m": None if rsi14 is None else round(rsi14, 2),
            f"ema20Side{n}m": ema_side,
            f"micro{n}m": _micro_state(prefix),
        }

    def _close_update(
        self, sig, result, result_r, mfe, mae, bars, close_utc,
        exit_price, exit_reason, tp1_hit_utc="", time_status="OK",
        telemetry=None
    ):
        out = {
            "id": sig["id"],
            "state": "CLOSED",
            "result": result,
            "resultR": None if result_r is None else round(result_r, 4),
            "mfeR": round(max(0.0, mfe), 4),
            "maeR": round(max(0.0, mae), 4),
            "barsElapsed": int(bars),
            "tp1HitUtc": tp1_hit_utc or sig.get("tp1HitUtc", ""),
            "closeUtc": close_utc,
            "exitPrice": None if exit_price is None else float(exit_price),
            "exitReason": exit_reason,
            "timeStopStatus": time_status,
        }
        if telemetry:
            out.update(telemetry)
        return out

    def _evaluate_one(self, key, sig, rows_by_tf):
        direction = str(sig.get("direction", "")).upper()
        motor = str(sig.get("motor", "")).upper()
        state = str(sig.get("state", "")).upper()
        if state != "OPEN" or direction not in ("LONG", "SHORT"):
            return None

        entry = _num(sig.get("entry"))
        stop = _num(sig.get("stop"))
        tp1 = _num(sig.get("tp1"))
        tp2 = _num(sig.get("tp2"))
        signal_dt = _dt(sig.get("signalUtc"))
        if None in (entry, stop, tp1, tp2) or signal_dt is None:
            return None

        risk = abs(entry - stop)
        if risk <= 0:
            return None
        if direction == "LONG" and not (stop < entry < tp1 <= tp2):
            return None
        if direction == "SHORT" and not (stop > entry > tp1 >= tp2):
            return None

        all_1m = rows_by_tf.get("1m", [])
        start_dt = _ceil_minute(signal_dt)
        one_min = []
        for row in all_1m:
            open_dt = _dt(row[0])
            if open_dt and open_dt >= start_dt:
                one_min.append(row)
        if not one_min:
            return None

        tf = "15m" if motor.startswith("SCALP") else "1h"
        tp1_hit_utc = str(sig.get("tp1HitUtc") or "")
        tp1_already = bool(tp1_hit_utc)
        known_tp1_dt = _dt(tp1_hit_utc) if tp1_already else None
        r1 = self._r_at(direction, entry, risk, tp1)
        r2 = self._r_at(direction, entry, risk, tp2)
        telemetry = {}

        running_high = None
        running_low = None

        for i, row in enumerate(one_min, 1):
            high = float(row[2])
            low = float(row[3])
            close_utc = str(row[6])
            close_price = float(row[4])
            close_dt = _dt(close_utc)

            running_high = high if running_high is None else max(running_high, high)
            running_low = low if running_low is None else min(running_low, low)

            if direction == "LONG":
                mfe = (running_high - entry) / risk
                mae = (entry - running_low) / risk
            else:
                mfe = (entry - running_low) / risk
                mae = (running_high - entry) / risk

            if motor.startswith("SCALP") and i in self.SNAP_MINUTES:
                telemetry.update(
                    self._snapshot(sig, direction, entry, risk, one_min[:i], all_1m)
                )

            bars_at_row = _bars_until(
                rows_by_tf.get(tf, []), signal_dt, close_dt or signal_dt
            )

            # Si TP1 ya venía registrado de un ciclo anterior, no tratamos
            # velas anteriores al hit como si el stop ya estuviera en BE.
            if known_tp1_dt is not None and close_dt is not None and close_dt <= known_tp1_dt:
                continue

            if not tp1_already:
                if direction == "LONG":
                    sl_hit = low <= stop
                    t1_hit = high >= tp1
                    t2_hit = high >= tp2
                    be_same = low <= entry
                else:
                    sl_hit = high >= stop
                    t1_hit = low <= tp1
                    t2_hit = low <= tp2
                    be_same = high >= entry

                if sl_hit and t1_hit:
                    return self._close_update(
                        sig, "AMBIGUOUS", None, mfe, mae, bars_at_row,
                        close_utc, close_price, "AMBIGUOUS",
                        tp1_hit_utc="", time_status="OK", telemetry=telemetry
                    )

                if sl_hit:
                    return self._close_update(
                        sig, "LOSS", -1.0, mfe, mae, bars_at_row,
                        close_utc, stop, "SL",
                        tp1_hit_utc="", time_status="OK", telemetry=telemetry
                    )

                if t1_hit:
                    tp1_already = True
                    tp1_hit_utc = close_utc
                    known_tp1_dt = close_dt

                    if be_same and not t2_hit:
                        return self._close_update(
                            sig, "AMBIGUOUS", None, mfe, mae, bars_at_row,
                            close_utc, close_price, "AMBIGUOUS",
                            tp1_hit_utc=tp1_hit_utc, time_status="OK",
                            telemetry=telemetry
                        )

                    if t2_hit:
                        result_r = 0.5 * r1 + 0.5 * r2
                        return self._close_update(
                            sig, "WIN", result_r, mfe, mae, bars_at_row,
                            close_utc, tp2, "TP2",
                            tp1_hit_utc=tp1_hit_utc, time_status="OK",
                            telemetry=telemetry
                        )
                    continue

            else:
                if direction == "LONG":
                    be_hit = low <= entry
                    t2_hit = high >= tp2
                else:
                    be_hit = high >= entry
                    t2_hit = low <= tp2

                if be_hit and t2_hit:
                    return self._close_update(
                        sig, "AMBIGUOUS", None, mfe, mae, bars_at_row,
                        close_utc, close_price, "AMBIGUOUS",
                        tp1_hit_utc=tp1_hit_utc, time_status="OK",
                        telemetry=telemetry
                    )

                if t2_hit:
                    result_r = 0.5 * r1 + 0.5 * r2
                    return self._close_update(
                        sig, "WIN", result_r, mfe, mae, bars_at_row,
                        close_utc, tp2, "TP2",
                        tp1_hit_utc=tp1_hit_utc, time_status="OK",
                        telemetry=telemetry
                    )

                if be_hit:
                    result_r = 0.5 * r1
                    return self._close_update(
                        sig, "WIN" if result_r > 0 else "BE",
                        result_r, mfe, mae, bars_at_row,
                        close_utc, entry, "TP1_BE",
                        tp1_hit_utc=tp1_hit_utc, time_status="OK",
                        telemetry=telemetry
                    )

        latest = one_min[-1]
        latest_close = float(latest[4])
        latest_utc = str(latest[6])
        latest_dt = _dt(latest_utc) or signal_dt

        if direction == "LONG":
            mfe = (running_high - entry) / risk
            mae = (entry - running_low) / risk
        else:
            mfe = (entry - running_low) / risk
            mae = (running_high - entry) / risk

        bars = _bars_until(rows_by_tf.get(tf, []), signal_dt, latest_dt)

        # TIME STOP ACTIVO: no cambia con la telemetría 1m.
        current_time_status = str(sig.get("timeStopStatus") or "OK").upper()
        if not tp1_already:
            if motor.startswith("SCALP"):
                review_bars, soft_stop_bars, hard_stop_bars = 2, 4, 6
            else:
                review_bars, soft_stop_bars, hard_stop_bars = 3, 6, 8

            should_soft_stop = bars >= soft_stop_bars and mfe < 0.5
            should_hard_stop = bars >= hard_stop_bars

            if should_soft_stop or should_hard_stop:
                result_r = self._r_at(direction, entry, risk, latest_close)
                update = self._close_update(
                    sig, "TIME_STOP", result_r, mfe, mae, bars,
                    latest_utc, latest_close, "TIME_STOP",
                    tp1_hit_utc="", time_status="TIME_STOP",
                    telemetry=telemetry
                )
                self._notify(
                    key,
                    f"⏰ {key.upper()} — TIME STOP\n"
                    f"{motor} {direction}\n"
                    f"Bars: {bars} | MFE: {mfe:.2f}R | Resultado paper: {result_r:.2f}R\n"
                    f"El tracker cerró la señal de performance; no ejecuta órdenes reales."
                )
                return update

            time_status = current_time_status
            if bars >= review_bars and mfe < 0.3:
                time_status = "REVIEW"
                if current_time_status != "REVIEW":
                    self._notify(
                        key,
                        f"⏳ {key.upper()} — REVISIÓN POR TIEMPO\n"
                        f"{motor} {direction}\n"
                        f"Bars: {bars} | MFE: {mfe:.2f}R\n"
                        f"La señal no desarrolla suficiente avance. Revisa protección/salida con el agente."
                    )
            elif current_time_status == "":
                time_status = "OK"
        else:
            time_status = "OK"

        out = {
            "id": sig["id"],
            "mfeR": round(max(0.0, mfe), 4),
            "maeR": round(max(0.0, mae), 4),
            "barsElapsed": int(bars),
            "tp1HitUtc": tp1_hit_utc,
            "timeStopStatus": time_status or "OK",
        }
        out.update(telemetry)
        return out

    def evaluate(self, key, open_signals, rows_by_tf):
        if key.lower() != "solv":
            return []
        updates = []
        for sig in open_signals or []:
            try:
                update = self._evaluate_one(key, sig, rows_by_tf)
                if update:
                    updates.append(update)
            except Exception:
                continue
        return updates
