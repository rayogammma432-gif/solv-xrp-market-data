from __future__ import annotations
import argparse, bisect, csv, hashlib, json, math, sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

FEATURE_SET="FEATURES_V1"
NORM="HIST_NORM_V1"
GRIDS={"SCALP_1M":("1m",1),"PRIMARY_15M":("15m",15)}
PRICE_FEATURES=[
    "close","ret_1","ret_3","ret_12","ema20","ema50","ema200","rsi14","atr14","atr_pct",
    "dist_ema20_atr","dist_ema50_atr","dist_ema200_atr","rel_volume20","rel_trades20",
    "taker_buy_ratio","taker_imbalance","dist_prev20_high_atr","dist_prev20_low_atr",
    "session_vwap","dist_vwap_atr"
]

def safe_div(a,b):
    if a is None or b is None or b==0:return None
    return a/b

def ema(vals,n):
    out=[None]*len(vals)
    if len(vals)<n:return out
    seed=sum(vals[:n])/n
    out[n-1]=seed
    alpha=2/(n+1)
    prev=seed
    for i in range(n,len(vals)):
        prev=alpha*vals[i]+(1-alpha)*prev
        out[i]=prev
    return out

def rsi_wilder(closes,n=14):
    out=[None]*len(closes)
    if len(closes)<=n:return out
    gains=[];losses=[]
    for i in range(1,n+1):
        d=closes[i]-closes[i-1]
        gains.append(max(d,0.0));losses.append(max(-d,0.0))
    ag=sum(gains)/n;al=sum(losses)/n
    def calc(g,l):
        if l==0 and g>0:return 100.0
        if l==0 and g==0:return 50.0
        rs=g/l;return 100-(100/(1+rs))
    out[n]=calc(ag,al)
    for i in range(n+1,len(closes)):
        d=closes[i]-closes[i-1];g=max(d,0.0);l=max(-d,0.0)
        ag=((n-1)*ag+g)/n;al=((n-1)*al+l)/n
        out[i]=calc(ag,al)
    return out

def atr_wilder(bars,n=14):
    out=[None]*len(bars)
    trs=[]
    for i,b in enumerate(bars):
        if i==0:tr=b["high"]-b["low"]
        else:
            pc=bars[i-1]["close"]
            tr=max(b["high"]-b["low"],abs(b["high"]-pc),abs(b["low"]-pc))
        trs.append(tr)
    if len(trs)<n:return out
    a=sum(trs[:n])/n;out[n-1]=a
    for i in range(n,len(trs)):
        a=((n-1)*a+trs[i])/n
        out[i]=a
    return out

def utc_day(ms):
    return datetime.fromtimestamp(ms/1000,tz=timezone.utc).date().isoformat()

def load_1m(db,symbol):
    q="""SELECT open_time_ms,close_time_ms,available_at_ms,open,high,low,close,volume,quote_volume,trades,taker_buy_base,taker_buy_quote
         FROM contract_1m WHERE symbol=? ORDER BY open_time_ms"""
    cols=["open_time_ms","close_time_ms","available_at_ms","open","high","low","close","volume","quote_volume","trades","taker_buy_base","taker_buy_quote"]
    return [dict(zip(cols,r)) for r in db.execute(q,(symbol,))]

def load_grid(db,symbol,grid):
    if grid=="SCALP_1M":
        return load_1m(db,symbol)
    q="""SELECT open_time_ms,close_time_ms,available_at_ms,open,high,low,close,volume,quote_volume,trades,taker_buy_base,taker_buy_quote
         FROM contract_resampled WHERE symbol=? AND timeframe='15m' ORDER BY open_time_ms"""
    cols=["open_time_ms","close_time_ms","available_at_ms","open","high","low","close","volume","quote_volume","trades","taker_buy_base","taker_buy_quote"]
    return [dict(zip(cols,r)) for r in db.execute(q,(symbol,))]

def session_vwap_map(one_minute):
    out={}
    day=None;pv=0.0;vol=0.0
    for b in one_minute:
        d=utc_day(b["open_time_ms"])
        if d!=day:
            day=d;pv=0.0;vol=0.0
        typical=(b["high"]+b["low"]+b["close"])/3.0
        pv+=typical*b["volume"];vol+=b["volume"]
        out[b["open_time_ms"]]=pv/vol if vol>0 else None
    return out

def calc_price_features(bars,one_min_vwap,tf_min):
    closes=[b["close"] for b in bars]
    e20=ema(closes,20);e50=ema(closes,50);e200=ema(closes,200)
    rs=rsi_wilder(closes,14);at=atr_wilder(bars,14)
    out=[]
    for i,b in enumerate(bars):
        f={}
        f["close"]=b["close"]
        for n in (1,3,12):
            f[f"ret_{n}"]=b["close"]/closes[i-n]-1 if i>=n and closes[i-n]!=0 else None
        f["ema20"]=e20[i];f["ema50"]=e50[i];f["ema200"]=e200[i]
        f["rsi14"]=rs[i];f["atr14"]=at[i]
        f["atr_pct"]=safe_div(at[i],b["close"]) if at[i] is not None else None
        for n,e in ((20,e20[i]),(50,e50[i]),(200,e200[i])):
            f[f"dist_ema{n}_atr"]=(b["close"]-e)/at[i] if e is not None and at[i] not in (None,0) else None
        if i>=20:
            prev=bars[i-20:i]
            mv=sum(x["volume"] for x in prev)/20
            mt=sum(x["trades"] for x in prev)/20
            f["rel_volume20"]=safe_div(b["volume"],mv) if mv>0 else None
            f["rel_trades20"]=safe_div(b["trades"],mt) if mt>0 else None
            ph=max(x["high"] for x in prev);pl=min(x["low"] for x in prev)
            f["dist_prev20_high_atr"]=(b["close"]-ph)/at[i] if at[i] not in (None,0) else None
            f["dist_prev20_low_atr"]=(b["close"]-pl)/at[i] if at[i] not in (None,0) else None
        else:
            f["rel_volume20"]=None;f["rel_trades20"]=None
            f["dist_prev20_high_atr"]=None;f["dist_prev20_low_atr"]=None
        ratio=safe_div(b["taker_buy_base"],b["volume"]) if b["volume"]>0 else None
        f["taker_buy_ratio"]=ratio
        f["taker_imbalance"]=2*ratio-1 if ratio is not None else None
        last_min_open=b["open_time_ms"]+(tf_min-1)*60000
        vwap=one_min_vwap.get(last_min_open)
        f["session_vwap"]=vwap
        f["dist_vwap_atr"]=(b["close"]-vwap)/at[i] if vwap is not None and at[i] not in (None,0) else None
        out.append(f)
    return out

class Asof:
    def __init__(self,rows,key="available_at_ms"):
        self.rows=rows
        self.times=[r[key] for r in rows]
        self.key=key
    def get(self,t,max_age_ms=None):
        i=bisect.bisect_right(self.times,t)-1
        if i<0:return None
        r=self.rows[i]
        age=t-r[self.key]
        if max_age_ms is not None and age>max_age_ms:return None
        return r

def load_funding(db,symbol):
    cols=["source_timestamp_ms","available_at_ms","funding_rate"]
    return [dict(zip(cols,r)) for r in db.execute(
        "SELECT source_timestamp_ms,available_at_ms,funding_rate FROM funding WHERE symbol=? ORDER BY available_at_ms",(symbol,))]

METRIC_COLS=["sum_open_interest","sum_open_interest_value","count_toptrader_long_short_ratio","sum_toptrader_long_short_ratio","count_long_short_ratio","sum_taker_long_short_vol_ratio"]
def load_metrics(db,symbol):
    cols=["source_timestamp_ms","available_at_ms"]+METRIC_COLS+["source_zero","source_missing_fields"]
    rows=[dict(zip(cols,r)) for r in db.execute(
        """SELECT source_timestamp_ms,available_at_ms,sum_open_interest,sum_open_interest_value,
        count_toptrader_long_short_ratio,sum_toptrader_long_short_ratio,count_long_short_ratio,
        sum_taker_long_short_vol_ratio,source_zero,source_missing_fields
        FROM metrics WHERE symbol=? ORDER BY available_at_ms""",(symbol,))]
    return rows,{r["source_timestamp_ms"]:r for r in rows}

def load_aux(db,symbol,family):
    cols=["open_time_ms","available_at_ms","close"]
    return [dict(zip(cols,r)) for r in db.execute(
        "SELECT open_time_ms,available_at_ms,close FROM aux_kline_1m WHERE symbol=? AND family=? ORDER BY available_at_ms",(symbol,family))]

def pct_change_metric(cur,lookup,mins):
    if cur is None:return None
    oi=cur["sum_open_interest"]
    if oi is None or oi<=0:return None
    prev=lookup.get(cur["source_timestamp_ms"]-mins*60000)
    if prev is None:return None
    poi=prev["sum_open_interest"]
    if poi is None or poi<=0:return None
    return oi/poi-1

def derivative_context(db,symbol):
    frows=load_funding(db,symbol)
    mrows,mlookup=load_metrics(db,symbol)
    aux={}
    for fam in ("markPriceKlines","indexPriceKlines","premiumIndexKlines"):
        rows=load_aux(db,symbol,fam)
        aux[fam]=Asof(rows)
    return {
        "funding":Asof(frows),
        "metrics":Asof(mrows),
        "metrics_lookup":mlookup,
        "aux":aux,
    }

def deriv_features(ctx,t,full=True):
    out={}
    lin={}
    fr=ctx["funding"].get(t,12*60*60*1000)
    out["funding_rate"]=fr["funding_rate"] if fr else None
    out["funding_age_min"]=(t-fr["available_at_ms"])/60000 if fr else None
    lin["funding_available_at_ms"]=fr["available_at_ms"] if fr else None

    mr=ctx["metrics"].get(t,10*60*1000)
    if mr:
        out["sum_open_interest"]=mr["sum_open_interest"]
        out["metrics_age_min"]=(t-mr["available_at_ms"])/60000
        out["oi_chg_15m"]=pct_change_metric(mr,ctx["metrics_lookup"],15)
        out["oi_chg_60m"]=pct_change_metric(mr,ctx["metrics_lookup"],60)
        if full:
            out["sum_open_interest_value"]=mr["sum_open_interest_value"]
            out["count_toptrader_long_short_ratio"]=mr["count_toptrader_long_short_ratio"]
            out["sum_toptrader_long_short_ratio"]=mr["sum_toptrader_long_short_ratio"]
            out["count_long_short_ratio"]=mr["count_long_short_ratio"]
            out["sum_taker_long_short_vol_ratio"]=mr["sum_taker_long_short_vol_ratio"]
            out["oi_chg_5m"]=pct_change_metric(mr,ctx["metrics_lookup"],5)
        lin["metrics_available_at_ms"]=mr["available_at_ms"]
    else:
        for k in ["sum_open_interest","metrics_age_min","oi_chg_15m","oi_chg_60m"]:
            out[k]=None
        if full:
            for k in ["sum_open_interest_value","count_toptrader_long_short_ratio","sum_toptrader_long_short_ratio","count_long_short_ratio","sum_taker_long_short_vol_ratio","oi_chg_5m"]:
                out[k]=None
        lin["metrics_available_at_ms"]=None

    if full:
        ar={}
        for fam,key in (("markPriceKlines","mark"),("indexPriceKlines","index"),("premiumIndexKlines","premium")):
            r=ctx["aux"][fam].get(t,2*60*1000)
            ar[key]=r
            out[f"{key}_close"]=r["close"] if r else None
            lin[f"{key}_available_at_ms"]=r["available_at_ms"] if r else None
        out["mark_index_basis"]=(ar["mark"]["close"]/ar["index"]["close"]-1) if ar["mark"] and ar["index"] and ar["index"]["close"]!=0 else None
    return out,lin

def fmt(v):
    if v is None:return ""
    if isinstance(v,str):return v
    if isinstance(v,int):return str(v)
    if isinstance(v,float):
        if math.isnan(v) or math.isinf(v):raise ValueError(f"non-finite {v}")
        return format(v,".15g")
    return str(v)

def build(db,out_csv):
    one={"XRPUSDT":load_1m(db,"XRPUSDT"),"BTCUSDT":load_1m(db,"BTCUSDT")}
    vwap={s:session_vwap_map(one[s]) for s in one}
    deriv={s:derivative_context(db,s) for s in ("XRPUSDT","BTCUSDT")}

    base_cols=["feature_set_version","normalization_version","decision_grid","xrp_bar_open_time_ms","decision_time_ms"]
    xrp_price=[f"xrp_{x}" for x in PRICE_FEATURES]
    btc_price=[f"btc_{x}" for x in PRICE_FEATURES]
    xrp_der=["xrp_funding_rate","xrp_funding_age_min","xrp_sum_open_interest","xrp_sum_open_interest_value",
             "xrp_count_toptrader_long_short_ratio","xrp_sum_toptrader_long_short_ratio","xrp_count_long_short_ratio",
             "xrp_sum_taker_long_short_vol_ratio","xrp_metrics_age_min","xrp_oi_chg_5m","xrp_oi_chg_15m","xrp_oi_chg_60m",
             "xrp_mark_close","xrp_index_close","xrp_premium_close","xrp_mark_index_basis"]
    btc_der=["btc_funding_rate","btc_funding_age_min","btc_sum_open_interest","btc_metrics_age_min","btc_oi_chg_15m","btc_oi_chg_60m"]
    lineage=["btc_bar_available_at_ms","xrp_metrics_available_at_ms","btc_metrics_available_at_ms",
             "xrp_funding_available_at_ms","btc_funding_available_at_ms",
             "xrp_mark_available_at_ms","xrp_index_available_at_ms","xrp_premium_available_at_ms"]
    header=base_cols+xrp_price+btc_price+xrp_der+btc_der+lineage

    row_count=0;grid_counts=defaultdict(int);sha=hashlib.sha256()
    with open(out_csv,"w",newline="",encoding="utf-8") as f:
        writer=csv.writer(f,lineterminator="\n")
        writer.writerow(header);sha.update((",".join(header)+"\n").encode())
        for grid,(tf,tfmin) in GRIDS.items():
            xb=load_grid(db,"XRPUSDT",grid);bb=load_grid(db,"BTCUSDT",grid)
            xf=calc_price_features(xb,vwap["XRPUSDT"],tfmin)
            bf=calc_price_features(bb,vwap["BTCUSDT"],tfmin)
            bmap={b["open_time_ms"]:(b,bf[i]) for i,b in enumerate(bb)}
            for i,b in enumerate(xb):
                t=b["available_at_ms"]
                rec={
                    "feature_set_version":FEATURE_SET,"normalization_version":NORM,"decision_grid":grid,
                    "xrp_bar_open_time_ms":b["open_time_ms"],"decision_time_ms":t
                }
                for k,v in xf[i].items():rec["xrp_"+k]=v
                bp=bmap.get(b["open_time_ms"])
                if bp:
                    bbar,bfeat=bp
                    if bbar["available_at_ms"]>t:raise RuntimeError("BTC future bar")
                    for k,v in bfeat.items():rec["btc_"+k]=v
                    rec["btc_bar_available_at_ms"]=bbar["available_at_ms"]
                else:
                    for k in PRICE_FEATURES:rec["btc_"+k]=None
                    rec["btc_bar_available_at_ms"]=None

                xd,xlin=deriv_features(deriv["XRPUSDT"],t,True)
                bd,blin=deriv_features(deriv["BTCUSDT"],t,False)
                for k,v in xd.items():rec["xrp_"+k]=v
                for k,v in bd.items():rec["btc_"+k]=v
                rec["xrp_metrics_available_at_ms"]=xlin.get("metrics_available_at_ms")
                rec["btc_metrics_available_at_ms"]=blin.get("metrics_available_at_ms")
                rec["xrp_funding_available_at_ms"]=xlin.get("funding_available_at_ms")
                rec["btc_funding_available_at_ms"]=blin.get("funding_available_at_ms")
                rec["xrp_mark_available_at_ms"]=xlin.get("mark_available_at_ms")
                rec["xrp_index_available_at_ms"]=xlin.get("index_available_at_ms")
                rec["xrp_premium_available_at_ms"]=xlin.get("premium_available_at_ms")

                vals=[fmt(rec.get(c)) for c in header]
                writer.writerow(vals)
                # Canonical hash independent of platform newline.
                line=",".join('"' + x.replace('"','""') + '"' if ("," in x or '"' in x or "\n" in x) else x for x in vals)+"\n"
                sha.update(line.encode("utf-8"))
                row_count+=1;grid_counts[grid]+=1
    return header,row_count,dict(grid_counts),sha.hexdigest()

def read_qc(path,header):
    idx={c:i for i,c in enumerate(header)}
    counts=defaultdict(int);seen=defaultdict(set);last_t={};violations=[];nonfinite=0;ratio_bad=0
    warm={"xrp_ema200":defaultdict(list),"btc_ema200":defaultdict(list),"xrp_rel_volume20":defaultdict(list),
          "xrp_dist_prev20_high_atr":defaultdict(list)}
    with open(path,newline="",encoding="utf-8") as f:
        rr=csv.reader(f);next(rr)
        for row in rr:
            grid=row[idx["decision_grid"]];t=int(row[idx["decision_time_ms"]]);ot=int(row[idx["xrp_bar_open_time_ms"]])
            counts[grid]+=1
            if ot in seen[grid]:violations.append(f"duplicate bar {grid} {ot}")
            seen[grid].add(ot)
            if grid in last_t and t<=last_t[grid]:violations.append(f"non-increasing decision time {grid}")
            last_t[grid]=t
            for c in ["btc_bar_available_at_ms","xrp_metrics_available_at_ms","btc_metrics_available_at_ms",
                      "xrp_funding_available_at_ms","btc_funding_available_at_ms","xrp_mark_available_at_ms",
                      "xrp_index_available_at_ms","xrp_premium_available_at_ms"]:
                x=row[idx[c]]
                if x and int(x)>t:violations.append(f"future lineage {c} {x}>{t}")
            for c in header:
                if c.startswith(("xrp_","btc_")) and c not in ("xrp_bar_open_time_ms",):
                    x=row[idx[c]]
                    if x:
                        try:
                            v=float(x)
                            if math.isnan(v) or math.isinf(v):nonfinite+=1
                        except ValueError:pass
            x=row[idx["xrp_taker_buy_ratio"]]
            if x and not (-1e-12<=float(x)<=1+1e-12):ratio_bad+=1
            for c in warm:
                warm[c][grid].append(row[idx[c]]!="")
    # Warm-up rules checked per grid position.
    for grid in counts:
        for c,minimum in (("xrp_ema200",199),("btc_ema200",199),("xrp_rel_volume20",20),("xrp_dist_prev20_high_atr",20)):
            arr=warm[c][grid]
            if any(arr[:minimum]):violations.append(f"{c} appears before warmup on {grid}")
    return {"grid_counts":dict(counts),"violations":violations,"nonfinite":nonfinite,"taker_ratio_bad":ratio_bad}

def normalization_versions(db):
    checks={}
    for table in ("contract_1m","contract_resampled","aux_kline_1m","funding","metrics"):
        vals=[r[0] for r in db.execute(f"SELECT DISTINCT normalization_version FROM {table}")]
        checks[table]=vals
        if vals!=[NORM]:
            raise RuntimeError(f"unexpected normalization version {table}: {vals}")
    return checks

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--db",required=True)
    ap.add_argument("--outdir",default="feature-output")
    args=ap.parse_args()
    out=Path(args.outdir);out.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(args.db)
    versions=normalization_versions(db)
    csvpath=out/"XRP_FEATURES_V1.csv"
    header,rows,grid_counts,canon_sha=build(db,csvpath)
    db.close()
    qc=read_qc(csvpath,header)
    passed=(not qc["violations"] and qc["nonfinite"]==0 and qc["taker_ratio_bad"]==0 and qc["grid_counts"]==grid_counts)
    report={
        "feature_set":FEATURE_SET,"normalization":NORM,"rows":rows,"grid_counts":grid_counts,
        "canonical_csv_sha256":canon_sha,"normalization_versions":versions,"qc":qc,"pass":passed
    }
    (out/"XRP_FEATURES_V1_QC.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    md=["# XRP Feature Engineering Smoke V1","",
        f"Result: **{'PASS' if passed else 'FAIL'}**",
        f"Feature set: **{FEATURE_SET}**",
        f"Input normalization: **{NORM}**",
        f"Rows: **{rows:,}**",
        f"Canonical CSV SHA-256: `{canon_sha}`","",
        "## Decision rows","",
        f"- SCALP_1M: {grid_counts.get('SCALP_1M',0):,}",
        f"- PRIMARY_15M: {grid_counts.get('PRIMARY_15M',0):,}","",
        "## QA","",
        f"- future-lineage / duplicates / ordering / warm-up violations: {len(qc['violations'])}",
        f"- non-finite numeric values: {qc['nonfinite']}",
        f"- taker_buy_ratio outside [0,1]: {qc['taker_ratio_bad']}","",
        "## Scope","",
        "- No forward returns, MFE, MAE, ANALYSES, SIGNALS, PERFORMANCE or CURRENT-agent decisions were read.",
        "- This output contains features only. It contains no LONG/SHORT decision, score, entry, stop, TP or strategy outcome.",
        ""]
    if qc["violations"]:
        md+=["## Violations",""]+[f"- {x}" for x in qc["violations"][:50]]
    (out/"XRP_FEATURES_V1_QC.md").write_text("\n".join(md),encoding="utf-8")
    print("\n".join(md),flush=True)
    if not passed:raise SystemExit(2)

if __name__=="__main__":
    main()
