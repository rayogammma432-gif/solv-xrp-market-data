from __future__ import annotations
import argparse, hashlib, json, math, random, statistics
from collections import defaultdict
from pathlib import Path

REGISTRY_PATH=Path("research/experiments/XRP_HYPOTHESIS_REGISTRY_V2.jsonl")
REGISTRY_SHA256="ab6a355df4699a284ff51ee49ff8e0f944b98e902b87b46384a6957eb9066912"
BOOTSTRAPS=2000
SEED_TAG="XRP_VALIDATION_BOOTSTRAP_V2"

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def merge_dir(dst,src):
    dst["n"]=dst.get("n",0)+src.get("n",0)
    dst["sum"]=dst.get("sum",0.0)+src.get("sum",0.0)
    dst["long_n"]=dst.get("long_n",0)+src.get("long_n",0)
    dst["short_n"]=dst.get("short_n",0)+src.get("short_n",0)
    dst["quarter"]=src["quarter"]
    ds=dst.setdefault("secondary",{})
    for k,v in src.get("secondary",{}).items():
        z=ds.setdefault(k,{"n":0,"sum":0.0})
        z["n"]+=v["n"]; z["sum"]+=v["sum"]

def merge_comp(dst,src):
    dst["a_n"]=dst.get("a_n",0)+src.get("a_n",0)
    dst["a_sum"]=dst.get("a_sum",0.0)+src.get("a_sum",0.0)
    dst["b_n"]=dst.get("b_n",0)+src.get("b_n",0)
    dst["b_sum"]=dst.get("b_sum",0.0)+src.get("b_sum",0.0)
    dst["quarter"]=src["quarter"]

def effect_dir(vals):
    n=sum(x["n"] for x in vals)
    return sum(x["sum"] for x in vals)/n if n else None

def effect_comp(vals):
    an=sum(x["a_n"] for x in vals)
    bn=sum(x["b_n"] for x in vals)
    if not an or not bn:return None
    return sum(x["a_sum"] for x in vals)/an - sum(x["b_sum"] for x in vals)/bn

def seed_for(hid):
    s=f"{REGISTRY_SHA256}|{hid}|{SEED_TAG}".encode()
    return int.from_bytes(hashlib.sha256(s).digest()[:8],"big")

def bootstrap(data,comparative,hid):
    vals=list(data.values()); nd=len(vals)
    if nd==0:return [],None,None,None
    rng=random.Random(seed_for(hid))
    effects=[]; attempts=0
    while len(effects)<BOOTSTRAPS and attempts<BOOTSTRAPS*20:
        attempts+=1
        sample=[vals[rng.randrange(nd)] for _ in range(nd)]
        e=effect_comp(sample) if comparative else effect_dir(sample)
        if e is not None:effects.append(e)
    if len(effects)<BOOTSTRAPS:return effects,None,None,None
    effects.sort()
    def quant(p):
        x=(len(effects)-1)*p; i=int(math.floor(x)); j=min(i+1,len(effects)-1); w=x-i
        return effects[i]*(1-w)+effects[j]*w
    se=statistics.stdev(effects) if len(effects)>1 else 0.0
    return effects,quant(.025),quant(.975),se

def norm_cdf(x): return .5*(1+math.erf(x/math.sqrt(2)))

def holm_adjust(items):
    m=len(items); ordered=sorted(items,key=lambda x:(x[1],x[0]))
    adj={}; running=0.0
    for rank,(hid,p) in enumerate(ordered):
        v=min(1.0,(m-rank)*p)
        running=max(running,v)
        adj[hid]=running
    return adj

def quarter_stability(data,comparative):
    qs=defaultdict(list)
    for _,v in data.items():qs[v["quarter"]].append(v)
    effects=[]; detail={}
    for q,vals in sorted(qs.items()):
        if comparative:
            an=sum(x["a_n"] for x in vals); bn=sum(x["b_n"] for x in vals)
            e=effect_comp(vals)
            informative=an>=50 and bn>=50 and e is not None
            detail[q]={"a_n":an,"b_n":bn,"effect":e,"informative":informative}
        else:
            n=sum(x["n"] for x in vals); e=effect_dir(vals)
            informative=n>=100 and e is not None
            detail[q]={"n":n,"effect":e,"informative":informative}
        if informative: effects.append(e)
    med=statistics.median(effects) if effects else None
    return {
        "informative_quarters":len(effects),
        "median_informative_effect":med,
        "pass":len(effects)>=4 and med is not None and med>0,
        "detail":detail
    }

def sample_stats(data,h,comparative):
    days=len(data)
    if comparative:
        an=sum(x["a_n"] for x in data.values()); bn=sum(x["b_n"] for x in data.values())
        passed=an>=h["minimum_each_group"] and bn>=h["minimum_each_group"] and days>=h["minimum_unique_days"]
        return {"unique_days":days,"a_n":an,"b_n":bn,"pass":passed}
    n=sum(x["n"] for x in data.values()); ln=sum(x["long_n"] for x in data.values()); sn=sum(x["short_n"] for x in data.values())
    passed=n>=h["minimum_total"] and ln>=h["minimum_each_side"] and sn>=h["minimum_each_side"] and days>=h["minimum_unique_days"]
    return {"unique_days":days,"n":n,"long_n":ln,"short_n":sn,"pass":passed}

def secondary_means(data):
    acc={}
    for v in data.values():
        for k,z in v.get("secondary",{}).items():
            a=acc.setdefault(k,{"n":0,"sum":0.0})
            a["n"]+=z["n"]; a["sum"]+=z["sum"]
    return {k:{"n":v["n"],"mean":v["sum"]/v["n"] if v["n"] else None} for k,v in acc.items()}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",required=True)
    ap.add_argument("--outdir",default="validation-final")
    args=ap.parse_args()

    if sha256_file(REGISTRY_PATH)!=REGISTRY_SHA256:
        raise SystemExit("V2 registry SHA mismatch")

    regs=[json.loads(x) for x in REGISTRY_PATH.read_text().splitlines() if x.strip()]
    reg={x["hypothesis_id"]:x for x in regs}
    parts=[json.loads(p.read_text()) for p in sorted(Path(args.root).rglob("XRP_VALIDATION_PART_V2.json"))]
    if len(parts)!=2:raise SystemExit(f"expected 2 validation parts, got {len(parts)}")
    for p in parts:
        if p["registry_sha256"]!=REGISTRY_SHA256:raise SystemExit("partial registry mismatch")
        if p.get("holdout_2026_opened"):raise SystemExit("holdout flag unexpectedly true")

    merged={hid:{} for hid in reg}
    comparative={"XRP-V2-H2-PRIMARY-OI-MODERATOR"}
    for p in parts:
        for hid,days in p["daily"].items():
            for d,v in days.items():
                dst=merged[hid].setdefault(d,{"quarter":v["quarter"]})
                (merge_comp if hid in comparative else merge_dir)(dst,v)

    results={}
    pitems=[]
    for h in regs:
        hid=h["hypothesis_id"]; comp=hid in comparative; data=merged[hid]
        eff=effect_comp(list(data.values())) if comp else effect_dir(list(data.values()))
        sample=sample_stats(data,h,comp)
        qst=quarter_stability(data,comp)
        boots,lo,hi,se=bootstrap(data,comp,hid) if eff is not None else ([],None,None,None)
        if eff is None or se is None:p=1.0
        elif se==0:p=0.0 if eff>0 else 1.0
        else:p=max(0.0,min(1.0,1-norm_cdf(eff/se)))
        pitems.append((hid,p))
        results[hid]={
            "family":h["family"],
            "fixed_parameters":h["fixed_parameters"],
            "primary_effect":eff,
            "sample":sample,
            "bootstrap_replicates":len(boots),
            "ci95_lower":lo,
            "ci95_upper":hi,
            "bootstrap_se":se,
            "p_one_sided":p,
            "economic_floor":h["economic_floor"],
            "validation_effect_floor":h["validation_effect_floor"],
            "discovery_reference_effect":h["discovery_reference_effect"],
            "quarter_stability":qst,
            "secondary":secondary_means(data) if not comp else {}
        }

    adj=holm_adjust(pitems)
    pass_count=0
    for h in regs:
        hid=h["hypothesis_id"]; r=results[hid]
        r["p_holm"]=adj[hid]
        r["effect_sign_pass"]=r["primary_effect"] is not None and r["primary_effect"]>0
        r["ci_pass"]=r["ci95_lower"] is not None and r["ci95_lower"]>0
        r["multiplicity_pass"]=r["p_holm"]<0.05
        r["economic_floor_pass"]=r["primary_effect"] is not None and r["primary_effect"]>=r["economic_floor"]
        r["retention_floor_pass"]=r["primary_effect"] is not None and r["primary_effect"]>=r["validation_effect_floor"]
        r["validation_pass"]=all([
            r["sample"]["pass"],r["effect_sign_pass"],r["ci_pass"],r["multiplicity_pass"],
            r["economic_floor_pass"],r["retention_floor_pass"],r["quarter_stability"]["pass"]
        ])
        r["status"]="VALIDATION_PASS" if r["validation_pass"] else "VALIDATION_FAIL"
        if r["validation_pass"]:pass_count+=1

    report={
        "evaluation_version":"XRP_VALIDATION_EVALUATION_V2",
        "registry_sha256":REGISTRY_SHA256,
        "validation_period":{"start":"2024-01-01T00:00:00Z","end":"2025-12-31T20:00:00Z"},
        "parts":[{"start":p["target_start"],"end":p["target_end"],"features_sha256":p["features_sha256"],"outcomes_sha256":p["outcomes_sha256"]} for p in parts],
        "bootstrap_replicates":BOOTSTRAPS,
        "holdout_2026_opened":False,
        "pass_count":pass_count,
        "results":results
    }
    out=Path(args.outdir);out.mkdir(parents=True,exist_ok=True)
    jp=out/"XRP_VALIDATION_RESULTS_V2.json"
    jp.write_text(json.dumps(report,indent=2,sort_keys=True),encoding="utf-8")
    (out/"XRP_VALIDATION_RESULTS_V2_SHA256.txt").write_text(sha256_file(jp)+"\n",encoding="utf-8")

    lines=["# XRP Validation Results V2","",
           f"Registry SHA-256: `{REGISTRY_SHA256}`",
           f"Bootstrap replicates: **{BOOTSTRAPS}**",
           "2026 holdout opened: **NO**","",
           "| Hypothesis | Status | Effect | CI95 lower | Holm p | Effect floor | Sample |",
           "|---|---|---:|---:|---:|---:|---:|"]
    for h in regs:
        hid=h["hypothesis_id"];r=results[hid];s=r["sample"]
        n=s.get("n",s.get("a_n",0)+s.get("b_n",0))
        eff="" if r["primary_effect"] is None else f"{r['primary_effect']:.8f}"
        lo="" if r["ci95_lower"] is None else f"{r['ci95_lower']:.8f}"
        lines.append(f"| {hid} | {r['status']} | {eff} | {lo} | {r['p_holm']:.6g} | {r['validation_effect_floor']:.8f} | {n:,} |")
    lines+=["","## Gate detail",""]
    for h in regs:
        hid=h["hypothesis_id"];r=results[hid]
        lines += [
            f"### {hid}",
            f"- sample: {'PASS' if r['sample']['pass'] else 'FAIL'} — `{json.dumps(r['sample'],sort_keys=True)}`",
            f"- effect sign: {'PASS' if r['effect_sign_pass'] else 'FAIL'}",
            f"- CI95 lower > 0: {'PASS' if r['ci_pass'] else 'FAIL'}",
            f"- Holm p < 0.05: {'PASS' if r['multiplicity_pass'] else 'FAIL'}",
            f"- economic floor: {'PASS' if r['economic_floor_pass'] else 'FAIL'}",
            f"- validation retention floor: {'PASS' if r['retention_floor_pass'] else 'FAIL'}",
            f"- quarter stability: {'PASS' if r['quarter_stability']['pass'] else 'FAIL'}",
            f"- secondary: `{json.dumps(r['secondary'],sort_keys=True)}`",
            ""
        ]
    lines += ["## Decision","",
              f"Validation passes: **{pass_count}/3**.",
              "The 2026 historical holdout remains sealed in this evaluation.",
              ""]
    (out/"XRP_VALIDATION_RESULTS_V2.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
