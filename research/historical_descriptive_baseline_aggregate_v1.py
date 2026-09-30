from __future__ import annotations
import argparse, json, math
from pathlib import Path

def corr(s):
    n=s["n"]
    if n<3:return None
    num=n*s["sumxy"]-s["sumx"]*s["sumy"]
    dx=n*s["sumxx"]-s["sumx"]*s["sumx"];dy=n*s["sumyy"]-s["sumy"]*s["sumy"]
    if dx<=0 or dy<=0:return None
    return num/math.sqrt(dx*dy)

def merge_stat(parts):
    rows=sum(x["rows"] for x in parts)
    n=sum(x["non_null"] for x in parts)
    sm=sum(x["sum"] for x in parts);ss=sum(x["sumsq"] for x in parts)
    mean=sm/n if n else None
    sd=math.sqrt(max(0.0,(ss-sm*sm/n)/(n-1))) if n>1 else None
    mins=[x["min"] for x in parts if x["min"] is not None]
    maxs=[x["max"] for x in parts if x["max"] is not None]
    return {"rows":rows,"non_null":n,"coverage":n/rows if rows else None,"mean":mean,"sd":sd,
            "min":min(mins) if mins else None,"max":max(maxs) if maxs else None}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",required=True);ap.add_argument("--outdir",default="baseline-final")
    args=ap.parse_args()
    files=sorted(Path(args.root).rglob("DESCRIPTIVE_BASELINE_PART.json"))
    if not files:raise SystemExit("no partial reports")
    reports=[json.loads(p.read_text()) for p in files]
    reports.sort(key=lambda x:x["target_start"])
    grids=reports[0]["summaries"].keys()
    merged={};stability={}
    for g in grids:
        features=reports[0]["summaries"][g].keys()
        merged[g]={};stability[g]={}
        for c in features:
            ps=[r["summaries"][g][c] for r in reports]
            merged[g][c]=merge_stat(ps)
            stability[g][c]=[
                {"period":r["target_start"][:4],"coverage":r["summaries"][g][c]["coverage"],
                 "mean":r["summaries"][g][c]["mean"],"p50":r["summaries"][g][c]["p50"],
                 "p05":r["summaries"][g][c]["p05"],"p95":r["summaries"][g][c]["p95"]}
                for r in reports
            ]
    pair_stats={};correlations={}
    for g in grids:
        pair_stats[g]={};correlations[g]={}
        keys=reports[0]["core_pair_stats"][g].keys()
        for k in keys:
            s={"n":0,"sumx":0.0,"sumy":0.0,"sumxx":0.0,"sumyy":0.0,"sumxy":0.0}
            for r in reports:
                p=r["core_pair_stats"][g][k]
                for z in s:s[z]+=p[z]
            pair_stats[g][k]=s;correlations[g][k]=corr(s)
    redundancy={}
    for g in grids:
        arr=[{"pair":k,"corr":v,"n":pair_stats[g][k]["n"]} for k,v in correlations[g].items() if v is not None]
        arr.sort(key=lambda x:abs(x["corr"]),reverse=True)
        redundancy[g]=arr[:25]
    rows_by_grid={g:sum(r["rows_by_grid"].get(g,0) for r in reports) for g in grids}
    report={
        "baseline_version":"XRP_DESCRIPTIVE_BASELINE_V1",
        "period_start":reports[0]["target_start"],"period_end":reports[-1]["target_end"],
        "feature_set":reports[0]["feature_set"],"normalization_version":reports[0]["normalization_version"],
        "rows_by_grid":rows_by_grid,"merged_summary":merged,"stability_by_period":stability,
        "core_pair_stats":pair_stats,"core_correlations":correlations,"top_absolute_correlations":redundancy,
        "outcomes_used":False,"parts":[{"start":r["target_start"],"end":r["target_end"]} for r in reports]
    }
    out=Path(args.outdir);out.mkdir(parents=True,exist_ok=True)
    (out/"XRP_DESCRIPTIVE_BASELINE_V1.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    sel=["xrp_ema200","xrp_rsi14","xrp_atr_pct","xrp_rel_volume20","xrp_funding_rate","xrp_sum_open_interest",
         "xrp_oi_chg_15m","xrp_count_toptrader_long_short_ratio","btc_sum_open_interest","btc_oi_chg_15m"]
    lines=["# XRP Historical Descriptive Baseline V1","",
           f"Period: **{report['period_start']} → {report['period_end']}**","",
           f"- SCALP_1M rows: **{rows_by_grid.get('SCALP_1M',0):,}**",
           f"- PRIMARY_15M rows: **{rows_by_grid.get('PRIMARY_15M',0):,}**",
           "- Outcomes used: **NO**",
           "- Strategy rules tested: **NO**","",
           "## Coverage and distribution scale","",
           "| Grid | Feature | Coverage | Mean | SD | Min | Max |","|---|---|---:|---:|---:|---:|---:|"]
    def fmt(x):return "" if x is None else f"{x:.6g}"
    for g in grids:
        for c in sel:
            s=merged[g].get(c)
            if s:lines.append(f"| {g} | {c} | {s['coverage']:.2%} | {fmt(s['mean'])} | {fmt(s['sd'])} | {fmt(s['min'])} | {fmt(s['max'])} |")
    lines+=["","## Coverage stability by year","",
            "| Grid | Feature | 2020 | 2021 | 2022 | 2023 |","|---|---|---:|---:|---:|---:|"]
    for g in grids:
        for c in sel:
            if c not in stability[g]:continue
            ys={x["period"]:x["coverage"] for x in stability[g][c]}
            lines.append(f"| {g} | {c} | {ys.get('2020',0):.2%} | {ys.get('2021',0):.2%} | {ys.get('2022',0):.2%} | {ys.get('2023',0):.2%} |")
    lines+=["","## Strongest contemporaneous correlations among core features",""]
    for g in grids:
        lines.append(f"### {g}")
        for x in redundancy[g][:12]:
            lines.append(f"- {x['pair']}: r={x['corr']:.4f}, n={x['n']:,}")
        lines.append("")
    lines+=["## Interpretation boundary","",
            "This baseline describes data availability, scale, temporal stability and contemporaneous redundancy only.",
            "It does not use future returns, MFE, MAE or trade outcomes and therefore does not establish predictive edge.",
            ""]
    (out/"XRP_DESCRIPTIVE_BASELINE_V1.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":main()
