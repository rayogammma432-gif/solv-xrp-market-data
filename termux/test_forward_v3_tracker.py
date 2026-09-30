#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import historical_feature_builder_v1 as hf
import historical_normalizer_v1 as hn
from forward_v3_tracker import (
    CANDIDATES,
    FORWARD_START_MS,
    FORWARD_START_UTC,
    PROTOCOL_VERSION,
    ForwardV3Tracker,
    iso_ms,
    parse_iso_ms,
    rel_volume20,
    resample_15m_from_1m,
    ret_12,
    row_available_at_ms,
    taker_imbalance,
)

UTC=timezone.utc


def raw_kline(open_ms, price, volume=100.0, taker_ratio=0.5):
    close_ms=open_ms+59_999
    close=price
    return [
        open_ms,
        f"{price:.10f}",
        f"{price*1.0005:.10f}",
        f"{price*0.9995:.10f}",
        f"{close:.10f}",
        f"{volume:.10f}",
        close_ms,
        f"{close*volume:.10f}",
        50,
        f"{volume*taker_ratio:.10f}",
        f"{close*volume*taker_ratio:.10f}",
        "0"
    ]


def row_from_raw(k):
    return [
        iso_ms(k[0]),float(k[1]),float(k[2]),float(k[3]),float(k[4]),float(k[5]),
        iso_ms(k[6]),float(k[7]),int(k[8]),float(k[9]),float(k[10])
    ]


class Resp:
    def __init__(self,data):
        self._data=data
    def raise_for_status(self):
        return None
    def json(self):
        return self._data


class FakeSession:
    def __init__(self, raw_1m, oi_rows=None):
        self.raw_1m=list(raw_1m)
        self.oi_rows=list(oi_rows or [])
        self.kline_calls=0
        self.oi_calls=0
    def get(self,url,params=None,timeout=30):
        params=params or {}
        if url.endswith("/fapi/v1/klines"):
            self.kline_calls+=1
            s=int(params["startTime"]);e=int(params["endTime"])
            lim=int(params.get("limit",1500))
            arr=[x for x in self.raw_1m if s<=int(x[0])<=e][:lim]
            return Resp(arr)
        if url.endswith("/futures/data/openInterestHist"):
            self.oi_calls+=1
            s=int(params.get("startTime",0));e=int(params.get("endTime",2**63-1))
            arr=[x for x in self.oi_rows if s<=int(x["timestamp"])<=e]
            return Resp(arr[:int(params.get("limit",20))])
        raise AssertionError(url)


def make_series(start_open, minutes):
    out=[]
    for i in range(minutes):
        # Gentle trend produces deterministic 15m ret_12.
        p=1.0*(1+0.00012*i)
        out.append(raw_kline(start_open+i*60_000,p))
    return out


def test_pre_start_gate():
    with tempfile.TemporaryDirectory() as td:
        tracker=ForwardV3Tracker(
            state_path=Path(td)/"state.json",
            now_fn=lambda: FORWARD_START_UTC-timedelta(seconds=1),
        )
        s=FakeSession([])
        ev,out,health=tracker.evaluate(s)
        assert (ev,out,health)==([],[],[])
        assert s.kline_calls==0


def test_paginated_catchup_and_all_new_minutes():
    start_open=FORWARD_START_MS-400*60_000
    raw=make_series(start_open, 405)
    # Make four post-last-eval rows strong A candidates.
    for k in range(len(raw)-4,len(raw)):
        raw[k][5]="300.0"; raw[k][7]=f"{float(raw[k][4])*300:.10f}"
        raw[k][9]="240.0"; raw[k][10]=f"{float(raw[k][4])*240:.10f}"

    oi=[]
    for ts in range(FORWARD_START_MS-60*60_000,FORWARD_START_MS+60*60_000,300_000):
        oi.append({"timestamp":ts,"sumOpenInterest":str(1000+((ts//300_000)%20)*10)})

    now=datetime.fromtimestamp((int(raw[-1][6])+1)/1000,tz=UTC)+timedelta(seconds=10)
    with tempfile.TemporaryDirectory() as td:
        tr=ForwardV3Tracker(
            state_path=Path(td)/"state.json",
            now_fn=lambda: now,
            oi_feature_fetcher=lambda session,decision:(0.006,iso_ms(decision)),
        )
        # Pretend everything through four minutes ago was already evaluated.
        tr.state["coverage"]["last_evaluated_1m_ms"]=row_available_at_ms(row_from_raw(raw[-5]))
        # Avoid historical 15m replay in this catch-up-specific assertion.
        tr.state["coverage"]["last_evaluated_15m_ms"]=row_available_at_ms(
            resample_15m_from_1m([row_from_raw(x) for x in raw])[-2]
        )
        tr._save_state = None if False else getattr(tr,"_save_state",None)
        # Persist state via normal helper behavior on evaluate.
        from forward_v3_tracker import _save_state
        _save_state(tr.state_path,tr.state)

        s=FakeSession(raw,oi)
        ev,out,health=tr.evaluate(s)
        assert tr.state["coverage"]["last_evaluated_1m_ms"]==row_available_at_ms(row_from_raw(raw[-1]))
        hour=tr.state["coverage"]["hours"][iso_ms((row_available_at_ms(row_from_raw(raw[-1]))//3_600_000)*3_600_000)]
        assert hour["evaluated_1m"]==4, hour
        assert hour["events_a"]==4, hour
        assert len([r for r in ev if r[2]=="XRP-FWD-V3-A-TAKER-EXHAUSTION"])==4

    # Separate pagination assertion >1500 rows.
    long_raw=make_series(FORWARD_START_MS-2100*60_000,2000)
    with tempfile.TemporaryDirectory() as td:
        tr=ForwardV3Tracker(state_path=Path(td)/"p.json",now_fn=lambda: FORWARD_START_UTC)
        s=FakeSession(long_raw)
        rows=tr._fetch_1m_window(
            s,
            int(long_raw[0][6])+1,
            int(long_raw[-1][6])+1,
        )
        assert len(rows)==2000
        assert s.kline_calls>=2


def test_resample_and_feature_parity():
    start_open=FORWARD_START_MS-450*60_000
    raw=make_series(start_open,450)
    rows=[row_from_raw(x) for x in raw]
    live15=resample_15m_from_1m(rows)
    assert len(live15)==30

    db=sqlite3.connect(":memory:")
    hn.init_db(db)
    for k in raw:
        om=int(k[0]);cm=int(k[6])
        db.execute(
            "INSERT INTO contract_1m VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("XRPUSDT",om,cm,om,cm+1,float(k[1]),float(k[2]),float(k[3]),float(k[4]),
             float(k[5]),float(k[7]),int(k[8]),float(k[9]),float(k[10]),
             "synthetic","sha","synthetic",0,hn.NORM)
        )
    hn.resample_contract(db,"XRPUSDT")
    hist=db.execute(
        "SELECT open_time_ms,close_time_ms,available_at_ms,open,high,low,close,volume,quote_volume,trades,taker_buy_base,taker_buy_quote "
        "FROM contract_resampled WHERE symbol='XRPUSDT' AND timeframe='15m' ORDER BY open_time_ms"
    ).fetchall()
    assert len(hist)==len(live15)

    for h,l in zip(hist,live15):
        assert h[0]==parse_iso_ms(l[0])
        assert h[1]==parse_iso_ms(l[6])
        assert h[2]==row_available_at_ms(l)
        for hv,lv in zip(h[3:12],[l[1],l[2],l[3],l[4],l[5],l[7],l[8],l[9],l[10]]):
            assert abs(float(hv)-float(lv))<1e-9, (hv,lv)

    bars=[{
        "open_time_ms":h[0],"close_time_ms":h[1],"available_at_ms":h[2],
        "open":h[3],"high":h[4],"low":h[5],"close":h[6],"volume":h[7],
        "quote_volume":h[8],"trades":h[9],"taker_buy_base":h[10],"taker_buy_quote":h[11]
    } for h in hist]
    feats=hf.calc_price_features(bars,{},15)
    assert abs(feats[-1]["ret_12"]-ret_12(live15))<1e-12
    assert abs(feats[-1]["rel_volume20"]-rel_volume20(live15))<1e-12
    assert abs(feats[-1]["taker_imbalance"]-taker_imbalance(live15[-1]))<1e-12


def test_recovery_and_health():
    decision=FORWARD_START_MS+15*60_000
    eid=f"XRP-FWD-V3-C-MOMENTUM-EXHAUSTION|{iso_ms(decision)}"
    event=[
        eid,PROTOCOL_VERSION,"XRP-FWD-V3-C-MOMENTUM-EXHAUSTION","XRPUSDT",
        "PRIMARY_15M_RESAMPLED_1M",iso_ms(decision),iso_ms(decision-900_000),"SHORT",1.2,
        0.02,2.0,"","",json.dumps(CANDIDATES["XRP-FWD-V3-C-MOMENTUM-EXHAUSTION"]["params"]),
        json.dumps({"xrp_ret_12":0.02,"xrp_rel_volume20":2.0}),
        "FEATURES_V1_LIVE_EQUIV_V1","LIVE_BINANCE_NORMALIZATION_EQUIV_V1",iso_ms(decision),"",
        "registry","sha","protocol","protocolsha","collector",iso_ms(decision),"git","payload",
        "receptor",iso_ms(decision)
    ]
    health=[
        f"{PROTOCOL_VERSION}|{iso_ms(FORWARD_START_MS)}",PROTOCOL_VERSION,iso_ms(FORWARD_START_MS),
        60,60,0,4,4,0,4,0,0,0,1,0,0,iso_ms(FORWARD_START_MS+59*60_000),
        iso_ms(FORWARD_START_MS+45*60_000),"collector","git","hash","receptor",iso_ms(FORWARD_START_MS+70*60_000)
    ]
    recovery={"events":[event],"outcomeIds":[f"{eid}|H15"],"latestHealth":health}
    with tempfile.TemporaryDirectory() as td:
        tr=ForwardV3Tracker(
            state_path=Path(td)/"state.json",
            now_fn=lambda: FORWARD_START_UTC+timedelta(hours=2, minutes=11),
        )
        tr.reconcile_remote(recovery)
        rec=tr.state["events"][eid]
        assert rec["event_posted"] is True
        assert rec["posted_horizons"]==[15]
        assert tr.state["coverage"]["last_evaluated_1m_ms"]==parse_iso_ms(health[16])
        assert tr.state["coverage"]["last_evaluated_15m_ms"]==parse_iso_ms(health[17])

        # A finalized hour with a missing minute must surface it.
        hkey=iso_ms(FORWARD_START_MS+3_600_000)
        tr.state["coverage"]["hours"][hkey]={
            "evaluated_1m":59,"evaluated_15m":4,"oi_checks":4,"oi_failures":1,
            "events_a":2,"events_b":0,"events_c":1
        }
        rows=tr.pending_health_rows()
        target=[r for r in rows if r[2]==hkey]
        assert len(target)==1
        assert target[0][5]==1
        assert target[0][8]==0


def main():
    test_pre_start_gate()
    test_paginated_catchup_and_all_new_minutes()
    test_resample_and_feature_parity()
    test_recovery_and_health()
    print("PASS XRP_FORWARD_V3_1_CAPTURE_PARITY_RECOVERY")
    print("pre_start=PASS catchup=PASS pagination=PASS resample_parity=PASS feature_parity=PASS recovery=PASS health=PASS")


if __name__=="__main__":
    main()
