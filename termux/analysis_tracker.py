#!/usr/bin/env python3
from datetime import datetime, timezone, timedelta


HORIZONS = (5, 15, 30, 60, 240)
EXECUTION_HORIZON_MINUTES = 240


def _dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).strip().replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def _num(value):
    try:
        if value in ("", None):
            return None
        return float(value)
    except Exception:
        return None


def _pct(base, value):
    if not base:
        return None
    return ((value / base) - 1.0) * 100.0


def _ceil_minute(dt):
    if dt.second == 0 and dt.microsecond == 0:
        return dt
    return (dt + timedelta(minutes=1)).replace(second=0, microsecond=0)


def _plan_direction(entry, stop, tp1, tp2):
    if None in (entry, stop, tp1, tp2):
        return None
    if stop < entry < tp1 <= tp2:
        return "LONG"
    if stop > entry > tp1 >= tp2:
        return "SHORT"
    return "INVALID"


def _touches(row, price):
    low = float(row[3])
    high = float(row[2])
    return low <= price <= high


class AnalysisTracker:
    """
    Shadow tracker de TODOS los ANALIZA de SOLV/XRP.

    No convierte análisis en trades y no modifica SIGNALS.

    Mantiene las métricas forward históricas:
      - retorno a 5/15/30/60/240m
      - MFE/MAE a 15/60/240m

    Y añade auditoría cronológica de ejecución a 1m:
      - valida geometría Entry/Stop/TP
      - detecta fill
      - determina qué barrera ocurrió primero (TP1 o STOP)
      - marca AMBIGUOUS cuando ambas barreras caen dentro de la misma vela 1m
      - calcula R realizado para TP1/STOP
      - nunca infiere el orden desde MFE/MAE
    """

    def evaluate(self, key, pending_analyses, rows_1m):
        if key.lower() not in ("solv", "xrp"):
            return []
        updates = []
        for item in pending_analyses or []:
            try:
                u = self._evaluate_one(item, rows_1m)
                if u:
                    updates.append(u)
            except Exception:
                continue
        return updates

    def _execution_audit(self, item, rows_1m, analysis_dt, latest_dt):
        entry = _num(item.get("entry"))
        stop = _num(item.get("stop"))
        tp1 = _num(item.get("tp1"))
        tp2 = _num(item.get("tp2"))

        if None in (entry, stop, tp1, tp2):
            return {
                "planDirection": "",
                "geometryValid": "N/A",
                "executionAuditStatus": "N/A",
                "executionAuditNotes": "MISSING_LEVELS",
            }

        direction = _plan_direction(entry, stop, tp1, tp2)
        if direction == "INVALID":
            return {
                "planDirection": "INVALID",
                "geometryValid": "NO",
                "executionAuditStatus": "COMPLETE",
                "firstBarrier": "INVALID_GEOMETRY",
                "executionAuditNotes": "Entry/Stop/TP no forman LONG ni SHORT válido.",
            }

        audit = {
            "planDirection": direction,
            "geometryValid": "YES",
        }

        primary_bias = str(item.get("primaryBias") or "").upper()
        notes = []
        if primary_bias in ("LONG", "SHORT") and primary_bias != direction:
            notes.append(f"BIAS_PLAN_MISMATCH:{primary_bias}->{direction}")

        start_open = _ceil_minute(analysis_dt)
        target = analysis_dt + timedelta(minutes=EXECUTION_HORIZON_MINUTES)
        window = []
        for r in rows_1m or []:
            open_dt = _dt(r[0])
            close_dt = _dt(r[6])
            if open_dt is None or close_dt is None:
                continue
            if open_dt >= start_open and close_dt <= target:
                window.append((open_dt, close_dt, r))

        if not window:
            audit["executionAuditStatus"] = "PENDING"
            if notes:
                audit["executionAuditNotes"] = ";".join(notes)
            return audit

        filled = False
        fill_close_dt = None
        fill_utc = ""
        risk = abs(entry - stop)
        reward_r = abs(tp1 - entry) / risk if risk > 0 else None

        for open_dt, close_dt, row in window:
            if not filled:
                if not _touches(row, entry):
                    continue
                filled = True
                fill_close_dt = close_dt
                fill_utc = close_dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")
                audit["entryFilledUtc"] = fill_utc
                audit["minutesToFill"] = round(
                    max(0.0, (close_dt - analysis_dt).total_seconds() / 60.0), 2
                )

                stop_same = _touches(row, stop)
                tp_same = _touches(row, tp1)
                if stop_same or tp_same:
                    audit["firstBarrier"] = "AMBIGUOUS_ENTRY_BAR"
                    audit["executionExitUtc"] = fill_utc
                    audit["minutesInTrade"] = 0.0
                    audit["executionAuditStatus"] = "COMPLETE"
                    notes.append(
                        "ENTRY_AND_BARRIER_SAME_1M"
                        + (":BOTH" if stop_same and tp_same else ":STOP" if stop_same else ":TP1")
                    )
                    audit["executionAuditNotes"] = ";".join(notes)
                    return audit
                continue

            stop_hit = _touches(row, stop)
            tp_hit = _touches(row, tp1)
            exit_utc = close_dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")

            if stop_hit and tp_hit:
                audit["firstBarrier"] = "AMBIGUOUS_SAME_1M"
                audit["executionExitUtc"] = exit_utc
                audit["minutesInTrade"] = round(
                    max(0.0, (close_dt - fill_close_dt).total_seconds() / 60.0), 2
                )
                audit["executionAuditStatus"] = "COMPLETE"
                notes.append("TP1_AND_STOP_SAME_1M")
                audit["executionAuditNotes"] = ";".join(notes)
                return audit

            if tp_hit:
                audit["firstBarrier"] = "TP1"
                audit["executionExitUtc"] = exit_utc
                audit["realizedR"] = round(reward_r, 4)
                audit["minutesInTrade"] = round(
                    max(0.0, (close_dt - fill_close_dt).total_seconds() / 60.0), 2
                )
                audit["executionAuditStatus"] = "COMPLETE"
                if notes:
                    audit["executionAuditNotes"] = ";".join(notes)
                return audit

            if stop_hit:
                audit["firstBarrier"] = "STOP"
                audit["executionExitUtc"] = exit_utc
                audit["realizedR"] = -1.0
                audit["minutesInTrade"] = round(
                    max(0.0, (close_dt - fill_close_dt).total_seconds() / 60.0), 2
                )
                audit["executionAuditStatus"] = "COMPLETE"
                if notes:
                    audit["executionAuditNotes"] = ";".join(notes)
                return audit

        if latest_dt >= target:
            audit["executionAuditStatus"] = "COMPLETE"
            if filled:
                audit["firstBarrier"] = "OPEN_240M"
                notes.append("NO_TP1_OR_STOP_WITHIN_240M")
            else:
                audit["firstBarrier"] = "NO_FILL"
                notes.append("ENTRY_NOT_TOUCHED_WITHIN_240M")
        else:
            audit["executionAuditStatus"] = "PARTIAL"
            if filled:
                audit["firstBarrier"] = "OPEN"
            else:
                audit["firstBarrier"] = "WAITING_ENTRY"

        if notes:
            audit["executionAuditNotes"] = ";".join(notes)
        return audit

    def _evaluate_one(self, item, rows_1m):
        analysis_id = str(item.get("analysisId") or "")
        analysis_dt = _dt(item.get("analysisUtc"))
        base = _num(item.get("markPrice"))
        if not analysis_id or analysis_dt is None or base in (None, 0):
            return None

        candles = []
        for r in rows_1m or []:
            close_dt = _dt(r[6])
            if close_dt and close_dt > analysis_dt:
                candles.append((close_dt, r))
        if not candles:
            return None

        latest_dt = candles[-1][0]
        update = {"analysisId": analysis_id}
        any_metric = False

        for minutes in HORIZONS:
            target = analysis_dt + timedelta(minutes=minutes)
            eligible = [(dt, r) for dt, r in candles if dt <= target]
            if latest_dt < target or not eligible:
                continue
            row = eligible[-1][1]
            update[f"fwd{minutes}mPct"] = round(_pct(base, float(row[4])), 4)
            any_metric = True

        for minutes in (15, 60, 240):
            target = analysis_dt + timedelta(minutes=minutes)
            eligible = [r for dt, r in candles if dt <= target]
            if latest_dt < target or not eligible:
                continue
            high = max(float(r[2]) for r in eligible)
            low = min(float(r[3]) for r in eligible)
            update[f"mfe{minutes}mPct"] = round(max(0.0, _pct(base, high)), 4)
            update[f"mae{minutes}mPct"] = round(max(0.0, -_pct(base, low)), 4)
            any_metric = True

        update.update(self._execution_audit(item, rows_1m, analysis_dt, latest_dt))

        if latest_dt >= analysis_dt + timedelta(minutes=240):
            update["outcomeStatus"] = "COMPLETE"
        elif any_metric:
            update["outcomeStatus"] = "PARTIAL"
        else:
            update["outcomeStatus"] = str(item.get("outcomeStatus") or "PENDING")

        return update if any_metric or update.get("executionAuditStatus") else None
