from __future__ import annotations
import hashlib, json
from pathlib import Path
from datetime import datetime, timezone

REG=Path("research/experiments/XRP_FORWARD_REGISTRY_V3.jsonl")
HOLDOUT=Path("research/XRP_2026_HOLDOUT_LOCK_V1.md")
VERSION="XRP_FORWARD_V3"
MIN_START="2026-10-01T00:00:00Z"

def parse(s):
    return datetime.fromisoformat(s.replace("Z","+00:00")).astimezone(timezone.utc)

def main():
    raw=REG.read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    rows=[json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]
    errors=[]
    if len(rows)!=3:errors.append(f"expected 3 candidates, got {len(rows)}")
    ids=[r.get("candidate_id") for r in rows]
    if len(set(ids))!=len(ids):errors.append("duplicate candidate_id")
    for r in rows:
        cid=r.get("candidate_id")
        if r.get("version")!=VERSION:errors.append(f"{cid}: wrong version")
        if r.get("mode")!="FORWARD_ONLY_SHADOW":errors.append(f"{cid}: wrong mode")
        try:
            if parse(r.get("forward_start","1900-01-01T00:00:00Z")) < parse(MIN_START):
                errors.append(f"{cid}: forward_start before lock boundary")
        except Exception:
            errors.append(f"{cid}: invalid forward_start")
        if not isinstance(r.get("fixed_parameters"),dict) or not r["fixed_parameters"]:
            errors.append(f"{cid}: fixed_parameters missing")
        if "parameter_grid" in r:errors.append(f"{cid}: parameter_grid forbidden")
        if r.get("status")!="PREREGISTERED_FORWARD":errors.append(f"{cid}: wrong status")
        if not r.get("features"):errors.append(f"{cid}: features missing")
        if not r.get("direction_rule"):errors.append(f"{cid}: direction_rule missing")
        if r.get("effect_floor") is None:errors.append(f"{cid}: effect_floor missing")
    hold=HOLDOUT.read_text(encoding="utf-8")
    required=[
        "**LOCKED / DO NOT OPEN**",
        "2026-01-01 00:00 UTC → 2026-08-31 23:59 UTC",
        "forward_start = `2026-10-01T00:00:00Z`",
        "V3 mode: FORWARD-ONLY"
    ]
    for x in required:
        if x not in hold:errors.append(f"holdout lock missing marker: {x}")
    forbidden=["holdout_result","historical_2026_result","winning_threshold","parameter_grid"]
    low=raw.decode("utf-8").lower()
    for x in forbidden:
        if x in low:errors.append(f"forbidden field/string in registry: {x}")
    report={
        "version":VERSION,
        "registry_sha256":sha,
        "candidate_count":len(rows),
        "candidate_ids":ids,
        "minimum_forward_start":MIN_START,
        "historical_2026_holdout":"LOCKED",
        "pass":not errors,
        "errors":errors
    }
    out=Path("forward-v3-seal");out.mkdir(exist_ok=True)
    (out/"XRP_FORWARD_V3_SEAL.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    lines=["# XRP Forward V3 — Seal","",
           f"Result: **{'PASS' if report['pass'] else 'FAIL'}**",
           f"Registry SHA-256: `{sha}`",
           f"Candidates: **{len(rows)}**",
           "Historical 2026 holdout: **LOCKED**",
           f"Earliest forward start: **{MIN_START}**","",
           "## Candidates",""]+[f"- {x}" for x in ids]
    if errors:lines+=["","## Errors",""]+[f"- {x}" for x in errors]
    (out/"XRP_FORWARD_V3_SEAL.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines))
    if errors:raise SystemExit(2)

if __name__=="__main__":main()
