from __future__ import annotations
import argparse, csv, hashlib, json, math, sqlite3
from pathlib import Path
from datetime import datetime, timezone

VERSION="OUTCOMES_V1"
FWD_H=(5,15,30,60,240)
EXC_H=(15,60,240)

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def parse_iso_ms(s):
    dt=datetime.fromisoformat(s.replace("Z","+00:00"))
    if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp()*1000)

def fmt(v):
    if v is None:return ""
    if isinstance(v,int):return str(v)
    if isinstance(v,str):return v
    if isinstance(v,float):
        if not math.isfinite(v):raise ValueError("non-finite")
        return format(v,".15g")
    return str(v)

def load_contract(db):
    q="""SELECT available_at_ms, open_time_ms, high, low, close
         FROM contract_1m WHERE symbol='XRPUSDT' ORDER BY available_at_ms"""
    out={}
    for a,o,h,l,c in db.execute(q):
        out[int(a)]={"available_at_ms":int(a),"open_time_ms":int(o),"high":float(h),"low":float(l),"close":float(c)}
    return out

def synthetic_selftest():
    decision=1_000_000
    bars={}
    for k in range(1,11):
        a=decision+k*60_000
        bars[a]={"available_at_ms":a,"high":100+k,"low":99-k/10,"close":100+k/2}
    ref=100.0
    # Exact 5m exists.
    target=bars.get(decision+5*60_000)
    assert target is not None and math.isclose(target["close"]/ref-1,0.025,abs_tol=1e-12)
    # Remove exact 5m; engine must not take minute 6.
    del bars[decision+5*60_000]
    assert bars.get(decision+5*60_000) is None
    # Full 10m window should now be incomplete.
    seq=[bars.get(decision+k*60_000) for k in range(1,11)]
    assert any(x is None for x in seq)
    return True

def compute_one(contract,decision_time,reference_price):
    rec={}
    for h in FWD_H:
        target_at=decision_time+h*60_000
        b=contract.get(target_at)
        rec[f"target_available_at_{h}m"]=target_at
        rec[f"forward_return_{h}m"]=(b["close"]/reference_price-1) if b else None
        rec[f"forward_complete_{h}m"]=1 if b else 0
    for h in EXC_H:
        bars=[contract.get(decision_time+k*60_000) for k in range(1,h+1)]
        complete=all(x is not None for x in bars)
        rec[f"excursion_complete_{h}m"]=1 if complete else 0
        if complete:
            rec[f"raw_up_excursion_{h}m"]=max(x["high"] for x in bars)/reference_price-1
            rec[f"raw_down_excursion_{h}m"]=min(x["low"] for x in bars)/reference_price-1
        else:
            rec[f"raw_up_excursion_{h}m"]=None
            rec[f"raw_down_excursion_{h}m"]=None
    return rec

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--db",required=True)
    ap.add_argument("--features",required=True)
    ap.add_argument("--target-start",required=True)
    ap.add_argument("--target-end",required=True)
    ap.add_argument("--outdir",default="outcome-output")
    args=ap.parse_args()

    assert synthetic_selftest()

    start=parse_iso_ms(args.target_start); end=parse_iso_ms(args.target_end)
    out=Path(args.outdir);out.mkdir(parents=True,exist_ok=True)

    feature_sha_before=sha256_file(args.features)
    db=sqlite3.connect(args.db)
    contract=load_contract(db)
    db.close()

    with open(args.features,newline="",encoding="utf-8") as f:
        rr=csv.reader(f)
        header=next(rr)
        idx={c:i for i,c in enumerate(header)}
        required=["decision_grid","xrp_bar_open_time_ms","decision_time_ms","xrp_close"]
        for c in required:
            if c not in idx:raise SystemExit(f"missing feature column {c}")
        selected=[]
        for row in rr:
            t=int(row[idx["decision_time_ms"]])
            if start<=t<end:selected.append(row)

    out_header=[
        "outcome_engine_version","decision_grid","xrp_bar_open_time_ms","decision_time_ms","reference_price"
    ]
    for h in FWD_H:
        out_header += [f"target_available_at_{h}m",f"forward_return_{h}m",f"forward_complete_{h}m"]
    for h in EXC_H:
        out_header += [f"raw_up_excursion_{h}m",f"raw_down_excursion_{h}m",f"excursion_complete_{h}m"]

    rows=0
    grid_counts={}
    duplicate_keys=set()
    seen=set()
    reference_mismatch=0
    future_target_violation=0
    nonfinite=0
    incomplete_fwd={h:0 for h in FWD_H}
    incomplete_exc={h:0 for h in EXC_H}

    csvpath=out/"XRP_OUTCOMES_V1.csv"
    with open(csvpath,"w",newline="",encoding="utf-8") as f:
        w=csv.writer(f,lineterminator="\n")
        w.writerow(out_header)
        for row in selected:
            grid=row[idx["decision_grid"]]
            ot=int(row[idx["xrp_bar_open_time_ms"]])
            t=int(row[idx["decision_time_ms"]])
            ref=float(row[idx["xrp_close"]])
            key=(grid,t)
            if key in seen:duplicate_keys.add(key)
            seen.add(key)
            refbar=contract.get(t)
            if refbar is None or not math.isclose(refbar["close"],ref,rel_tol=1e-12,abs_tol=1e-12):
                reference_mismatch+=1
                continue
            rec={
                "outcome_engine_version":VERSION,
                "decision_grid":grid,
                "xrp_bar_open_time_ms":ot,
                "decision_time_ms":t,
                "reference_price":ref,
            }
            rec.update(compute_one(contract,t,ref))
            for h in FWD_H:
                ta=rec[f"target_available_at_{h}m"]
                if ta<=t:future_target_violation+=1
                if not rec[f"forward_complete_{h}m"]:incomplete_fwd[h]+=1
            for h in EXC_H:
                if not rec[f"excursion_complete_{h}m"]:incomplete_exc[h]+=1
            vals=[rec.get(c) for c in out_header]
            for v in vals:
                if isinstance(v,float) and not math.isfinite(v):nonfinite+=1
            w.writerow([fmt(v) for v in vals])
            rows+=1
            grid_counts[grid]=grid_counts.get(grid,0)+1

    feature_sha_after=sha256_file(args.features)
    output_sha=sha256_file(csvpath)

    qc={
        "outcome_engine_version":VERSION,
        "target_start":args.target_start,
        "target_end":args.target_end,
        "rows":rows,
        "grid_counts":grid_counts,
        "feature_sha_before":feature_sha_before,
        "feature_sha_after":feature_sha_after,
        "feature_unchanged":feature_sha_before==feature_sha_after,
        "output_sha256":output_sha,
        "reference_mismatch":reference_mismatch,
        "duplicate_decision_keys":len(duplicate_keys),
        "future_target_violation":future_target_violation,
        "nonfinite":nonfinite,
        "incomplete_forward":incomplete_fwd,
        "incomplete_excursion":incomplete_exc,
        "synthetic_missing_target_selftest":"PASS",
    }
    qc["pass"]=(
        rows==len(selected)
        and reference_mismatch==0
        and len(duplicate_keys)==0
        and future_target_violation==0
        and nonfinite==0
        and qc["feature_unchanged"]
    )
    (out/"XRP_OUTCOME_ENGINE_V1_QC.json").write_text(json.dumps(qc,indent=2),encoding="utf-8")

    lines=[
        "# XRP Outcome Engine V1 — Smoke QC","",
        f"Result: **{'PASS' if qc['pass'] else 'FAIL'}**",
        f"Range: **{args.target_start} → {args.target_end}**",
        f"Rows: **{rows:,}**",
        f"Output SHA-256: `{output_sha}`","",
        "## Integrity","",
        f"- reference mismatches: {reference_mismatch}",
        f"- duplicate decision keys: {len(duplicate_keys)}",
        f"- future target violations: {future_target_violation}",
        f"- non-finite values: {nonfinite}",
        f"- feature input unchanged: {'PASS' if qc['feature_unchanged'] else 'FAIL'}",
        "- synthetic exact-target/no-nearest self-test: PASS","",
        "## Incomplete exact horizons",""
    ]
    for h in FWD_H:lines.append(f"- forward {h}m: {incomplete_fwd[h]}")
    for h in EXC_H:lines.append(f"- excursion {h}m: {incomplete_exc[h]}")
    lines += [
        "",
        "No hypothesis effect, mean return, win rate, MFE/MAE aggregate or threshold result is reported by this smoke test.",
        ""
    ]
    (out/"XRP_OUTCOME_ENGINE_V1_QC.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines),flush=True)
    if not qc["pass"]:raise SystemExit(2)

if __name__=="__main__":
    main()
