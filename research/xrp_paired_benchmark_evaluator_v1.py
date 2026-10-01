#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, json, math, random, statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ALLOWED_STATES={"TRADE_LONG","TRADE_SHORT","NO_TRADE","DATA_INSUFFICIENT"}
HORIZON_BY_TYPE={"SCALP_TRIGGER":15,"PRIMARY_TRIGGER":60,"PRIMARY":60}
BOOTSTRAPS=5000

def read_csv(path):
    with open(path,newline="",encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def fnum(v):
    if v in ("",None): return None
    if isinstance(v,(int,float)): return float(v)
    s=str(v).strip()
    if "," in s and "." not in s: s=s.replace(",",".")
    return float(s)

def parse_utc(s):
    return datetime.fromisoformat(str(s).replace("Z","+00:00")).astimezone(timezone.utc)

def one_by(rows,key):
    out={}
    dup=[]
    for r in rows:
        k=str(r.get(key,""))
        if not k: continue
        if k in out: dup.append(k)
        out[k]=r
    if dup: raise ValueError(f"duplicate {key}: {sorted(set(dup))[:10]}")
    return out

def trade_sign(state):
    if state=="TRADE_LONG": return 1
    if state=="TRADE_SHORT": return -1
    return 0

def primary_raw_pct(outcome, alert_type):
    h=HORIZON_BY_TYPE.get(alert_type)
    if h is None: raise ValueError(f"unsupported Alert Type {alert_type}")
    return fnum(outcome.get(f"Raw Fwd {h}m %"))

def arm_return_pct(decision, raw_pct, cost_bps):
    state=str(decision.get("Benchmark State","")).upper()
    if state not in ALLOWED_STATES:
        raise ValueError(f"invalid benchmark state {state}")
    sign=trade_sign(state)
    gross=sign*raw_pct if sign else 0.0
    if cost_bps is None:
        return gross,gross
    cost_pct=(float(cost_bps)/100.0) if sign else 0.0
    return gross,gross-cost_pct

def max_drawdown_pct(returns_pct):
    equity=1.0; peak=1.0; maxdd=0.0
    for r in returns_pct:
        equity*=1.0+float(r)/100.0
        peak=max(peak,equity)
        if peak>0:maxdd=max(maxdd,(peak-equity)/peak*100.0)
    return maxdd

def quantile(xs,p):
    xs=sorted(xs)
    if not xs:return None
    x=(len(xs)-1)*p;i=int(math.floor(x));j=min(i+1,len(xs)-1);w=x-i
    return xs[i]*(1-w)+xs[j]*w

def bootstrap_day_diff(records,reps=BOOTSTRAPS):
    byday=defaultdict(list)
    for r in records: byday[r["day"]].append(r["diff"])
    days=sorted(byday)
    if not days:return [],None,None
    seed_src="|".join(r["pair_id"] for r in records)+"|XRP_PAIRED_V1"
    seed=int.from_bytes(hashlib.sha256(seed_src.encode()).digest()[:8],"big")
    rng=random.Random(seed)
    vals=[]
    for _ in range(reps):
        sampled=[days[rng.randrange(len(days))] for _ in days]
        total=0.0;n=0
        for d in sampled:
            arr=byday[d]
            total+=sum(arr);n+=len(arr)
        vals.append(total/n if n else 0.0)
    return vals,quantile(vals,.025),quantile(vals,.975)

def arm_summary(records,prefix,use_net):
    vals=[r[f"{prefix}_{'net' if use_net else 'gross'}"] for r in records]
    traded=[r for r in records if r[f"{prefix}_trade"]]
    trade_vals=[r[f"{prefix}_{'net' if use_net else 'gross'}"] for r in traded]
    return {
        "captures":len(records),
        "trades":len(traded),
        "trade_rate":len(traded)/len(records) if records else None,
        "data_insufficient":sum(1 for r in records if r[f"{prefix}_state"]=="DATA_INSUFFICIENT"),
        "mean_return_per_capture_pct":statistics.mean(vals) if vals else None,
        "total_return_sum_pct":sum(vals),
        "mean_return_per_trade_pct":statistics.mean(trade_vals) if trade_vals else None,
        "win_rate_trades":sum(1 for x in trade_vals if x>0)/len(trade_vals) if trade_vals else None,
        "max_drawdown_pct":max_drawdown_pct(vals),
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--captures",required=True)
    ap.add_argument("--current",required=True)
    ap.add_argument("--challenger",required=True)
    ap.add_argument("--outcomes",required=True)
    ap.add_argument("--round-trip-cost-bps",type=float)
    ap.add_argument("--include-prelaunch",action="store_true")
    ap.add_argument("--outdir",default="paired-eval")
    args=ap.parse_args()

    caps=read_csv(args.captures);cur=read_csv(args.current);cha=read_csv(args.challenger);outs=read_csv(args.outcomes)
    cap_by=one_by(caps,"Pair ID");cur_by=one_by(cur,"Pair ID");cha_by=one_by(cha,"Pair ID");out_by=one_by(outs,"Pair ID")

    formal_ids=[pid for pid,r in cap_by.items() if str(r.get("Eligibility","")).upper()=="FORMAL_PROSPECTIVE"]
    supportive_ids=[pid for pid,r in cap_by.items() if str(r.get("Eligibility","")).upper()=="PRELAUNCH_POOL"]
    selected_ids=list(formal_ids)
    mode="FORMAL_PROSPECTIVE"
    if args.include_prelaunch:
        selected_ids=sorted(set(selected_ids+supportive_ids))
        mode="MIXED_SUPPORTIVE"
    else:
        selected_ids=sorted(selected_ids)

    missing_current=[x for x in selected_ids if x not in cur_by]
    missing_challenger=[x for x in selected_ids if x not in cha_by]
    missing_outcome=[x for x in selected_ids if x not in out_by or str(out_by[x].get("Outcome Complete","")).upper()!="COMPLETE"]

    records=[]; provenance_errors=[]
    for pid in selected_ids:
        if pid in missing_current or pid in missing_challenger or pid in missing_outcome: continue
        cap=cap_by[pid];c=cur_by[pid];h=cha_by[pid];o=out_by[pid]
        if str(c.get("Status","")).upper()!="COMPLETE": provenance_errors.append(f"{pid}: CURRENT status")
        if str(h.get("Status","")).upper()!="COMPLETE": provenance_errors.append(f"{pid}: CHALLENGER status")
        capsha=str(cap.get("Full Snapshot SHA256",""))
        if not capsha: provenance_errors.append(f"{pid}: full snapshot sha missing")
        if str(cap.get("Eligibility","")).upper()=="FORMAL_PROSPECTIVE":
            if str(cap.get("Snapshot Completeness","")).upper()!="FULL":
                provenance_errors.append(f"{pid}: formal snapshot not FULL")
            if str(cap.get("Snapshot Version",""))!="XRP_PAIRED_SNAPSHOT_V1":
                provenance_errors.append(f"{pid}: formal snapshot version mismatch")
        if capsha and str(c.get("Snapshot SHA256",""))!=capsha: provenance_errors.append(f"{pid}: CURRENT capture sha mismatch")
        if capsha and str(h.get("Snapshot SHA256",""))!=capsha: provenance_errors.append(f"{pid}: CHALLENGER capture sha mismatch")
        for arm,row in (("CURRENT",c),("CHALLENGER",h)):
            sha=str(row.get("Rule Commit SHA",""))
            if len(sha)!=40: provenance_errors.append(f"{pid}: {arm} rule sha invalid")
            if not str(row.get("Output SHA256","")): provenance_errors.append(f"{pid}: {arm} output sha missing")
            if not str(row.get("Model ID","")): provenance_errors.append(f"{pid}: {arm} model id missing")
            if not str(row.get("Run Mode","")): provenance_errors.append(f"{pid}: {arm} run mode missing")
        if str(c.get("Model ID","")) != str(h.get("Model ID","")):
            provenance_errors.append(f"{pid}: model id mismatch")
        if str(c.get("Run Mode","")) != str(h.get("Run Mode","")):
            provenance_errors.append(f"{pid}: run mode mismatch")
        at=str(cap.get("Alert Type","")).upper()
        raw=primary_raw_pct(o,at)
        if raw is None: continue
        cg,cn=arm_return_pct(c,raw,args.round_trip_cost_bps)
        hg,hn=arm_return_pct(h,raw,args.round_trip_cost_bps)
        cs=str(c.get("Benchmark State","")).upper();hs=str(h.get("Benchmark State","")).upper()
        records.append({
            "pair_id":pid,"alert_utc":str(cap.get("Alert UTC","")),"day":parse_utc(cap["Alert UTC"]).date().isoformat(),
            "alert_type":at,"current_state":cs,"challenger_state":hs,
            "current_trade":trade_sign(cs)!=0,"challenger_trade":trade_sign(hs)!=0,
            "current_gross":cg,"challenger_gross":hg,"current_net":cn,"challenger_net":hn,
            "gross_diff":hg-cg,"net_diff":hn-cn
        })

    use_net=args.round_trip_cost_bps is not None
    for r in records:r["diff"]=r["net_diff"] if use_net else r["gross_diff"]
    boots,lo,hi=bootstrap_day_diff(records)

    if records:
        start=min(parse_utc(r["alert_utc"]) for r in records)
        end=max(parse_utc(r["alert_utc"]) for r in records)
        calendar_days=(end.date()-start.date()).days+1
        unique_days=len({r["day"] for r in records})
    else:
        start=end=None;calendar_days=unique_days=0

    sample_gate=(len(records)>=1000 and calendar_days>=60 and unique_days>=40)
    completeness_gate=not missing_current and not missing_challenger and not missing_outcome
    provenance_gate=not provenance_errors
    formal_only=(mode=="FORMAL_PROSPECTIVE" and bool(formal_ids))

    current_summary=arm_summary(records,"current",use_net)
    challenger_summary=arm_summary(records,"challenger",use_net)

    categories=defaultdict(int)
    for r in records:
        cs=r["current_state"];hs=r["challenger_state"]
        if cs==hs: categories["same_state"]+=1
        if trade_sign(cs)!=0 and trade_sign(hs)!=0:
            categories["both_trade_same_direction" if trade_sign(cs)==trade_sign(hs) else "both_trade_opposite_direction"]+=1
        elif trade_sign(cs)!=0: categories["current_trade_challenger_abstain"]+=1
        elif trade_sign(hs)!=0: categories["challenger_trade_current_abstain"]+=1
        else: categories["both_abstain"]+=1

    verdict="INCOMPLETE"
    if records and not use_net:
        verdict="NO_NET_VERDICT"
    if use_net and formal_only and sample_gate and completeness_gate and provenance_gate and lo is not None:
        if lo>0 and challenger_summary["total_return_sum_pct"]>0: verdict="CHALLENGER_SUPERIOR"
        elif hi<0 and current_summary["total_return_sum_pct"]>0: verdict="CURRENT_SUPERIOR"
        else: verdict="INCONCLUSIVE"
    elif use_net and records:
        verdict="PRECHECK_NOT_MET"

    report={
        "version":"XRP_PAIRED_EVALUATOR_V1",
        "mode":mode,
        "round_trip_cost_bps":args.round_trip_cost_bps,
        "selected_capture_count":len(selected_ids),
        "complete_pair_count":len(records),
        "formal_capture_count":len(formal_ids),
        "supportive_capture_count":len(supportive_ids),
        "missing_current_count":len(missing_current),
        "missing_challenger_count":len(missing_challenger),
        "missing_outcome_count":len(missing_outcome),
        "provenance_error_count":len(provenance_errors),
        "calendar_days":calendar_days,"unique_utc_days":unique_days,
        "sample_gate":sample_gate,"completeness_gate":completeness_gate,"provenance_gate":provenance_gate,
        "primary_mean_paired_diff_pct":statistics.mean([r["diff"] for r in records]) if records else None,
        "paired_ci95_lower_pct":lo,"paired_ci95_upper_pct":hi,"bootstrap_replicates":len(boots),
        "current":current_summary,"challenger":challenger_summary,
        "model_ids":sorted({str(cur_by[r["pair_id"]].get("Model ID","")) for r in records}),
        "run_modes":sorted({str(cur_by[r["pair_id"]].get("Run Mode","")) for r in records}),
        "disagreement_categories":dict(categories),
        "verdict":verdict,
        "provenance_errors":provenance_errors[:100]
    }
    out=Path(args.outdir);out.mkdir(parents=True,exist_ok=True)
    (out/"XRP_PAIRED_RESULTS_V1.json").write_text(json.dumps(report,indent=2,sort_keys=True),encoding="utf-8")
    lines=["# XRP Paired Benchmark Results V1","",
           f"Mode: **{mode}**",f"Complete pairs: **{len(records)}**",
           f"Cost model: **{'FROZEN '+str(args.round_trip_cost_bps)+' bps' if use_net else 'NOT PROVIDED'}**",
           f"Mean paired difference: **{report['primary_mean_paired_diff_pct']} % per capture**",
           f"CI95: **[{lo}, {hi}]**",f"Verdict: **{verdict}**","",
           "A formal economic winner requires prospective formal captures, the minimum sample gate, complete provenance and a frozen cost model."]
    (out/"XRP_PAIRED_RESULTS_V1.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":
    main()
