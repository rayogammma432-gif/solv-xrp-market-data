from __future__ import annotations
import csv, hashlib, io, json, urllib.request, zipfile
from datetime import datetime, timezone
from pathlib import Path

BASE="https://data.binance.vision/data/futures/um/monthly/klines/XRPUSDT/1m"
UA="xrp-taker-ratio-audit/1.0"

def months():
    for y in range(2020,2024):
        for m in range(1,13):
            yield f"{y:04d}-{m:02d}"

def get(u):
    req=urllib.request.Request(u,headers={"User-Agent":UA})
    with urllib.request.urlopen(req,timeout=60) as r:return r.read()

def main():
    anomalies=[]
    files=0
    for mo in months():
        name=f"XRPUSDT-1m-{mo}.zip";u=f"{BASE}/{name}"
        b=get(u);c=get(u+".CHECKSUM").decode().strip().splitlines()[0]
        if hashlib.sha256(b).hexdigest().lower()!=c.split()[0].lower():
            raise RuntimeError(f"checksum fail {mo}")
        z=zipfile.ZipFile(io.BytesIO(b));n=[x for x in z.namelist() if x.endswith(".csv")][0]
        with z.open(n) as f:rows=list(csv.reader(io.TextIOWrapper(f,encoding="utf-8-sig")))
        if rows and not rows[0][0].isdigit():rows=rows[1:]
        files+=1
        for r in rows:
            vol=float(r[5]);tb=float(r[9])
            if vol>0:
                ratio=tb/vol
                if ratio<0 or ratio>1:
                    ts=int(float(r[0]))
                    anomalies.append({
                        "month":mo,"open_time_ms":ts,
                        "open_time_iso":datetime.fromtimestamp(ts/1000,tz=timezone.utc).isoformat().replace("+00:00","Z"),
                        "volume":vol,"taker_buy_base":tb,"ratio":ratio,
                        "source_file":name,"source_sha256":hashlib.sha256(b).hexdigest()
                    })
    report={"files":files,"anomalies":anomalies,"count":len(anomalies)}
    Path("audit-output").mkdir(exist_ok=True)
    Path("audit-output/XRP_TAKER_RATIO_AUDIT_V1.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2),flush=True)

if __name__=="__main__":main()
