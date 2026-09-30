from __future__ import annotations
import csv, hashlib, io, json, urllib.request, zipfile
from datetime import datetime, timezone
from pathlib import Path

BASE="https://data.binance.vision/data/futures/um/monthly/klines/XRPUSDT/1m"
UA="xrp-taker-ratio-anomaly-audit/1.0"

def get(u):
    req=urllib.request.Request(u,headers={"User-Agent":UA})
    with urllib.request.urlopen(req,timeout=120) as r:return r.read()

rows_bad=[];max_ratio=(-1,None)
for m in range(1,13):
    mo=f"2023-{m:02d}";name=f"XRPUSDT-1m-{mo}.zip";u=f"{BASE}/{name}"
    b=get(u);line=get(u+".CHECKSUM").decode().strip().splitlines()[0]
    assert hashlib.sha256(b).hexdigest().lower()==line.split()[0].lower()
    z=zipfile.ZipFile(io.BytesIO(b));csvname=[x for x in z.namelist() if x.endswith(".csv")][0]
    with z.open(csvname) as f:
        rr=csv.reader(io.TextIOWrapper(f,encoding="utf-8-sig"))
        for r in rr:
            if not r or not r[0].isdigit():continue
            vol=float(r[5]);tb=float(r[9])
            if vol<=0:continue
            ratio=tb/vol
            if ratio>max_ratio[0]:max_ratio=(ratio,(mo,r[:12]))
            if ratio>1:
                t=int(r[0]);rows_bad.append({
                    "month":mo,"open_time_ms":t,
                    "open_time_iso":datetime.fromtimestamp(t/1000,tz=timezone.utc).isoformat().replace("+00:00","Z"),
                    "volume":vol,"taker_buy_base":tb,"ratio":ratio,
                    "excess_abs":tb-vol,"excess_rel":ratio-1,
                    "raw":r[:12]
                })
out={"bad_count":len(rows_bad),"bad_rows":rows_bad,"max_ratio":max_ratio[0],"max_row":max_ratio[1]}
Path("audit-output").mkdir(exist_ok=True)
Path("audit-output/XRP_TAKER_RATIO_ANOMALY_2023.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(out,indent=2))
