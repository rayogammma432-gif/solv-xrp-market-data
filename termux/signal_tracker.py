#!/usr/bin/env python3
from datetime import datetime, timezone, timedelta


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


class SignalTracker:
    """
    Forward tracker determinista de señales SOLV.

    - Solo rastrea señales ACTIVE/OPEN registradas en SIGNALS.
    - Usa velas cerradas 1m para TP/SL/MFE/MAE.
    - Usa 15m para Bars elapsed de SCALP y 1H para PRIMARY.
    - 50% TP1 + 50% TP2; tras TP1, stop de la mitad restante a BE.
    - Si TP y stop/BE ocurren en la misma vela 1m y el orden no se puede
      determinar, cierra como AMBIGUOUS y no asigna Result R.
    - TIME STOP es una regla de evaluación/performance; nunca ejecuta órdenes.
    """

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

    def _close_update(
        self, sig, result, result_r, mfe, mae, bars, close_utc,
        exit_price, exit_reason, tp1_hit_utc="", time_status="OK"
    ):
        return {
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

        start_dt = _ceil_minute(signal_dt)
        one_min = []
        for row in rows_by_tf.get("1m", []):
            open_dt = _dt(row[0])
            if open_dt and open_dt >= start_dt:
                one_min.append(row)
        if not one_min:
            return None

        # Los máximos/mínimos se calculan desde la primera vela 1m completa
        # posterior a la señal para no mezclar recorrido previo a la señal.
        highs = [float(r[2]) for r in one_min]
        lows = [float(r[3]) for r in one_min]
        if direction == "LONG":
            mfe = (max(highs) - entry) / risk
            mae = (entry - min(lows)) / risk
        else:
            mfe = (entry - min(lows)) / risk
            mae = (max(highs) - entry) / risk

        tf = "15m" if motor.startswith("SCALP") else "1h"
        bars = sum(
            1 for r in rows_by_tf.get(tf, [])
            if (_dt(r[6]) is not None and _dt(r[6]) > signal_dt)
        )

        tp1_hit_utc = str(sig.get("tp1HitUtc") or "")
        tp1_already = bool(tp1_hit_utc)
        r1 = self._r_at(direction, entry, risk, tp1)
        r2 = self._r_at(direction, entry, risk, tp2)

        for row in one_min:
            high = float(row[2])
            low = float(row[3])
            close_utc = str(row[6])
            close_price = float(row[4])

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
                        sig, "AMBIGUOUS", None, mfe, mae, bars,
                        close_utc, close_price, "AMBIGUOUS",
                        tp1_hit_utc="", time_status="OK"
                    )

                if sl_hit:
                    return self._close_update(
                        sig, "LOSS", -1.0, mfe, mae, bars,
                        close_utc, stop, "SL",
                        tp1_hit_utc="", time_status="OK"
                    )

                if t1_hit:
                    tp1_already = True
                    tp1_hit_utc = close_utc

                    # Si en la misma vela se alcanza TP1 y también vuelve a BE,
                    # el orden intravela no es demostrable con datos de 1m.
                    if be_same and not t2_hit:
                        return self._close_update(
                            sig, "AMBIGUOUS", None, mfe, mae, bars,
                            close_utc, close_price, "AMBIGUOUS",
                            tp1_hit_utc=tp1_hit_utc, time_status="OK"
                        )

                    if t2_hit:
                        result_r = 0.5 * r1 + 0.5 * r2
                        return self._close_update(
                            sig, "WIN", result_r, mfe, mae, bars,
                            close_utc, tp2, "TP2",
                            tp1_hit_utc=tp1_hit_utc, time_status="OK"
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
                        sig, "AMBIGUOUS", None, mfe, mae, bars,
                        close_utc, close_price, "AMBIGUOUS",
                        tp1_hit_utc=tp1_hit_utc, time_status="OK"
                    )

                if t2_hit:
                    result_r = 0.5 * r1 + 0.5 * r2
                    return self._close_update(
                        sig, "WIN", result_r, mfe, mae, bars,
                        close_utc, tp2, "TP2",
                        tp1_hit_utc=tp1_hit_utc, time_status="OK"
                    )

                if be_hit:
                    result_r = 0.5 * r1
                    return self._close_update(
                        sig, "WIN" if result_r > 0 else "BE",
                        result_r, mfe, mae, bars,
                        close_utc, entry, "TP1_BE",
                        tp1_hit_utc=tp1_hit_utc, time_status="OK"
                    )

        latest = one_min[-1]
        latest_close = float(latest[4])
        latest_utc = str(latest[6])

        # El time stop solo se aplica antes de TP1. Tras TP1 manda TP2/BE.
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
                reason = "TIME_STOP"
                update = self._close_update(
                    sig, "TIME_STOP", result_r, mfe, mae, bars,
                    latest_utc, latest_close, reason,
                    tp1_hit_utc="", time_status="TIME_STOP"
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

        # Actualización incremental de métricas aunque la señal siga abierta.
        return {
            "id": sig["id"],
            "mfeR": round(max(0.0, mfe), 4),
            "maeR": round(max(0.0, mae), 4),
            "barsElapsed": int(bars),
            "tp1HitUtc": tp1_hit_utc,
            "timeStopStatus": time_status or "OK",
        }

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
