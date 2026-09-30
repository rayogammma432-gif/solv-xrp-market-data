from __future__ import annotations
import argparse, hashlib, itertools, json, math, random, statistics
from collections import defaultdict
from pathlib import Path

REGISTRY_PATH=Path("research/experiments/XRP_HYPOTHESIS_REGISTRY_V1.jsonl")
REGISTRY_SHA256="54c0694bed4539300dd919f93349b8b33ddc7e5d9d5982efce08270ccba93479"
BOOTSTRAPS=2000
SEED_TAG="XRP_DISCOVERY_BOOTSTRAP_V1"

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

def product_configs(h):
    keys=list(h["parameter_grid"].keys())
    vals=[h["parameter_grid"][k] for k in keys]
    out=[]
    for combo in itertools.product(*vals):
        p=dict(zip(keys,combo))
        cid="|".join(f"{k}={format(float(v),'.12g')}" for k,v in p.items())
        out.append((cid,p))
    return out

def merge_dir(dst,src):
    dst["n"]=dst.get("n",0)+src.get("n",0)
    dst["sum"]=dst.get("sum",0.0)+src.get("sum",0.0)
    dst["long_n"]=dst.get("long_n",0)+src.get("long_n",0)
    dst["short_n"]=dst.get("short_n",0)+src.get("short_n",0)
    dst["quarter"]=src["quarter"]
    ds=dst.setdefault("secondary",{})
    for k,v in src.get("secondary",{}).items():
        z=ds.setdefault(k,{"n":0,"sum":0.0})
        z["n"]+=v["n"];z["sum"]+=v["sum"]

def merge_comp(dst,src):
    dst["a_n"]=dst.get("a_n",0)+src.get("a_n",0);dst["a_sum"]=dst.get("a_sum",0.0)+src.get("a_sum",0.0)
    dst["b_n"]=dst.get("b_n",0)+src.get("b_n",0);dst["b_sum"]=dst.get("b_sum",0.0)+src.get("b_sum",0.0)
    dst["quarter"]=src["quarter"]

def effect_dir(vals):
    n=sum(x["n"] for x in vals)
    return (sum(x["sum"] for x in vals)/n) if n else None

def effect_comp(vals):
    an=sum(x["a_n"] for x in vals);bn=sum(x["b_n"] for x in vals)
    if not an or not bn:return None
    return sum(x["a_sum"] for x in vals)/an - sum(x["b_sum"] for x in vals)/bn

def seed_for(hid,cid):
    s=f"{REGISTRY_SHA256}|{hid}|{cid}|{SEED_TAG}".encode()
    return int.from_bytes(hashlib.sha256(s).digest()[:8],"big")

def bootstrap(data,comparative,hid,cid):
    vals=list(data.values());nd=len(vals)
    if nd==0:return [],None,None,None
    rng=random.Random(seed_for(hid,cid))
    effects=[]
    attempts=0
    while len(effects)<BOOTSTRAPS and attempts<BOOTSTRAPS*20:
        attempts+=1
        sample=[vals[rng.randrange(nd)] for _ in range(nd)]
        e=effect_comp(sample) if comparative else effect_dir(sample)
        if e is not None:effects.append(e)
    if len(effects)<BOOTSTRAPS:return effects,None,None,None
    effects.sort()
    def quant(p):
        x=(len(effects)-1)*p;i=int(math.floor(x));j=min(i+1,len(effects)-1);w=x-i
        return effects[i]*(1-w)+effects[j]*w
    se=statistics.stdev(effects) if len(effects)>1 else 0.0
    return effects,quant(.025),quant(.975),se

def norm_cdf(x):return .5*(1+math.erf(x/math.sqrt(2)))

def holm_adjust(items):
    # items: [(cid,p)]
    m=len(items);ordered=sorted(items,key=lambda x:(x[1],x[0]))
    adj={};running=0.0
    for rank,(cid,p) in enumerate(ordered):
        v=min(1.0,(m-rank)*p)
        running=max(running,v)
        adj[cid]=running
    return adj

def quarter_stability(data,comparative,h):
    qs=defaultdict(list)
    for d,v in data.items():qs[v["quarter"]].append(v)
    effects=[];detail={}
    if comparative:
        qmin=max(15,math.ceil(.05*h["minimum_each_group"]))
        for q,vals in sorted(qs.items()):
            an=sum(x["a_n"] for x in vals);bn=sum(x["b_n"] for x in vals)
            e=effect_comp(vals)
            informative=an>=qmin and bn>=qmin and e is not None
            detail[q]={"a_n":an,"b_n":bn,"effect":e,"informative":informative}
            if informative:effects.append(e)
    else:
        qmin=max(25,math.ceil(.05*h.get("minimum_total",0)))
        for q,vals in sorted(qs.items()):
            n=sum(x["n"] for x in vals);e=effect_dir(vals)
            informative=n>=qmin and e is not None
            detail[q]={"n":n,"effect":e,"informative":informative}
            if informative:effects.append(e)
    med=statistics.median(effects) if effects else None
    return {"informative_quarters":len(effects),"median_informative_effect":med,
            "pass":len(effects)>=4 and med is not None and med>0,"detail":detail}

def sample_stats(data,comparative,h):
    days=len(data)
    if comparative:
        an=sum(x["a_n"] for x in data.values());bn=sum(x["b_n"] for x in data.values())
        passed=an>=h["minimum_each_group"] and bn>=h["minimum_each_group"] and days>=h["minimum_unique_days"]
        return {"unique_days":days,"a_n":an,"b_n":bn,"pass":passed}
    n=sum(x["n"] for x in data.values());ln=sum(x["long_n"] for x in data.values());sn=sum(x["short_n"] for x in data.values())
    passed=(n>=h["minimum_total"] and ln>=h["minimum_each_side"] and sn>=h["minimum_each_side"] and days>=h["minimum_unique_days"])
    return {"unique_days":days,"n":n,"long_n":ln,"short_n":sn,"pass":passed}

def secondary_means(data):
    acc={}
    for v in data.values():
        for k,z in v.get("secondary",{}).items():
            a=acc.setdefault(k,{"n":0,"sum":0.0})
            a["n"]+=z["n"];a["sum"]+=z["sum"]
    return {k:{"n":v["n"],"mean":v["sum"]/v["n"] if v["n"] else None} for k,v in acc.items()}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",required=True);ap.add_argument("--outdir",default="discovery-final")
    args=ap.parse_args()
    if sha256_file(REGISTRY_PATH)!=REGISTRY_SHA256:raise SystemExit("registry SHA mismatch")
    regs=[json.loads(x) for x in REGISTRY_PATH.read_text().splitlines() if x.strip()]
    reg={x["hypothesis_id"]:x for x in regs}
    parts=[json.loads(p.read_text()) for p in sorted(Path(args.root).rglob("XRP_DISCOVERY_PART.json"))]
    if len(parts)!=4:raise SystemExit(f"expected 4 discovery parts, got {len(parts)}")
    for p in parts:
        if p["registry_sha256"]!=REGISTRY_SHA256:raise SystemExit("partial registry mismatch")

    merged={}
    for h in regs:
        hid=h["hypothesis_id"]
        if hid=="XRP-H6-FUNDING-EXTREME-REVERSION":continue
        merged[hid]={cid:{} for cid,p in product_configs(h)}
    for part in parts:
        for hid,cfgs in part["daily"].items():
            comparative=hid in ("XRP-H4-PRIMARY-OI-MODERATOR","XRP-H5-PRIMARY-BTC-ALIGNMENT")
            for cid,days in cfgs.items():
                for d,v in days.items():
                    dst=merged[hid][cid].setdefault(d,{"quarter":v["quarter"]})
                    (merge_comp if comparative else merge_dir)(dst,v)

    # H6: deduplicate funding events globally, then create config/day buckets.
    events={}
    for part in parts:
        for e in part["h6_events"]:
            k=str(e["funding_event_ms"])
            if k not in events or e["decision_time_ms"]<events[k]["decision_time_ms"]:events[k]=e
    h6=reg["XRP-H6-FUNDING-EXTREME-REVERSION"]
    merged["XRP-H6-FUNDING-EXTREME-REVERSION"]={cid:{} for cid,p in product_configs(h6)}
    for cid,p in product_configs(h6):
        thr=p["abs_funding_rate_min"]
        for e in events.values():
            fr=e["funding_rate"]
            if abs(fr)<thr:continue
            d=-1 if fr>0 else 1
            primary=d*e["forward_return_240m"]
            b=merged[h6["hypothesis_id"]][cid].setdefault(e["day"],{"quarter":e["quarter"],"n":0,"sum":0.0,"long_n":0,"short_n":0,"secondary":{}})
            b["n"]+=1;b["sum"]+=primary
            if d>0:b["long_n"]+=1
            else:b["short_n"]+=1
            if e["forward_return_60m"] is not None:
                z=b["secondary"].setdefault("signed_60m",{"n":0,"sum":0.0});z["n"]+=1;z["sum"]+=d*e["forward_return_60m"]

    results={}
    for h in regs:
        hid=h["hypothesis_id"];comparative=hid in ("XRP-H4-PRIMARY-OI-MODERATOR","XRP-H5-PRIMARY-BTC-ALIGNMENT")
        cfgres={}
        pitems=[]
        for cid,params in product_configs(h):
            data=merged[hid][cid]
            eff=effect_comp(list(data.values())) if comparative else effect_dir(list(data.values()))
            sample=sample_stats(data,comparative,h)
            qst=quarter_stability(data,comparative,h)
            boots,lo,hi,se=bootstrap(data,comparative,hid,cid) if eff is not None else ([],None,None,None)
            if eff is None:p=1.0
            elif se is None:p=1.0
            elif se==0:p=0.0 if eff>0 else 1.0
            else:p=max(0.0,min(1.0,1-norm_cdf(eff/se)))
            pitems.append((cid,p))
            cfgres[cid]={
                "params":params,"primary_effect":eff,"sample":sample,"bootstrap_replicates":len(boots),
                "ci95_lower":lo,"ci95_upper":hi,"bootstrap_se":se,"p_one_sided":p,
                "quarter_stability":qst,"economic_floor":h["economic_floor"],
                "economic_floor_pass":eff is not None and eff>=h["economic_floor"],
                "secondary":secondary_means(data) if not comparative else {}
            }
        adj=holm_adjust(pitems)
        passes=[]
        for cid,r in cfgres.items():
            r["p_holm"]=adj[cid]
            r["ci_pass"]=r["ci95_lower"] is not None and r["ci95_lower"]>0
            r["multiplicity_pass"]=r["p_holm"]<0.05
            r["effect_sign_pass"]=r["primary_effect"] is not None and r["primary_effect"]>0
            r["discovery_pass"]=all([
                r["sample"]["pass"],r["effect_sign_pass"],r["ci_pass"],r["multiplicity_pass"],
                r["economic_floor_pass"],r["quarter_stability"]["pass"]
            ])
            if r["discovery_pass"]:passes.append((r["primary_effect"],cid))
        passes.sort(key=lambda x:(-x[0],x[1]))
        selected=passes[0][1] if passes else None
        results[hid]={
            "family":h["family"],"config_count":len(cfgres),"configs":cfgres,
            "status":"DISCOVERY_PASS" if selected else "DISCOVERY_FAIL",
            "selected_config":selected,
            "selected_result":cfgres[selected] if selected else None
        }

    report={
        "evaluation_version":"XRP_DISCOVERY_EVALUATION_V1","registry_sha256":REGISTRY_SHA256,
        "parts":[{"start":p["target_start"],"end":p["target_end"],"features_sha256":p["features_sha256"],"outcomes_sha256":p["outcomes_sha256"]} for p in parts],
        "validation_opened":False,"holdout_2026_opened":False,"bootstrap_replicates":BOOTSTRAPS,
        "results":results
    }
    out=Path(args.outdir);out.mkdir(parents=True,exist_ok=True)
    jp=out/"XRP_DISCOVERY_RESULTS_V1.json"
    jp.write_text(json.dumps(report,indent=2,sort_keys=True),encoding="utf-8")
    (out/"XRP_DISCOVERY_RESULTS_V1_SHA256.txt").write_text(sha256_file(jp)+"\n",encoding="utf-8")

    lines=["# XRP Discovery Results V1","",
           f"Registry SHA-256: `{REGISTRY_SHA256}`",
           f"Bootstrap replicates per configuration: **{BOOTSTRAPS}**",
           "Validation opened: **NO**",
           "2026 holdout opened: **NO**","",
           "| Hypothesis | Status | Selected config | Effect | CI95 lower | Holm p | Sample |",
           "|---|---|---|---:|---:|---:|---:|"]
    for h in regs:
        hid=h["hypothesis_id"];rr=results[hid];sel=rr["selected_result"]
        if sel:
            smp=sel["sample"];n=smp.get("n",smp.get("a_n",0)+smp.get("b_n",0))
            lines.append(f"| {hid} | {rr['status']} | `{rr['selected_config']}` | {sel['primary_effect']:.8f} | {sel['ci95_lower']:.8f} | {sel['p_holm']:.6g} | {n:,} |")
        else:
            # report highest observed effect config for diagnostics, explicitly not selected
            ranked=[(r["primary_effect"],cid,r) for cid,r in rr["configs"].items() if r["primary_effect"] is not None]
            ranked.sort(key=lambda x:(-x[0],x[1]))
            if ranked:
                e,c,r=ranked[0];smp=r["sample"];n=smp.get("n",smp.get("a_n",0)+smp.get("b_n",0))
                lo_txt="" if r["ci95_lower"] is None else format(r["ci95_lower"],".8f")
                lines.append(f"| {hid} | DISCOVERY_FAIL | — | {e:.8f}* | {lo_txt} | {r['p_holm']:.6g} | {n:,} |")
            else:lines.append(f"| {hid} | DISCOVERY_FAIL | — | — | — | — | 0 |")
    lines+=["","\* For a failed hypothesis, the displayed effect is the largest observed preregistered configuration for diagnostics only; it is **not selected**.","",
            "## Selected configurations",""]
    for h in regs:
        rr=results[h["hypothesis_id"]]
        if rr["selected_config"]:
            r=rr["selected_result"]
            lines += [f"### {h['hypothesis_id']}",f"- config: `{rr['selected_config']}`",f"- primary effect: {r['primary_effect']:.8f}",
                      f"- CI95: [{r['ci95_lower']:.8f}, {r['ci95_upper']:.8f}]",f"- Holm p: {r['p_holm']:.6g}",
                      f"- quarter stability: {'PASS' if r['quarter_stability']['pass'] else 'FAIL'}",
                      f"- secondary: `{json.dumps(r['secondary'],sort_keys=True)}`",""]
    lines+=["## Boundary","",
            "These are discovery results only. Validation 2024-2025 and the 2026 historical holdout remain sealed.",
            "A DISCOVERY_PASS is not yet a validated strategy.",""]
    (out/"XRP_DISCOVERY_RESULTS_V1.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":main()
