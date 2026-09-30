from __future__ import annotations
import hashlib, json
from pathlib import Path

PATH=Path("research/experiments/XRP_HYPOTHESIS_REGISTRY_V1.jsonl")
VERSION="XRP_HYPOTHESES_V1"
VALID_GRIDS={"PRIMARY_15M","PRIMARY_15M_FIRST_AFTER_FUNDING","SCALP_1M"}
MAX_DISCOVERY_END="2024-01-01T00:00:00Z"

def main():
    raw=PATH.read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    rows=[]
    for i,line in enumerate(raw.decode("utf-8").splitlines(),1):
        if not line.strip():continue
        try:rows.append(json.loads(line))
        except Exception as e:raise SystemExit(f"invalid json line {i}: {e}")
    errors=[]
    ids=[r.get("hypothesis_id") for r in rows]
    if len(rows)!=7:errors.append(f"expected 7 hypotheses, got {len(rows)}")
    if len(set(ids))!=len(ids):errors.append("duplicate hypothesis_id")
    for r in rows:
        hid=r.get("hypothesis_id")
        if r.get("version")!=VERSION:errors.append(f"{hid}: wrong version")
        if r.get("grid") not in VALID_GRIDS:errors.append(f"{hid}: invalid grid {r.get('grid')}")
        if not isinstance(r.get("parameter_grid"),dict) or not r["parameter_grid"]:errors.append(f"{hid}: missing parameter_grid")
        if not r.get("primary_horizon_min"):errors.append(f"{hid}: missing primary horizon")
        if not r.get("primary_effect"):errors.append(f"{hid}: missing primary effect")
        if not r.get("direction_rule"):errors.append(f"{hid}: missing direction rule")
        if r.get("discovery_end")!=MAX_DISCOVERY_END:errors.append(f"{hid}: discovery end not sealed at {MAX_DISCOVERY_END}")
        if r.get("economic_floor") is None:errors.append(f"{hid}: missing economic floor")
        if r.get("status")!="PREREGISTERED":errors.append(f"{hid}: wrong status")
        if r.get("multiplicity")!="Holm within hypothesis family":errors.append(f"{hid}: multiplicity rule changed")
        feats=r.get("features")
        if not isinstance(feats,list) or not feats:errors.append(f"{hid}: missing features")
    forbidden=["forward_return_value","mfe_value","mae_value","best_result","winning_threshold","validation_result"]
    txt=raw.decode("utf-8").lower()
    for x in forbidden:
        if x in txt:errors.append(f"forbidden post-outcome field present: {x}")
    report={
        "registry":str(PATH),
        "version":VERSION,
        "hypothesis_count":len(rows),
        "ids":ids,
        "sha256":sha,
        "pass":not errors,
        "errors":errors
    }
    out=Path("prereg-output");out.mkdir(exist_ok=True)
    (out/"XRP_HYPOTHESIS_REGISTRY_V1_SEAL.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    md=["# XRP Hypothesis Registry V1 — Seal","",
        f"Result: **{'PASS' if report['pass'] else 'FAIL'}**",
        f"Hypotheses: **{len(rows)}**",
        f"SHA-256: `{sha}`","",
        "## IDs",""]+[f"- {x}" for x in ids]
    if errors:md+=["","## Errors",""]+[f"- {e}" for e in errors]
    (out/"XRP_HYPOTHESIS_REGISTRY_V1_SEAL.md").write_text("\n".join(md)+"\n",encoding="utf-8")
    print("\n".join(md))
    if errors:raise SystemExit(2)

if __name__=="__main__":main()
