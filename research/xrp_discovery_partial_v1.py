from __future__ import annotations
import argparse, csv, hashlib, itertools, json, math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REGISTRY_PATH=Path("research/experiments/XRP_HYPOTHESIS_REGISTRY_V1.jsonl")
REGISTRY_SHA256="54c0694bed4539300dd919f93349b8b33ddc7e5d9d5982efce08270ccba93479"

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

def ms(s):
    dt=datetime.fromisoformat(s.replace("Z","+00:00"))
    if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp()*1000)

def dayq(t):
    dt=datetime.fromtimestamp(t/1000,tz=timezone.utc)
    return dt.strftime("%Y-%m-%d"), f"{dt.year}-Q{(dt.month-1)//3+1}"

def num(row,idx,name):
    x=row[idx[name]]
    return None if x=="" else float(x)

def product_configs(h):
    keys=list(h["parameter_grid"].keys())
    vals=[h["parameter_grid"][k] for k in keys]
    out=[]
    for combo in itertools.product(*vals):
        p=dict(zip(keys,combo))
        cid="|".join(f"{k}={format(float(v),'.12g')}" for k,v in p.items())
        out.append((cid,p))
    return out

def empty_dir():
    return {"n":0,"sum":0.0,"long_n":0,"short_n":0,"secondary":{}}

def add_secondary(d,key,val):
    if val is None:return
    s=d["secondary"].setdefault(key,{"n":0,"sum":0.0})
    s["n"]+=1;s["sum"]+=val

def add_directional(bucket,direction,primary,secondary):
    bucket["n"]+=1;bucket["sum"]+=primary
    if direction>0:bucket["long_n"]+=1
    else:bucket["short_n"]+=1
    for k,v in secondary.items():add_secondary(bucket,k,v)

def empty_comp():
    return {"a_n":0,"a_sum":0.0,"b_n":0,"b_sum":0.0}

def add_comp(bucket,group,val):
    if group=="A":bucket["a_n"]+=1;bucket["a_sum"]+=val
    else:bucket["b_n"]+=1;bucket["b_sum"]+=val

def load_outcomes(path):
    out={}
    with open(path,newline="",encoding="utf-8") as f:
        rr=csv.reader(f);h=next(rr);idx={c:i for i,c in enumerate(h)}
        for r in rr:
            key=(r[idx["decision_grid"]],int(r[idx["decision_time_ms"]]))
            out[key]={c:r[i] for c,i in idx.items()}
    return out

def oval(o,name):
    x=o.get(name,"")
    return None if x=="" else float(x)

def signed_exc(o,h,d):
    up=oval(o,f"raw_up_excursion_{h}m");dn=oval(o,f"raw_down_excursion_{h}m")
    if up is None or dn is None:return None,None
    return (up,-dn) if d>0 else (-dn,up)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--features",required=True);ap.add_argument("--outcomes",required=True)
    ap.add_argument("--target-start",required=True);ap.add_argument("--target-end",required=True)
    ap.add_argument("--outdir",default="discovery-part")
    args=ap.parse_args()

    if sha256_file(REGISTRY_PATH)!=REGISTRY_SHA256:raise SystemExit("registry SHA mismatch")
    regs=[json.loads(x) for x in REGISTRY_PATH.read_text().splitlines() if x.strip()]
    reg={x["hypothesis_id"]:x for x in regs}
    configs={hid:product_configs(h) for hid,h in reg.items()}
    start,end=ms(args.target_start),ms(args.target_end)
    outcomes=load_outcomes(args.outcomes)

    daily={};events_h6={}
    for hid,h in reg.items():
        if hid=="XRP-H6-FUNDING-EXTREME-REVERSION":continue
        daily[hid]={cid:{} for cid,p in configs[hid]}

    with open(args.features,newline="",encoding="utf-8") as f:
        rr=csv.reader(f);header=next(rr);idx={c:i for i,c in enumerate(header)}
        last_h6_event=None
        for row in rr:
            t=int(row[idx["decision_time_ms"]])
            if not (start<=t<end):continue
            grid=row[idx["decision_grid"]]
            o=outcomes.get((grid,t))
            if o is None:continue
            day,quarter=dayq(t)

            # H6 first PRIMARY decision after each funding event, before other logic.
            if grid=="PRIMARY_15M":
                fe=row[idx["xrp_funding_available_at_ms"]]
                fr=num(row,idx,"xrp_funding_rate")
                if fe and fr is not None:
                    fei=int(fe)
                    if fei!=last_h6_event:
                        last_h6_event=fei
                        f240=oval(o,"forward_return_240m");f60=oval(o,"forward_return_60m")
                        if f240 is not None:
                            events_h6[str(fei)]={
                                "funding_event_ms":fei,"decision_time_ms":t,"day":day,"quarter":quarter,
                                "funding_rate":fr,"forward_return_240m":f240,"forward_return_60m":f60
                            }

            # H1
            if grid=="PRIMARY_15M" and t>=ms(reg["XRP-H1-PRIMARY-MOMENTUM"]["discovery_start"]):
                r12=num(row,idx,"xrp_ret_12");rv=num(row,idx,"xrp_rel_volume20");f60=oval(o,"forward_return_60m")
                if None not in (r12,rv,f60):
                    for cid,p in configs["XRP-H1-PRIMARY-MOMENTUM"]:
                        if abs(r12)>=p["abs_ret_12"] and rv>=p["rel_volume20_min"]:
                            d=1 if r12>0 else -1;val=d*f60
                            b=daily["XRP-H1-PRIMARY-MOMENTUM"][cid].setdefault(day,{"quarter":quarter,**empty_dir()})
                            mfe,mae=signed_exc(o,60,d)
                            sec={"signed_15m":None if oval(o,"forward_return_15m") is None else d*oval(o,"forward_return_15m"),
                                 "signed_240m":None if oval(o,"forward_return_240m") is None else d*oval(o,"forward_return_240m"),
                                 "mfe_60m":mfe,"mae_60m":mae}
                            add_directional(b,d,val,sec)

            # H2
            if grid=="PRIMARY_15M":
                x=num(row,idx,"xrp_dist_vwap_atr");f60=oval(o,"forward_return_60m")
                if None not in (x,f60):
                    for cid,p in configs["XRP-H2-PRIMARY-EXTENSION-REVERSION"]:
                        if abs(x)>=p["abs_dist_vwap_atr_min"]:
                            d=-1 if x>0 else 1;val=d*f60
                            b=daily["XRP-H2-PRIMARY-EXTENSION-REVERSION"][cid].setdefault(day,{"quarter":quarter,**empty_dir()})
                            mfe,mae=signed_exc(o,60,d)
                            sec={"signed_15m":None if oval(o,"forward_return_15m") is None else d*oval(o,"forward_return_15m"),
                                 "signed_240m":None if oval(o,"forward_return_240m") is None else d*oval(o,"forward_return_240m"),
                                 "mfe_60m":mfe,"mae_60m":mae}
                            add_directional(b,d,val,sec)

            # H3/H4 only 2022+
            if grid=="PRIMARY_15M" and t>=ms(reg["XRP-H3-PRIMARY-OI-CONFIRMATION"]["discovery_start"]):
                r12=num(row,idx,"xrp_ret_12");oi=num(row,idx,"xrp_oi_chg_15m");f60=oval(o,"forward_return_60m")
                if None not in (r12,oi,f60):
                    d=1 if r12>0 else -1;sv=d*f60
                    for cid,p in configs["XRP-H3-PRIMARY-OI-CONFIRMATION"]:
                        if abs(r12)>=p["abs_ret_12"] and oi>=p["oi_chg_15m_min"]:
                            b=daily["XRP-H3-PRIMARY-OI-CONFIRMATION"][cid].setdefault(day,{"quarter":quarter,**empty_dir()})
                            mfe,mae=signed_exc(o,60,d)
                            sec={"signed_240m":None if oval(o,"forward_return_240m") is None else d*oval(o,"forward_return_240m"),
                                 "mfe_60m":mfe,"mae_60m":mae}
                            add_directional(b,d,sv,sec)
                    for cid,p in configs["XRP-H4-PRIMARY-OI-MODERATOR"]:
                        if abs(r12)>=p["abs_ret_12"]:
                            grp="A" if oi>=p["abs_oi_chg_15m"] else ("B" if oi<=-p["abs_oi_chg_15m"] else None)
                            if grp:
                                b=daily["XRP-H4-PRIMARY-OI-MODERATOR"][cid].setdefault(day,{"quarter":quarter,**empty_comp()})
                                add_comp(b,grp,sv)

            # H5
            if grid=="PRIMARY_15M":
                xr=num(row,idx,"xrp_ret_12");br=num(row,idx,"btc_ret_12");f60=oval(o,"forward_return_60m")
                if None not in (xr,br,f60):
                    d=1 if xr>0 else -1;sv=d*f60
                    for cid,p in configs["XRP-H5-PRIMARY-BTC-ALIGNMENT"]:
                        if abs(xr)>=p["abs_xrp_ret_12"] and abs(br)>=p["abs_btc_ret_12"]:
                            grp="A" if xr*br>0 else ("B" if xr*br<0 else None)
                            if grp:
                                b=daily["XRP-H5-PRIMARY-BTC-ALIGNMENT"][cid].setdefault(day,{"quarter":quarter,**empty_comp()})
                                add_comp(b,grp,sv)

            # H7
            if grid=="SCALP_1M":
                ti=num(row,idx,"xrp_taker_imbalance");rv=num(row,idx,"xrp_rel_volume20");f15=oval(o,"forward_return_15m")
                if None not in (ti,rv,f15):
                    for cid,p in configs["XRP-H7-SCALP-TAKER-FLOW"]:
                        if abs(ti)>=p["abs_taker_imbalance_min"] and rv>=p["rel_volume20_min"]:
                            d=1 if ti>0 else -1;sv=d*f15
                            b=daily["XRP-H7-SCALP-TAKER-FLOW"][cid].setdefault(day,{"quarter":quarter,**empty_dir()})
                            mfe,mae=signed_exc(o,15,d)
                            sec={"signed_5m":None if oval(o,"forward_return_5m") is None else d*oval(o,"forward_return_5m"),
                                 "signed_30m":None if oval(o,"forward_return_30m") is None else d*oval(o,"forward_return_30m"),
                                 "mfe_15m":mfe,"mae_15m":mae}
                            add_directional(b,d,sv,sec)

    out=Path(args.outdir);out.mkdir(parents=True,exist_ok=True)
    report={
        "registry_sha256":REGISTRY_SHA256,"target_start":args.target_start,"target_end":args.target_end,
        "features_sha256":sha256_file(args.features),"outcomes_sha256":sha256_file(args.outcomes),
        "daily":daily,"h6_events":list(events_h6.values())
    }
    p=out/"XRP_DISCOVERY_PART.json";p.write_text(json.dumps(report,separators=(",",":")),encoding="utf-8")
    print(json.dumps({"target_start":args.target_start,"target_end":args.target_end,
                      "h6_events":len(events_h6),
                      "daily_config_counts":{h:sum(len(v) for v in cfgs.values()) for h,cfgs in daily.items()}},indent=2))

if __name__=="__main__":main()
