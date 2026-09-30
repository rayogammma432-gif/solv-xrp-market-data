from __future__ import annotations
import csv, hashlib, io, json, urllib.request, zipfile
from datetime import datetime, timezone
from pathlib import Path

DAY="2023-11-30";START=1701347700000;END=START+60000
BASE="https://data.binance.vision/data/futures/um/daily/aggTrades/XRPUSDT"
UA="xrp-aggtrade-recovery-audit/1.0"

def get(u):
    req=urllib.request.Request(u,headers={"User-Agent":UA})
    with urllib.request.urlopen(req,timeout=120) as r:return r.read()

name=f"XRPUSDT-aggTrades-{DAY}.zip";u=f"{BASE}/{name}"
b=get(u);line=get(u+".CHECKSUM").decode().strip().splitlines()[0]
actual=hashlib.sha256(b).hexdigest().lower();expected=line.split()[0].lower()
assert actual==expected
z=zipfile.ZipFile(io.BytesIO(b));csvname=[x for x in z.namelist() if x.endswith(".csv")][0]
items=[]
with z.open(csvname) as f:
    rr=csv.reader(io.TextIOWrapper(f,encoding="utf-8-sig"))
    for r in rr:
        if not r:continue
        try:t=int(r[5])
        except:continue
        if START<=t<END:
            items.append(r)

if not items:raise SystemExit("no aggTrades in target minute")
total_qty=0.0;quote=0.0;taker_buy=0.0;taker_buy_quote=0.0;individual_trades=0
prices=[]
for r in items:
    p=float(r[1]);q=float(r[2]);first_id=int(r[3]);last_id=int(r[4]);buyer_maker=str(r[6]).lower() in ("true","1")
    total_qty+=q;quote+=p*q;prices.append(p);individual_trades+=last_id-first_id+1
    if not buyer_maker:
        taker_buy+=q;taker_buy_quote+=p*q
out={
 "source":u,"checksum_sha256":actual,"minute_start_ms":START,
 "minute_start_iso":datetime.fromtimestamp(START/1000,tz=timezone.utc).isoformat().replace("+00:00","Z"),
 "aggtrade_rows":len(items),"individual_trade_count_reconstructed":individual_trades,
 "open":float(items[0][1]),"high":max(prices),"low":min(prices),"close":float(items[-1][1]),
 "volume":total_qty,"quote_volume":quote,
 "taker_buy_base":taker_buy,"taker_buy_quote":taker_buy_quote,
 "taker_buy_ratio":taker_buy/total_qty if total_qty else None,
 "first_aggtrade_id":items[0][0],"last_aggtrade_id":items[-1][0]
}
Path("audit-output").mkdir(exist_ok=True)
Path("audit-output/XRP_20231130_1235_AGGTRADE_RECOVERY.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(out,indent=2))
