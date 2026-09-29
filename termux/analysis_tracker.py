#!/usr/bin/env python3
from datetime import datetime, timezone, timedelta


HORIZONS = (5, 15, 30, 60, 240)


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


class AnalysisTracker:
    """
    Shadow tracker de TODOS los ANALIZA de SOLV/XRP.

    No convierte análisis en trades y no modifica SIGNALS.
    Solo rellena resultados forward desde Mark Price usando velas 1m cerradas:
      - retorno a 5/15/30/60/240m
      - MFE/MAE a 15/60/240m
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

        if latest_dt >= analysis_dt + timedelta(minutes=240):
            update["outcomeStatus"] = "COMPLETE"
        elif any_metric:
            update["outcomeStatus"] = "PARTIAL"
        else:
            update["outcomeStatus"] = str(item.get("outcomeStatus") or "PENDING")

        return update if any_metric or update.get("outcomeStatus") == "COMPLETE" else None
