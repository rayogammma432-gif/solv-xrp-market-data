from __future__ import annotations
import argparse, csv, hashlib, json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REGISTRY_PATH=Path("research/experiments/XRP_HYPOTHESIS_REGISTRY_V2.jsonl")
REGISTRY_SHA256="ab6a355df4699a284ff51ee49ff8e0f944b98e902b87b46384a6957eb9066912"

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def ms(s):
    dt=datetime.fromisoformat(s.replace("Z","+00:00"))
    if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp()*1000)

def dayq(t):
    dt=datetime.fromtimestamp(t/1000,tz=timezone.utc)
    return dt.strftime("%Y-%m-%d"), f"{dt.year}-Q{(dt.month-1)//3+1}"

def num(row,idx,name):
    x=row[idx[name]]
    return None if x=="" else float(x)

def load_outcomes(path):
    out={}
    with open(path,newline="",encoding="utf-8") as f:
        rr=csv.reader(f); h=next(rr); idx={c:i for i,c in enumerate(h)}
        for r in rr:
            out[(r[idx["decision_grid"]],int(r[idx["decision_time_ms"]]))]={c:r[i] for c,i in idx.items()}
    return out

def oval(o,name):
    x=o.get(name,"")
    return None if x=="" else float(x)

def signed_exc(o,h,d):
    up=oval(o,f"raw_up_excursion_{h}m"); dn=oval(o,f"raw_down_excursion_{h}m")
    if up is None or dn is None: return None,None
    return (up,-dn) if d>0 else (-dn,up)

def empty_dir():
    return {"n":0,"sum":0.0,"long_n":0,"short_n":0,"secondary":{}}

def empty_comp():
    return {"a_n":0,"a_sum":0.0,"b_n":0,"b_sum":0.0}

def add_secondary(bucket,key,val):
    if val is None: return
    s=bucket["secondary"].setdefault(key,{"n":0,"sum":0.0})
    s["n"]+=1; s["sum"]+=val

def add_dir(bucket,d,val,secondary):
    bucket["n"]+=1; bucket["sum"]+=val
    if d>0: bucket["long_n"]+=1
    else: bucket["short_n"]+=1
    for k,v in secondary.items(): add_secondary(bucket,k,v)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--features",required=True)
    ap.add_argument("--outcomes",required=True)
    ap.add_argument("--target-start",required=True)
    ap.add_argument("--target-end",required=True)
    ap.add_argument("--outdir",default="validation-part")
    args=ap.parse_args()

    if sha256_file(REGISTRY_PATH)!=REGISTRY_SHA256:
        raise SystemExit("V2 registry SHA mismatch")

    regs=[json.loads(x) for x in REGISTRY_PATH.read_text().splitlines() if x.strip()]
    reg={x["hypothesis_id"]:x for x in regs}
    start,end=ms(args.target_start),ms(args.target_end)
    outcomes=load_outcomes(args.outcomes)

    daily={
        "XRP-V2-H1-PRIMARY-MOMENTUM-EXHAUSTION":{},
        "XRP-V2-H2-PRIMARY-OI-MODERATOR":{},
        "XRP-V2-H3-SCALP-TAKER-FLOW-EXHAUSTION":{},
    }

    with open(args.features,newline="",encoding="utf-8") as f:
        rr=csv.reader(f); header=next(rr); idx={c:i for i,c in enumerate(header)}
        for row in rr:
            t=int(row[idx["decision_time_ms"]])
            if not (start<=t<end): continue
            grid=row[idx["decision_grid"]]
            o=outcomes.get((grid,t))
            if o is None: continue
            day,quarter=dayq(t)

            if grid=="PRIMARY_15M":
                # V2-H1 fixed momentum exhaustion.
                r12=num(row,idx,"xrp_ret_12")
                rv=num(row,idx,"xrp_rel_volume20")
                f60=oval(o,"forward_return_60m")
                if None not in (r12,rv,f60) and abs(r12)>=0.01 and rv>=1.5:
                    d=-1 if r12>0 else 1
                    val=d*f60
                    b=daily["XRP-V2-H1-PRIMARY-MOMENTUM-EXHAUSTION"].setdefault(day,{"quarter":quarter,**empty_dir()})
                    mfe,mae=signed_exc(o,60,d)
                    sec={
                        "signed_15m": None if oval(o,"forward_return_15m") is None else d*oval(o,"forward_return_15m"),
                        "signed_240m": None if oval(o,"forward_return_240m") is None else d*oval(o,"forward_return_240m"),
                        "mfe_60m":mfe,
                        "mae_60m":mae
                    }
                    add_dir(b,d,val,sec)

                # V2-H2 fixed OI moderator.
                oi=num(row,idx,"xrp_oi_chg_15m")
                if None not in (r12,oi,f60) and abs(r12)>=0.005:
                    d=1 if r12>0 else -1
                    sv=d*f60
                    grp="A" if oi>=0.005 else ("B" if oi<=-0.005 else None)
                    if grp:
                        b=daily["XRP-V2-H2-PRIMARY-OI-MODERATOR"].setdefault(day,{"quarter":quarter,**empty_comp()})
                        if grp=="A":
                            b["a_n"]+=1; b["a_sum"]+=sv
                        else:
                            b["b_n"]+=1; b["b_sum"]+=sv

            elif grid=="SCALP_1M":
                # V2-H3 fixed taker-flow exhaustion.
                ti=num(row,idx,"xrp_taker_imbalance")
                rv=num(row,idx,"xrp_rel_volume20")
                f15=oval(o,"forward_return_15m")
                if None not in (ti,rv,f15) and abs(ti)>=0.30 and rv>=1.5:
                    d=-1 if ti>0 else 1
                    val=d*f15
                    b=daily["XRP-V2-H3-SCALP-TAKER-FLOW-EXHAUSTION"].setdefault(day,{"quarter":quarter,**empty_dir()})
                    mfe,mae=signed_exc(o,15,d)
                    sec={
                        "signed_5m": None if oval(o,"forward_return_5m") is None else d*oval(o,"forward_return_5m"),
                        "signed_30m": None if oval(o,"forward_return_30m") is None else d*oval(o,"forward_return_30m"),
                        "mfe_15m":mfe,
                        "mae_15m":mae
                    }
                    add_dir(b,d,val,sec)

    out=Path(args.outdir); out.mkdir(parents=True,exist_ok=True)
    report={
        "registry_sha256":REGISTRY_SHA256,
        "target_start":args.target_start,
        "target_end":args.target_end,
        "features_sha256":sha256_file(args.features),
        "outcomes_sha256":sha256_file(args.outcomes),
        "daily":daily,
        "holdout_2026_opened":False
    }
    p=out/"XRP_VALIDATION_PART_V2.json"
    p.write_text(json.dumps(report,separators=(",",":")),encoding="utf-8")
    print(json.dumps({
        "target_start":args.target_start,
        "target_end":args.target_end,
        "days_by_hypothesis":{k:len(v) for k,v in daily.items()},
        "holdout_2026_opened":False
    },indent=2))

if __name__=="__main__":
    main()
