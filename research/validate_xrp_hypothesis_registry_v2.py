from __future__ import annotations
import hashlib, json
from pathlib import Path

PATH=Path("research/experiments/XRP_HYPOTHESIS_REGISTRY_V2.jsonl")
VERSION="XRP_HYPOTHESES_V2"
VALIDATION_START="2024-01-01T00:00:00Z"
VALIDATION_END="2026-01-01T00:00:00Z"
EXPECTED_IDS=[
 "XRP-V2-H1-PRIMARY-MOMENTUM-EXHAUSTION",
 "XRP-V2-H2-PRIMARY-OI-MODERATOR",
 "XRP-V2-H3-SCALP-TAKER-FLOW-EXHAUSTION",
]

def main():
    raw=PATH.read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    rows=[json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]
    errors=[]
    ids=[r.get("hypothesis_id") for r in rows]
    if ids!=EXPECTED_IDS: errors.append(f"unexpected IDs/order: {ids}")
    if len(set(ids))!=3: errors.append("hypothesis IDs not unique")
    for r in rows:
        hid=r.get("hypothesis_id")
        if r.get("version")!=VERSION:errors.append(f"{hid}: wrong version")
        if r.get("validation_start")!=VALIDATION_START:errors.append(f"{hid}: wrong validation_start")
        if r.get("validation_end")!=VALIDATION_END:errors.append(f"{hid}: wrong validation_end")
        if not isinstance(r.get("fixed_parameters"),dict) or not r["fixed_parameters"]:
            errors.append(f"{hid}: fixed_parameters missing")
        if "parameter_grid" in r:
            errors.append(f"{hid}: parameter_grid forbidden in V2 validation")
        if r.get("status")!="PREREGISTERED":errors.append(f"{hid}: wrong status")
        if not r.get("features"):errors.append(f"{hid}: features missing")
        if not r.get("direction_rule"):errors.append(f"{hid}: direction_rule missing")
        if not r.get("primary_effect"):errors.append(f"{hid}: primary_effect missing")
        if r.get("primary_horizon_min") is None:errors.append(f"{hid}: horizon missing")
        if r.get("economic_floor") is None:errors.append(f"{hid}: economic_floor missing")
        if r.get("validation_effect_floor") is None:errors.append(f"{hid}: validation_effect_floor missing")
        if r["validation_effect_floor"] < r["economic_floor"]:
            errors.append(f"{hid}: validation floor below economic floor")
        if r.get("retention_fraction") != 0.5:
            errors.append(f"{hid}: retention_fraction changed")
        if r.get("discovery_reference_effect",0) <= 0:
            errors.append(f"{hid}: non-positive discovery reference")
    forbidden=["validation_result","holdout_result","winning_threshold","best_validation","parameter_grid"]
    low=raw.decode("utf-8").lower()
    for x in forbidden:
        if x in low:errors.append(f"forbidden post-seal field: {x}")
    report={"registry":str(PATH),"version":VERSION,"hypothesis_count":len(rows),"ids":ids,"sha256":sha,
            "validation_start":VALIDATION_START,"validation_end":VALIDATION_END,
            "pass":not errors,"errors":errors}
    out=Path("v2-seal-output");out.mkdir(exist_ok=True)
    (out/"XRP_HYPOTHESIS_REGISTRY_V2_SEAL.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    lines=["# XRP Hypothesis Registry V2 — Seal","",
           f"Result: **{'PASS' if report['pass'] else 'FAIL'}**",
           f"Hypotheses: **{len(rows)}**",
           f"SHA-256: `{sha}`","",
           "## IDs",""]+[f"- {x}" for x in ids]
    if errors:lines+=["","## Errors",""]+[f"- {x}" for x in errors]
    (out/"XRP_HYPOTHESIS_REGISTRY_V2_SEAL.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines))
    if errors:raise SystemExit(2)

if __name__=="__main__":main()
