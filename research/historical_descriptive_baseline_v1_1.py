from __future__ import annotations
import argparse, csv, hashlib, json, math
from array import array
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

START_MS=int(datetime(2020,2,1,tzinfo=timezone.utc).timestamp()*1000)
END_MS=int(datetime(2024,1,1,tzinfo=timezone.utc).timestamp()*1000)
FEATURE_SET="FEATURES_V1_1"
NORM="HIST_NORM_V1"

BASE_COLS={"feature_set_version","normalization_version","decision_grid","xrp_bar_open_time_ms","decision_time_ms"}
LINEAGE_COLS={
"btc_bar_available_at_ms","xrp_metrics_available_at_ms","btc_metrics_available_at_ms",
"xrp_funding_available_at_ms","btc_funding_available_at_ms","xrp_mark_available_at_ms",
"xrp_index_available_at_ms","xrp_premium_available_at_ms"
}
CORE=[
"xrp_ret_1","xrp_atr_pct","xrp_rsi14","xrp_rel_volume20","xrp_taker_imbalance",
"xrp_funding_rate","xrp_sum_open_interest","xrp_oi_chg_15m",
"btc_ret_1","btc_atr_pct","btc_oi_chg_15m"
]
CORR=[
"xrp_ret_1","btc_ret_1","xrp_atr_pct","btc_atr_pct","xrp_taker_imbalance",
"xrp_rel_volume20","xrp_funding_rate","xrp_oi_chg_15m","btc_oi_chg_15m"
]

def fnum(s):
    if s=="":return None
    x=float(s)
    if not math.isfinite(x):raise ValueError(f"non-finite {s}")
    return x

class Stats:
    __slots__=("n","missing","mean","m2","min","max","sample")
    def __init__(self):
        self.n=0;self.missing=0;self.mean=0.0;self.m2=0.0;self.min=None;self.max=None;self.sample=array("d")
    def add(self,x,take_sample):
        if x is None:
            self.missing+=1;return
        self.n+=1
        d=x-self.mean;self.mean+=d/self.n;self.m2+=d*(x-self.mean)
        self.min=x if self.min is None or x<self.min else self.min
        self.max=x if self.max is None or x>self.max else self.max
        if take_sample:self.sample.append(x)
    def out(self,total):
        qs=quantiles(self.sample)
        return {
            "total_rows":total,"non_null":self.n,"missing":total-self.n,
            "coverage_pct":100*self.n/total if total else None,
            "mean":self.mean if self.n else None,
            "std":math.sqrt(self.m2/(self.n-1)) if self.n>1 else None,
            "min":self.min,"max":self.max,
            **qs,"percentile_sample_n":len(self.sample)
        }

def quantiles(a):
    if not a:return {f"p{p:02d}":None for p in (1,5,25,50,75,95,99)}
    b=sorted(a);n=len(b)
    out={}
    for p in (1,5,25,50,75,95,99):
        pos=(n-1)*p/100
        lo=int(math.floor(pos));hi=int(math.ceil(pos))
        v=b[lo] if lo==hi else b[lo]+(b[hi]-b[lo])*(pos-lo)
        out[f"p{p:02d}"]=v
    return out

class Corr:
    __slots__=("n","sx","sy","sxx","syy","sxy")
    def __init__(self):self.n=0;self.sx=self.sy=self.sxx=self.syy=self.sxy=0.0
    def add(self,x,y):
        if x is None or y is None:return
        self.n+=1;self.sx+=x;self.sy+=y;self.sxx+=x*x;self.syy+=y*y;self.sxy+=x*y
    def out(self):
        if self.n<2:return {"n":self.n,"r":None}
        num=self.n*self.sxy-self.sx*self.sy
        dx=self.n*self.sxx-self.sx*self.sx;dy=self.n*self.syy-self.sy*self.sy
        if dx<=0 or dy<=0:return {"n":self.n,"r":None}
        return {"n":self.n,"r":num/math.sqrt(dx*dy)}

def iso_year(ms):
    return datetime.fromtimestamp(ms/1000,tz=timezone.utc).year

def expected_rows(grid):
    mins=int((datetime(2024,1,1,tzinfo=timezone.utc)-datetime(2020,2,1,tzinfo=timezone.utc)).total_seconds()/60)
    return mins if grid=="SCALP_1M" else mins//15

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--features",required=True)
    ap.add_argument("--outdir",default="baseline-output")
    args=ap.parse_args()
    outdir=Path(args.outdir);outdir.mkdir(parents=True,exist_ok=True)

    with open(args.features,newline="",encoding="utf-8") as f:
        reader=csv.reader(f);header=next(reader)
        idx={c:i for i,c in enumerate(header)}
        features=[c for c in header if c not in BASE_COLS and c not in LINEAGE_COLS]
        for c in CORE+CORR:
            if c not in idx:raise RuntimeError(f"missing preregistered feature {c}")

        stats={g:{c:Stats() for c in features} for g in ("SCALP_1M","PRIMARY_15M")}
        annual={g:{y:{c:Stats() for c in CORE} for y in (2020,2021,2022,2023)} for g in ("SCALP_1M","PRIMARY_15M")}
        pairs=[(a,b) for i,a in enumerate(CORR) for b in CORR[i+1:]]
        corr={g:{(a,b):Corr() for a,b in pairs} for g in ("SCALP_1M","PRIMARY_15M")}
        rows=defaultdict(int);last_open={};dups=0;bad_versions=0
        seen=set()

        for row in reader:
            ot=int(row[idx["xrp_bar_open_time_ms"]])
            if ot<START_MS or ot>=END_MS:continue
            grid=row[idx["decision_grid"]]
            if grid not in stats:continue
            if row[idx["feature_set_version"]]!=FEATURE_SET or row[idx["normalization_version"]]!=NORM:
                bad_versions+=1
            key=(grid,ot)
            if key in seen:dups+=1
            seen.add(key)
            if grid in last_open and ot<=last_open[grid]:
                raise RuntimeError(f"non increasing open_time {grid}")
            last_open[grid]=ot
            pos=rows[grid]
            rows[grid]+=1
            take_sample=(grid=="PRIMARY_15M" or pos%10==0)
            vals={}
            for c in features:
                x=fnum(row[idx[c]])
                vals[c]=x
                stats[grid][c].add(x,take_sample)
            year=iso_year(ot)
            for c in CORE:
                annual[grid][year][c].add(vals[c],False)
            for a,b in pairs:
                corr[grid][(a,b)].add(vals[a],vals[b])

    report={
        "baseline_version":"DESCRIPTIVE_BASELINE_V1_1",
        "feature_set":FEATURE_SET,"normalization":NORM,
        "period":{"start":"2020-02-01T00:00:00Z","end_exclusive":"2024-01-01T00:00:00Z"},
        "rows":dict(rows),"expected_rows":{g:expected_rows(g) for g in rows},
        "duplicate_rows":dups,"bad_version_rows":bad_versions,
        "features":{},"annual":{},"correlations":{}
    }
    for g in ("SCALP_1M","PRIMARY_15M"):
        total=rows[g]
        report["features"][g]={c:stats[g][c].out(total) for c in features}
        report["annual"][g]={str(y):{c:annual[g][y][c].out(sum(1 for _ in [])) for c in CORE} for y in ()}
        # annual total must come from actual per-year count; derive from any stat's n+missing.
        annual_out={}
        for y in (2020,2021,2022,2023):
            # each Stats receives add on every row, so n + missing is yearly rows.
            ref=annual[g][y][CORE[0]]
            total_y=ref.n+ref.missing
            annual_out[str(y)]={"rows":total_y,"features":{c:annual[g][y][c].out(total_y) for c in CORE}}
        report["annual"][g]=annual_out
        matrix={a:{b:({"n":total,"r":1.0} if a==b else None) for b in CORR} for a in CORR}
        for a,b in pairs:
            o=corr[g][(a,b)].out();matrix[a][b]=o;matrix[b][a]=o
        report["correlations"][g]=matrix

    report["pass"]=(dups==0 and bad_versions==0 and all(rows[g]==expected_rows(g) for g in ("SCALP_1M","PRIMARY_15M")))
    json_text=json.dumps(report,indent=2,sort_keys=True,allow_nan=False)
    (outdir/"XRP_DESCRIPTIVE_BASELINE_V1_1_1.json").write_text(json_text+"\n",encoding="utf-8")
    digest=hashlib.sha256((json_text+"\n").encode()).hexdigest()

    md=["# XRP Historical Descriptive Baseline V1.1","",
        f"Result: **{'PASS' if report['pass'] else 'FAIL'}**","",
        "Period: 2020-02-01 → 2023-12-31",
        f"Summary SHA-256: `{digest}`","",
        "## Rows","",
        "| Grid | Actual | Expected |","|---|---:|---:|"]
    for g in ("SCALP_1M","PRIMARY_15M"):
        md.append(f"| {g} | {rows[g]:,} | {expected_rows(g):,} |")
    md+=["","## Core coverage by grid","",
         "| Feature | SCALP coverage | PRIMARY coverage |","|---|---:|---:|"]
    for c in CORE:
        a=report["features"]["SCALP_1M"][c]["coverage_pct"];b=report["features"]["PRIMARY_15M"][c]["coverage_pct"]
        md.append(f"| {c} | {a:.3f}% | {b:.3f}% |")
    md+=["","## Annual core coverage",""]
    for g in ("SCALP_1M","PRIMARY_15M"):
        md+= [f"### {g}","", "| Year | Rows | XRP OI coverage | XRP OI Δ15m coverage | BTC OI Δ15m coverage |",
              "|---:|---:|---:|---:|---:|"]
        for y in ("2020","2021","2022","2023"):
            a=report["annual"][g][y]
            def cp(c):return a["features"][c]["coverage_pct"]
            md.append(f"| {y} | {a['rows']:,} | {cp('xrp_sum_open_interest'):.3f}% | {cp('xrp_oi_chg_15m'):.3f}% | {cp('btc_oi_chg_15m'):.3f}% |")
    md+=["","## Contemporaneous correlations","",
         "These are descriptive same-time correlations, not predictive tests.",""]
    for g in ("SCALP_1M","PRIMARY_15M"):
        md+= [f"### {g}","",
              "| Pair | n | Pearson r |","|---|---:|---:|"]
        for a,b in [("xrp_ret_1","btc_ret_1"),("xrp_atr_pct","btc_atr_pct"),("xrp_taker_imbalance","xrp_ret_1"),
                    ("xrp_oi_chg_15m","btc_oi_chg_15m"),("xrp_rel_volume20","xrp_taker_imbalance")]:
            o=report["correlations"][g][a][b]
            rv="NA" if o["r"] is None else f"{o['r']:.6f}"
            md.append(f"| {a} ↔ {b} | {o['n']:,} | {rv} |")
    md+=["","## Guardrails","",
         f"- duplicate decision rows: {dups}",
         f"- bad feature/normalization version rows: {bad_versions}",
         "- No forward returns, MFE, MAE, trade outcomes or CURRENT-agent decisions were read.",
         "- Percentiles for SCALP use deterministic systematic 1-in-10 sampling; PRIMARY uses all non-null rows.",
         "- Metrics missing before their official historical coverage remains NA.",
         ""]
    (outdir/"XRP_DESCRIPTIVE_BASELINE_V1_1_1.md").write_text("\n".join(md),encoding="utf-8")
    (outdir/"XRP_DESCRIPTIVE_BASELINE_V1_1_1_SHA256.txt").write_text(digest+"\n",encoding="utf-8")
    print("\n".join(md),flush=True)
    if not report["pass"]:raise SystemExit(2)

if __name__=="__main__":main()
