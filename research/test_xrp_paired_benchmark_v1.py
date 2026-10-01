#!/usr/bin/env python3
from __future__ import annotations
import csv, json, subprocess, sys, tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone

ROOT=Path(__file__).resolve().parents[1]
EVAL=ROOT/"research/xrp_paired_benchmark_evaluator_v1.py"

def write(path,headers,rows):
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=headers);w.writeheader();w.writerows(rows)

def main():
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        caps=[];cur=[];cha=[];outs=[]
        start=datetime(2026,10,2,tzinfo=timezone.utc)
        for i in range(1200):
            dt=start+timedelta(days=i//20,minutes=i%20)
            pid=f"P{i:04d}";sha=f"{i:064x}"[-64:]
            typ="SCALP_TRIGGER" if i%2==0 else "PRIMARY_TRIGGER"
            caps.append({"Pair ID":pid,"Alert UTC":dt.isoformat().replace("+00:00","Z"),"Alert Type":typ,"Eligibility":"FORMAL_PROSPECTIVE","Snapshot SHA256":sha})
            common={"Pair ID":pid,"Status":"COMPLETE","Snapshot SHA256":sha,"Rule Commit SHA":"a"*40,"Output SHA256":"b"*64}
            cur.append({**common,"Benchmark State":"TRADE_LONG" if i%3 else "NO_TRADE"})
            cha.append({**common,"Benchmark State":"TRADE_SHORT" if i%5==0 else "NO_TRADE"})
            # Negative raw return makes challenger shorts favorable on its traded subset.
            outs.append({"Pair ID":pid,"Outcome Complete":"COMPLETE","Raw Fwd 15m %":-0.20,"Raw Fwd 60m %":-0.20})
        write(td/"caps.csv",["Pair ID","Alert UTC","Alert Type","Eligibility","Snapshot SHA256"],caps)
        dh=["Pair ID","Status","Snapshot SHA256","Rule Commit SHA","Output SHA256","Benchmark State"]
        write(td/"cur.csv",dh,cur);write(td/"cha.csv",dh,cha)
        write(td/"out.csv",["Pair ID","Outcome Complete","Raw Fwd 15m %","Raw Fwd 60m %"],outs)
        p=subprocess.run([sys.executable,str(EVAL),"--captures",str(td/"caps.csv"),"--current",str(td/"cur.csv"),"--challenger",str(td/"cha.csv"),"--outcomes",str(td/"out.csv"),"--round-trip-cost-bps","1","--outdir",str(td/"res")],capture_output=True,text=True,check=True)
        rep=json.loads((td/"res/XRP_PAIRED_RESULTS_V1.json").read_text())
        assert rep["complete_pair_count"]==1200
        assert rep["sample_gate"] is True
        assert rep["provenance_gate"] is True
        assert rep["round_trip_cost_bps"]==1.0
        assert rep["verdict"] in ("CHALLENGER_SUPERIOR","CURRENT_SUPERIOR","INCONCLUSIVE")
        print("PASS XRP_PAIRED_EVALUATOR_SMOKE")
        print(f"pairs={rep['complete_pair_count']} days={rep['calendar_days']} verdict={rep['verdict']}")

if __name__=="__main__":main()
