#!/usr/bin/env python3
from __future__ import annotations
import json
from datetime import datetime, timezone
from types import SimpleNamespace
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"termux"))
import market_collector as mc

UTC=timezone.utc

class Resp:
    def __init__(self,data): self._data=data
    def raise_for_status(self): return None
    def json(self): return self._data

class FakeSession:
    def get(self,url,params=None,timeout=30):
        p=params or {}
        limit=int(p.get("limit",255))
        tf=str(p["interval"])
        step=mc.TF_MS[tf]
        end=int(p["endTime"])
        # Last closed bar ends 1ms before an aligned boundary <= alert.
        boundary=(end//step)*step
        if boundary>end: boundary-=step
        rows=[]
        start=boundary-limit*step
        for i in range(limit):
            om=start+i*step
            cm=om+step-1
            price=0.60+(i*0.000001)
            vol=1000.0+i
            rows.append([
                om,str(price),str(price*1.001),str(price*0.999),str(price),
                str(vol),cm,str(price*vol),100,str(vol*0.55),str(price*vol*0.55),"0"
            ])
        return Resp(rows)

def main():
    event={
        "id":"xrp:scalp_trigger:LONG:2026-10-01T05:59:59.999Z",
        "utc":"2026-10-01T06:00:05Z",
        "asset":"XRP",
        "type":"SCALP_TRIGGER",
        "direction":"LONG",
        "telegramSent":True,
        "research":{
            "market.mark_price":0.6,
            "detector.primary_score":"5/8",
            "detector.scalp_score":"6/7"
        }
    }
    s=FakeSession()
    a=mc._paired_snapshot_bundle(event,s)
    b=mc._paired_snapshot_bundle(event,s)
    assert a["capture"][16]==b["capture"][16]
    assert a["capture"][17]==b["capture"][17]
    assert [x[11] for x in a["segments"]]==[x[11] for x in b["segments"]]
    assert [x[10] for x in a["segments"]]==[x[10] for x in b["segments"]]
    assert len(a["capture"])==21
    assert len(a["segments"])==12
    assert a["capture"][18]=="FULL"
    assert len(a["capture"][17])==64
    alert_ms=int(datetime.fromisoformat(event["utc"].replace("Z","+00:00")).timestamp()*1000)
    seen=set()
    for seg in a["segments"]:
        assert len(seg)==14
        key=(seg[3],seg[4]);assert key not in seen;seen.add(key)
        bars=json.loads(seg[10])
        assert seg[8]==len(bars)==seg[7]
        assert seg[9]=="FULL"
        assert len(seg[11])==64
        assert len(seg[10])<48000, (key,len(seg[10]))
        assert all(int(r[6])<=alert_ms for r in bars)
        if key==("XRPUSDT","1m"):
            assert len(bars)==360
        else:
            assert len(bars)==250
    print("PASS XRP_PAIRED_SNAPSHOT_SMOKE")
    print("segments=12 full_hash=PASS no_lookahead=PASS cell_size=PASS xrp_1m=360")

if __name__=="__main__":main()
