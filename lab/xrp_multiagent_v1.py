#!/usr/bin/env python3
"""XRP Multiagent Lab V1: isolated, manual SHADOW runner. NO ORDER API.
Requires: pip install google-api-python-client google-auth
ENV: XRP_LAB_SOURCE_CREDS (read-only service identity)
     XRP_LAB_A_CREDS / XRP_LAB_B_CREDS (writer identities scoped to each lab Sheet)
     XRP_LAB_IAM_APPROVED=YES only after negative permission checks by operator.
Usage:
  python lab/xrp_multiagent_v1.py capture --out /secure/snapshot.json
  python lab/xrp_multiagent_v1.py run --agent A --snapshot /secure/snapshot.json
  python lab/xrp_multiagent_v1.py run --agent B --snapshot /secure/snapshot.json
Both agents MUST receive exactly the same untouched snapshot file.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "agents/XRP_MULTIAGENT_LAB_MANIFEST_V1.json"
UTC = dt.timezone.utc


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_manifest():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert m["status"] == "SETUP_ONLY_SHADOW"
    assert m["production_manifest_untouched"] == "agents/XRP_MASTER_MANIFEST.json"
    for spec in [dict(master_path=m["protocol_path"], master_git_blob_sha=m["protocol_git_blob_sha"]),
                 *m["agents"].values()]:
        p = ROOT / spec["master_path"]
        if not p.resolve().is_relative_to(ROOT.resolve()):
            raise RuntimeError("Path outside repo")
        if blob_sha(p.read_bytes()) != spec["master_git_blob_sha"]:
            raise RuntimeError(f"MASTER_MISMATCH: {p}")
    return m


def client(credentials_path, read_only):
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    if not credentials_path:
        raise RuntimeError("Missing credentials: fail closed")
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"] if read_only else [
        "https://www.googleapis.com/auth/spreadsheets"]
    cred = service_account.Credentials.from_service_account_file(credentials_path, scopes=scopes)
    return build("sheets", "v4", credentials=cred, cache_discovery=False).spreadsheets()


def timestamp(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(UTC)


def number(s):
    if s in ("", None): raise ValueError("Missing numeric value")
    raw = str(s).strip().replace(" ", "")
    if "," in raw and "." in raw: raise ValueError("Ambiguous decimal")
    x = float(raw.replace(",", "."))
    if not math.isfinite(x): raise ValueError("Nonfinite")
    return x


def validate(state, generated, captured):
    if state.get("market.symbol") != "XRPUSDT":
        raise ValueError("symbol mismatch")
    age = (timestamp(captured) - timestamp(generated)).total_seconds()
    if age < -15 or age > 120:
        raise ValueError(f"STALE_SNAPSHOT age={age}")
    for tf in ["1m", "5m", "15m", "1h", "4h", "1d"]:
        if state.get("data.sync_" + tf) != "OK" or state.get("btc.data.sync_" + tf) != "OK":
            raise ValueError(f"SYNC_BAD {tf}")
        last = state.get("data.last_close_" + tf)
        expected = state.get("data.expected_last_close_" + tf)
        btc_last = state.get("btc.data.last_close_" + tf)
        if not last or last != expected or not btc_last:
            raise ValueError(f"BAR_INCOMPLETE {tf}")
        if timestamp(last) > timestamp(generated) or timestamp(btc_last) > timestamp(generated):
            raise ValueError(f"LOOKAHEAD {tf}")
    number(state.get("market.mark_price"))


def capture(output):
    m = load_manifest()
    src = client(os.environ.get("XRP_LAB_SOURCE_CREDS"), True)
    resp = src.values().get(
        spreadsheetId=m["source"]["spreadsheet_id"],
        range="LIVE_STATE!A1:E214", valueRenderOption="FORMATTED_VALUE").execute()
    rows = resp.get("values", [])
    state = {}
    for row in rows[1:]:
        if len(row) >= 2:
            if row[0] in state: raise ValueError("Duplicate LIVE_STATE key")
            state[row[0]] = row[1]
    now = dt.datetime.now(UTC).isoformat().replace("+00:00", "Z")
    generated = state.get("system.generated_at_utc", "")
    validate(state, generated, now)
    body = {"source_sheet_id":m["source"]["spreadsheet_id"], "snapshot_utc":generated,
            "captured_at_utc":now, "state":state}
    obj = {"data":body, "snapshot_sha256":sha256(body)}
    obj["snapshot_id"] = "XLAB1|" + obj["snapshot_sha256"][:24]
    path = Path(output)
    if path.exists(): raise RuntimeError("Refuse overwrite of frozen capture")
    path.write_bytes(canonical(obj) + b"\n")
    print("CAPTURED", obj["snapshot_id"], obj["snapshot_sha256"])


def assess(agent, state):
    try:
        n = lambda k: number(state.get(k))
        if agent == "A":
            x = {k:n(k) for k in ["4h.close","4h.ema50","1h.close","1h.ema20",
              "1h.ema50","15m.close","15m.ema20","15m.ema50",
              "15m.rsi14","15m.volume_rel20","btc.1h.close","btc.1h.ema50"]}
            long = (x["4h.close"]>x["4h.ema50"] and
              x["1h.close"]>x["1h.ema20"]>x["1h.ema50"] and
              x["15m.close"]>x["15m.ema20"]>x["15m.ema50"] and
              52<=x["15m.rsi14"]<=70 and x["15m.volume_rel20"]>=1.10 and
              x["btc.1h.close"]>x["btc.1h.ema50"])
            short = (x["4h.close"]<x["4h.ema50"] and
              x["1h.close"]<x["1h.ema20"]<x["1h.ema50"] and
              x["15m.close"]<x["15m.ema20"]<x["15m.ema50"] and
              30<=x["15m.rsi14"]<=48 and x["15m.volume_rel20"]>=1.10 and
              x["btc.1h.close"]<x["btc.1h.ema50"])
            strat = "TREND_CONTINUATION_V1"
        else:
            x = {k:n(k) for k in ["15m.rsi14","15m.close","15m.ema20",
                 "15m.atr14","1m.rsi14","1h.rsi14","btc.1h.rsi14"]}
            if x["15m.atr14"]<=0: raise ValueError("ATR<=0")
            long = (x["15m.rsi14"]<=32 and x["15m.close"]<x["15m.ema20"] and
                x["15m.close"]<=x["15m.ema20"]-x["15m.atr14"] and
                x["1m.rsi14"]>=x["15m.rsi14"] and x["1h.rsi14"]>=25 and
                x["btc.1h.rsi14"]>=35)
            short = (x["15m.rsi14"]>=68 and x["15m.close"]>x["15m.ema20"] and
                x["15m.close"]>=x["15m.ema20"]+x["15m.atr14"] and
                x["1m.rsi14"]<=x["15m.rsi14"] and x["1h.rsi14"]<=75 and
                x["btc.1h.rsi14"]<=65)
            strat = "MEAN_REVERSION_V1"
        if long and short: return strat, "DATA_INSUFFICIENT", "CONTRADICTORY", json.dumps(x,sort_keys=True)
        dec = "SHADOW_LONG" if long else "SHADOW_SHORT" if short else "NO_TRADE"
        return strat, dec, "CANDIDATE_ONLY" if dec!="NO_TRADE" else "NO_SETUP", json.dumps(x,sort_keys=True)
    except (ValueError,KeyError,TypeError) as e:
        return ("TREND_CONTINUATION_V1" if agent=="A" else "MEAN_REVERSION_V1",
                "DATA_INSUFFICIENT","FEATURE_MISSING",str(e))


def append_checked(svc, book, spec, decision, args):
    # Single-writer external lease mandatory for unattended use; no distributed lock here.
    existing = svc.values().get(spreadsheetId=book, range="RUNS!A1:N2000").execute().get("values",[])
    if not existing or existing[0][0]!="run_id": raise RuntimeError("Schema mismatch")
    run_id = args["run_id"]
    for row in existing[1:]:
        if row and row[0]==run_id:
            if len(row)>11 and row[11] in ("COMPLETE","DATA_INSUFFICIENT"):
                print("DUPLICATE_RUN", run_id); return
            raise RuntimeError("PERSISTENCE_FAILED_RECONCILE: existing incomplete RUNS row")
    for tab, col in [("DECISIONS","A"),("AUDIT","A")]:
        val = svc.values().get(spreadsheetId=book,range=f"{tab}!{col}1:{col}2000").execute()
        if not val.get("values") or not val["values"][0] : raise RuntimeError(f"Schema mismatch {tab}")
    prior_dec = svc.values().get(spreadsheetId=book,range="DECISIONS!A1:A2000").execute().get("values",[])
    prior_aud = svc.values().get(spreadsheetId=book,range="AUDIT!A1:A2000").execute().get("values",[])
    def idx(rows):
        if len(rows)>=2000: raise RuntimeError("Destination full")
        return len(rows)+1
    utc=args["when"]
    run_row=[run_id,spec["agent_id"],args["snapshot_id"],args["snapshot_utc"],utc,
             args["model_id"],args["run_mode"],"LAB_V1",spec["master_git_blob_sha"],
             args["snapshot_sha"],"OK","STARTED",
             args["decision_id"],"MANUAL_DEPLOYMENT_ONLY"]
    decision_row=[args["decision_id"],run_id,spec["agent_id"],args["snapshot_id"],
      "XRPUSDT",args["snapshot_utc"],decision[0],
      "LONG" if decision[1]=="SHADOW_LONG" else "SHORT" if decision[1]=="SHADOW_SHORT" else "",
      decision[1],"OBSERVATIONAL",decision[2],"","","","","",0,
      decision[2],decision[3],"LAB_V1",spec["master_git_blob_sha"],sha256(decision),utc]
    audit_row=["AUD|"+run_id,utc,spec["agent_id"],run_id,"SHADOW_DECISION","INFO",
               "readback required",args["source_id"],book]
    requests=[
      {"range":f"RUNS!A{idx(existing)}:N{idx(existing)}","values":[run_row]},
      {"range":f"DECISIONS!A{idx(prior_dec)}:W{idx(prior_dec)}","values":[decision_row]},
      {"range":f"AUDIT!A{idx(prior_aud)}:I{idx(prior_aud)}","values":[audit_row]},
    ]
    svc.values().batchUpdate(spreadsheetId=book, body={"valueInputOption":"RAW","data":requests}).execute()
    # Read-back each ID: failure is NOT COMPLETE.
    for tab, row, key in [("RUNS",idx(existing),run_id),
                          ("DECISIONS",idx(prior_dec),args["decision_id"]),
                          ("AUDIT",idx(prior_aud),"AUD|"+run_id)]:
        got=svc.values().get(spreadsheetId=book,range=f"{tab}!A{row}").execute().get("values",[])
        if not got or not got[0] or got[0][0]!=key:
            raise RuntimeError("PERSISTENCE_FAILED read-back "+tab)
    final_status = "DATA_INSUFFICIENT" if decision[1]=="DATA_INSUFFICIENT" else "COMPLETE"
    svc.values().update(
        spreadsheetId=book,range=f"RUNS!L{idx(existing)}",valueInputOption="RAW",
        body={"values":[[final_status]]}).execute()
    status=svc.values().get(spreadsheetId=book,range=f"RUNS!L{idx(existing)}").execute().get("values",[])
    if not status or status[0][0]!=final_status:
        raise RuntimeError("PERSISTENCE_FAILED: completion status readback")
    print(final_status, spec["agent_id"],run_id,decision[1])


def run(agent, snap_path):
    m=load_manifest()
    if os.environ.get("XRP_LAB_IAM_APPROVED")!="YES":
        raise RuntimeError("IAM not verified: do not start writer")
    spec=m["agents"][agent]
    snapshot=json.loads(Path(snap_path).read_text(encoding="utf-8"))
    body=snapshot["data"]
    expected=sha256(body)
    if expected!=snapshot.get("snapshot_sha256") or snapshot.get("snapshot_id")!="XLAB1|"+expected[:24]:
        raise RuntimeError("Tampered snapshot")
    if body["source_sheet_id"]!=m["source"]["spreadsheet_id"]:
        raise RuntimeError("Unauthorized input sheet")
    validate(body["state"],body["snapshot_utc"],body["captured_at_utc"])
    decision=assess(agent,body["state"])
    model="PY_RULE_ENGINE_V1"
    mode="AUTOMATED_SHADOW"
    rid=sha256([spec["agent_id"],spec["master_git_blob_sha"],expected,model,mode])
    when=dt.datetime.now(UTC).isoformat().replace("+00:00","Z")
    writer=client(os.environ.get("XRP_LAB_"+agent+"_CREDS"),False)
    args={"run_id":"RLAB|"+rid[:28],"decision_id":"DLAB|"+rid[:28],"snapshot_id":snapshot["snapshot_id"],
      "snapshot_utc":body["snapshot_utc"],"snapshot_sha":expected,
      "model_id":model,"run_mode":mode,"when":when,"source_id":body["source_sheet_id"]}
    append_checked(writer,spec["destination_sheet_id"],spec,decision,args)


def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="command",required=True)
    cap=sub.add_parser("capture"); cap.add_argument("--out",required=True)
    ru=sub.add_parser("run"); ru.add_argument("--agent",choices=["A","B"],required=True)
    ru.add_argument("--snapshot",required=True)
    args=p.parse_args()
    if args.command=="capture": capture(args.out)
    else: run(args.agent,args.snapshot)

if __name__=="__main__":
    main()
