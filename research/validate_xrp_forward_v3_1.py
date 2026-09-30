from __future__ import annotations
import hashlib, json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"termux"))
import forward_v3_tracker as t

REG=ROOT/"research/experiments/XRP_FORWARD_REGISTRY_V3_1.jsonl"
PROTOCOL=ROOT/"research/XRP_FORWARD_RESEARCH_PROTOCOL_V3_1.md"
HOLDOUT=ROOT/"research/XRP_2026_HOLDOUT_LOCK_V1.md"

EXPECTED_START="2026-10-01T06:00:00Z"
EXPECTED_GATE="2027-03-30T06:00:00Z"
EXPECTED_IDS=[
 "XRP-FWD-V3-A-TAKER-EXHAUSTION",
 "XRP-FWD-V3-B-OI-MODERATOR",
 "XRP-FWD-V3-C-MOMENTUM-EXHAUSTION",
]

def main():
    raw=REG.read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    rows=[json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]
    errors=[]
    ids=[r.get("candidate_id") for r in rows]
    if ids!=EXPECTED_IDS:errors.append(f"unexpected candidate IDs/order: {ids}")
    if len(set(ids))!=3:errors.append("candidate IDs not unique")
    if sha!=t.REGISTRY_SHA256:errors.append(f"tracker registry SHA mismatch {t.REGISTRY_SHA256} != {sha}")
    if t.PROTOCOL_VERSION!="XRP_FORWARD_V3_1":errors.append("tracker protocol version mismatch")
    if t.FORWARD_START_UTC.isoformat().replace("+00:00","Z")!=EXPECTED_START:
        errors.append("tracker forward start mismatch")

    for r in rows:
        cid=r.get("candidate_id")
        if r.get("version")!="XRP_FORWARD_V3_1":errors.append(f"{cid}: wrong version")
        if r.get("mode")!="FORWARD_ONLY_SHADOW":errors.append(f"{cid}: wrong mode")
        if r.get("forward_start")!=EXPECTED_START:errors.append(f"{cid}: wrong start")
        if r.get("formal_family_gate")!=EXPECTED_GATE:errors.append(f"{cid}: wrong family gate")
        if "parameter_grid" in r:errors.append(f"{cid}: parameter_grid forbidden")
        if not isinstance(r.get("fixed_parameters"),dict) or not r["fixed_parameters"]:
            errors.append(f"{cid}: missing fixed parameters")
        if r.get("multiplicity")!="Holm across all 3 V3.1 primary hypotheses at common 180-day gate":
            errors.append(f"{cid}: multiplicity rule mismatch")
        if r.get("status")!="PREREGISTERED_FORWARD":errors.append(f"{cid}: wrong status")

    protocol=PROTOCOL.read_text(encoding="utf-8")
    for marker in [
        "**FROZEN BEFORE FORWARD START**",
        EXPECTED_START,
        EXPECTED_GATE,
        "Holm",
        "PRIMARY_15M resampleado exclusivamente desde 15 velas XRPUSDT 1m",
        "FORWARD_PASS_RESEARCH",
    ]:
        if marker not in protocol:errors.append(f"protocol marker missing: {marker}")

    hold=HOLDOUT.read_text(encoding="utf-8")
    for marker in [
        "**LOCKED / DO NOT OPEN**",
        "2026-01-01 00:00 UTC → 2026-08-31 23:59 UTC",
        EXPECTED_START,
    ]:
        if marker not in hold:errors.append(f"holdout marker missing: {marker}")

    report={
        "version":"XRP_FORWARD_V3_1",
        "registry_sha256":sha,
        "candidate_count":len(rows),
        "candidate_ids":ids,
        "forward_start":EXPECTED_START,
        "formal_family_gate":EXPECTED_GATE,
        "historical_2026_holdout":"LOCKED",
        "tracker_registry_sha256":t.REGISTRY_SHA256,
        "pass":not errors,
        "errors":errors,
    }
    out=ROOT/"forward-v3-1-seal";out.mkdir(exist_ok=True)
    (out/"XRP_FORWARD_V3_1_SEAL.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    lines=["# XRP Forward V3.1 — Seal","",
           f"Result: **{'PASS' if report['pass'] else 'FAIL'}**",
           f"Registry SHA-256: `{sha}`",
           f"Candidates: **{len(rows)}**",
           f"Forward start: **{EXPECTED_START}**",
           f"Formal family gate: **{EXPECTED_GATE}**",
           "Historical 2026 holdout: **LOCKED**","",
           "## Candidates",""]+[f"- {x}" for x in ids]
    if errors:lines+=["","## Errors",""]+[f"- {x}" for x in errors]
    (out/"XRP_FORWARD_V3_1_SEAL.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines))
    if errors:raise SystemExit(2)

if __name__=="__main__":main()
