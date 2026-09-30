#!/usr/bin/env python3
from __future__ import annotations
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from forward_v3_tracker import ForwardV3Tracker, FORWARD_START_UTC

UTC=timezone.utc

def iso(dt):
    return dt.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00","Z")

def make_rows(interval_min,count,last_available,base=1.0,current_volume=100.0,last_volume=200.0,last_taker_ratio=0.8):
    """
    Build Binance-like closed kline rows ending exactly at last_available.
    row[0]=open UTC, row[6]=close UTC (.999), row[9]=taker buy base.
    """
    out=[]
    step=timedelta(minutes=interval_min)
    first_open=last_available - step*count
    for i in range(count):
        op=first_open + step*i
        av=op+step
        close_time=av-timedelta(milliseconds=1)
        # Force a mild trend so 12-bar return is >1% in 15m fixtures.
        frac=i/max(1,count-1)
        close=base*(1+0.025*frac)
        open_=close*(1-0.0002)
        high=close*(1+0.0005)
        low=close*(1-0.0005)
        vol=current_volume
        taker=vol*0.5
        if i==count-1:
            vol=last_volume
            taker=vol*last_taker_ratio
        out.append([
            iso(op),open_,high,low,close,vol,iso(close_time),close*vol,100,taker,close*taker
        ])
    return out

def append_future_1m(rows,minutes,missing_k=None):
    last_available=datetime.fromisoformat(rows[-1][6].replace("Z","+00:00"))+timedelta(milliseconds=1)
    last_close=float(rows[-1][4])
    out=list(rows)
    for k in range(1,minutes+1):
        if missing_k is not None and k==missing_k:
            continue
        op=last_available+timedelta(minutes=k-1)
        av=last_available+timedelta(minutes=k)
        close_time=av-timedelta(milliseconds=1)
        close=last_close*(1+0.00005*k)
        out.append([
            iso(op),close,close*1.0003,close*0.9997,close,100.0,iso(close_time),close*100,80,50.0,close*50
        ])
    return out

def fake_oi(session,decision_ms):
    return 0.006, iso(datetime.fromtimestamp(decision_ms/1000,tz=UTC))

def main():
    decision=datetime(2026,10,2,0,0,0,tzinfo=UTC)
    one=make_rows(1,30,decision,base=1.0,last_volume=250.0,last_taker_ratio=0.8)
    fifteen=make_rows(15,30,decision,base=1.0,last_volume=250.0,last_taker_ratio=0.5)
    caches={"1m":one,"15m":fifteen}

    with tempfile.TemporaryDirectory() as td:
        td=Path(td)

        # Gate: before forward start must emit nothing.
        pre=ForwardV3Tracker(
            state_path=td/"pre.json",
            now_fn=lambda: FORWARD_START_UTC-timedelta(seconds=1),
            oi_feature_fetcher=fake_oi,
        )
        ev,out=pre.evaluate(caches,{"1m":True,"15m":True},session=None)
        assert ev==[] and out==[], (ev,out)

        tracker=ForwardV3Tracker(
            state_path=td/"state.json",
            now_fn=lambda: decision+timedelta(minutes=1),
            oi_feature_fetcher=fake_oi,
        )
        ev,out=tracker.evaluate(caches,{"1m":True,"15m":True},session=None)
        assert len(ev)==3, len(ev)
        assert out==[], out
        ids={r[2] for r in ev}
        assert ids=={
            "XRP-FWD-V3-A-TAKER-EXHAUSTION",
            "XRP-FWD-V3-B-OI-MODERATOR",
            "XRP-FWD-V3-C-MOMENTUM-EXHAUSTION",
        }
        assert all(r[5].startswith("2026-10-02T00:00:00") for r in ev)
        tracker.ack(event_rows=ev)

        # Retry same exact decision: no duplicate event rows.
        ev2,out2=tracker.evaluate(caches,{"1m":True,"15m":True},session=None)
        assert ev2==[], ev2
        assert out2==[], out2

        # Missing exact 5m target is not finalized during grace.
        missing_short=append_future_1m(one,9,missing_k=5)
        pending=tracker.pending_outcome_rows(missing_short)
        assert not any(r[4]==5 for r in pending), pending

        # Once grace expires, exact missing target becomes INCOMPLETE, never nearest.
        missing_long=append_future_1m(one,11,missing_k=5)
        pending=tracker.pending_outcome_rows(missing_long)
        h5=[r for r in pending if r[4]==5]
        assert len(h5)==1
        assert h5[0][10]=="INCOMPLETE"
        assert h5[0][7]=="" and h5[0][8]=="" and h5[0][9]==""

        # Full exact future window yields all 7 expected candidate/horizon rows.
        full=append_future_1m(one,245)
        pending=tracker.pending_outcome_rows(full)
        expected={
            ("XRP-FWD-V3-A-TAKER-EXHAUSTION",5),
            ("XRP-FWD-V3-A-TAKER-EXHAUSTION",15),
            ("XRP-FWD-V3-A-TAKER-EXHAUSTION",30),
            ("XRP-FWD-V3-B-OI-MODERATOR",60),
            ("XRP-FWD-V3-C-MOMENTUM-EXHAUSTION",15),
            ("XRP-FWD-V3-C-MOMENTUM-EXHAUSTION",60),
            ("XRP-FWD-V3-C-MOMENTUM-EXHAUSTION",240),
        }
        got={(r[2],int(r[4])) for r in pending}
        assert got==expected, (got,expected)
        assert all(r[10]=="COMPLETE" for r in pending)
        tracker.ack(outcome_rows=pending)
        assert tracker.pending_outcome_rows(full)==[]

        # Durable reload preserves acknowledgements/idempotence.
        tracker2=ForwardV3Tracker(
            state_path=td/"state.json",
            now_fn=lambda: decision+timedelta(hours=5),
            oi_feature_fetcher=fake_oi,
        )
        ev3,out3=tracker2.evaluate(caches,{"1m":True,"15m":True},session=None)
        assert ev3==[] and out3==[]

    print("PASS XRP_FORWARD_V3_CAPTURE_SMOKE")
    print("events=3 outcomes=7 pre_start_block=PASS retry_idempotence=PASS exact_window=PASS")

if __name__=="__main__":
    main()
