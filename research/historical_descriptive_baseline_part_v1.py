from __future__ import annotations
import argparse, csv, json, math, os, sqlite3, tempfile
from array import array
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import historical_feature_builder_v1 as fb

CORE=[
 "xrp_ret_1","xrp_ret_12","xrp_rsi14","xrp_atr_pct","xrp_rel_volume20","xrp_taker_imbalance",
 "xrp_dist_ema50_atr","xrp_dist_vwap_atr","xrp_funding_rate","xrp_oi_chg_15m","xrp_oi_chg_60m",
 "btc_ret_1","btc_ret_12","btc_rsi14","btc_atr_pct","btc_oi_chg_15m","btc_oi_chg_60m"
]
EXCLUDE_PREFIX=("feature_set_version","normalization_version","decision_grid")
EXCLUDE_EXACT={
 "xrp_bar_open_time_ms","decision_time_ms","btc_bar_available_at_ms","xrp_metrics_available_at_ms",
 "btc_metrics_available_at_ms","xrp_funding_available_at_ms","btc_funding_available_at_ms",
 "xrp_mark_available_at_ms","xrp_index_available_at_ms","xrp_premium_available_at_ms"
}

def ms(iso):
    dt=datetime.fromisoformat(iso.replace("Z","+00:00"))
    if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp()*1000)

def q(arrv,p):
    if not arrv:return None
    n=len(arrv)
    if n==1:return float(arrv[0])
    x=(n-1)*p;i=int(math.floor(x));j=min(i+1,n-1);w=x-i
    return float(arrv[i]*(1-w)+arrv[j]*w)

def corr_from_stats(s):
    n=s["n"]
    if n<3:return None
    num=n*s["sumxy"]-s["sumx"]*s["sumy"]
    dx=n*s["sumxx"]-s["sumx"]*s["sumx"]
    dy=n*s["sumyy"]-s["sumy"]*s["sumy"]
    if dx<=0 or dy<=0:return None
    return num/math.sqrt(dx*dy)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--db",required=True)
    ap.add_argument("--target-start",required=True)
    ap.add_argument("--target-end",required=True)
    ap.add_argument("--outdir",default="baseline-output")
    args=ap.parse_args()
    start=ms(args.target_start);end=ms(args.target_end)
    out=Path(args.outdir);out.mkdir(parents=True,exist_ok=True)
    tmp=out/"_features_temp.csv"
    db=sqlite3.connect(args.db)
    header,total,grid_counts,sha=fb.build(db,tmp)
    db.close()
    idx={c:i for i,c in enumerate(header)}
    numeric=[c for c in header if c not in EXCLUDE_EXACT and c not in EXCLUDE_PREFIX and (c.startswith("xrp_") or c.startswith("btc_"))]
    vals={g:{c:array("d") for c in numeric} for g in fb.GRIDS}
    rows_by_grid=defaultdict(int);rows_by_month=defaultdict(lambda:defaultdict(int))
    pair={g:{} for g in fb.GRIDS}
    for g in fb.GRIDS:
        for i,a in enumerate(CORE):
            for b in CORE[i+1:]:
                pair[g][(a,b)]={"n":0,"sumx":0.0,"sumy":0.0,"sumxx":0.0,"sumyy":0.0,"sumxy":0.0}

    with open(tmp,newline="",encoding="utf-8") as f:
        rr=csv.reader(f);next(rr)
        for row in rr:
            t=int(row[idx["decision_time_ms"]])
            if t<start or t>=end:continue
            g=row[idx["decision_grid"]];rows_by_grid[g]+=1
            mon=datetime.fromtimestamp(t/1000,tz=timezone.utc).strftime("%Y-%m")
            rows_by_month[g][mon]+=1
            numrow={}
            for c in numeric:
                x=row[idx[c]]
                if x!="":
                    v=float(x)
                    if not math.isfinite(v):raise RuntimeError(f"nonfinite {c}")
                    vals[g][c].append(v);numrow[c]=v
            for (a,b),s in pair[g].items():
                if a in numrow and b in numrow:
                    x=numrow[a];y=numrow[b]
                    s["n"]+=1;s["sumx"]+=x;s["sumy"]+=y;s["sumxx"]+=x*x;s["sumyy"]+=y*y;s["sumxy"]+=x*y
    tmp.unlink(missing_ok=True)

    summaries={}
    for g in fb.GRIDS:
        summaries[g]={}
        totalg=rows_by_grid[g]
        for c in numeric:
            a=vals[g][c];n=len(a)
            if n:
                sm=sum(a);ss=sum(x*x for x in a);mn=min(a);mx=max(a);mean=sm/n
                sd=math.sqrt(max(0.0,(ss-sm*sm/n)/(n-1))) if n>1 else 0.0
                a=array("d",sorted(a))
                summaries[g][c]={
                    "rows":totalg,"non_null":n,"coverage":n/totalg if totalg else None,
                    "sum":sm,"sumsq":ss,"mean":mean,"sd":sd,"min":mn,
                    "p05":q(a,0.05),"p25":q(a,0.25),"p50":q(a,0.50),"p75":q(a,0.75),"p95":q(a,0.95),"max":mx
                }
            else:
                summaries[g][c]={"rows":totalg,"non_null":0,"coverage":0.0,"sum":0.0,"sumsq":0.0,
                                 "mean":None,"sd":None,"min":None,"p05":None,"p25":None,"p50":None,"p75":None,"p95":None,"max":None}
    correlations={}
    pair_stats={}
    for g in fb.GRIDS:
        correlations[g]={};pair_stats[g]={}
        for (a,b),s in pair[g].items():
            k=f"{a}|{b}";pair_stats[g][k]=s;correlations[g][k]=corr_from_stats(s)

    report={
        "baseline_version":"XRP_DESCRIPTIVE_BASELINE_V1",
        "feature_set":fb.FEATURE_SET,"normalization_version":fb.NORM,
        "target_start":args.target_start,"target_end":args.target_end,
        "feature_builder_sha":sha,"source_feature_rows_before_filter":total,
        "rows_by_grid":dict(rows_by_grid),
        "rows_by_month":{g:dict(v) for g,v in rows_by_month.items()},
        "summaries":summaries,"core_pair_stats":pair_stats,"core_correlations":correlations,
        "outcomes_used":False
    }
    (out/"DESCRIPTIVE_BASELINE_PART.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    lines=["# XRP Descriptive Baseline V1 — Partial","",
           f"Range: **{args.target_start} → {args.target_end}**","",
           f"- SCALP_1M rows: {rows_by_grid.get('SCALP_1M',0):,}",
           f"- PRIMARY_15M rows: {rows_by_grid.get('PRIMARY_15M',0):,}",
           "- Outcomes used: **NO**","",
           "## Selected coverage","",
           "| Grid | Feature | Coverage | Median | P05 | P95 |",
           "|---|---|---:|---:|---:|---:|"]
    selected=["xrp_ema200","xrp_rsi14","xrp_atr_pct","xrp_rel_volume20","xrp_funding_rate","xrp_sum_open_interest",
              "xrp_oi_chg_15m","xrp_count_toptrader_long_short_ratio","btc_sum_open_interest","btc_oi_chg_15m"]
    for g in fb.GRIDS:
        for c in selected:
            s=summaries[g].get(c)
            if not s:continue
            def fnum(x):return "" if x is None else f"{x:.6g}"
            lines.append(f"| {g} | {c} | {s['coverage']:.2%} | {fnum(s['p50'])} | {fnum(s['p05'])} | {fnum(s['p95'])} |")
    (out/"DESCRIPTIVE_BASELINE_PART.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":main()
