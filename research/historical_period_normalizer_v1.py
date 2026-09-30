from __future__ import annotations
import argparse, hashlib, json, sqlite3
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import historical_normalizer_v1 as n

COVERAGE_START={"XRPUSDT":"2021-12","BTCUSDT":"2020-09"}

def months(start,end):
    y,m=map(int,start.split("-"));ey,em=map(int,end.split("-"))
    while (y,m)<=(ey,em):
        yield f"{y:04d}-{m:02d}"
        m+=1
        if m==13:y+=1;m=1

def db_sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--start",default="2020-01")
    ap.add_argument("--end",default="2023-12")
    ap.add_argument("--outdir",default="baseline-work")
    args=ap.parse_args()
    out=Path(args.outdir);out.mkdir(parents=True,exist_ok=True)
    dbpath=out/f"XRP_BTC_PERIOD_{args.start}_{args.end}_{n.NORM}.sqlite"
    if dbpath.exists():dbpath.unlink()
    db=sqlite3.connect(dbpath)
    n.init_db(db)

    stats={s:{"months":0,"contract":0,"funding":0,"metrics_raw":0,"metrics_normalized":0} for s in n.SYMBOLS}
    for mo in months(args.start,args.end):
        print("MONTH",mo,flush=True)
        for s in n.SYMBOLS:
            stats[s]["months"]+=1
            stats[s]["contract"]+=n.load_contract(db,s,mo)
            for fam in ("markPriceKlines","indexPriceKlines","premiumIndexKlines"):
                n.load_aux(db,s,mo,fam)
            stats[s]["funding"]+=n.load_funding(db,s,mo)
            if mo>=COVERAGE_START[s]:
                ms=n.load_metrics(db,s,mo)
                stats[s]["metrics_raw"]+=ms["raw"];stats[s]["metrics_normalized"]+=ms["normalized"]
        db.commit()

    for s in n.SYMBOLS:
        print("RESAMPLE",s,flush=True)
        n.resample_contract(db,s)
        db.commit()

    # Global invariants.
    checks={
      "contract_unique":db.execute("SELECT COUNT(*) FROM (SELECT symbol,open_time_ms,COUNT(*) c FROM contract_1m GROUP BY symbol,open_time_ms HAVING c>1)").fetchone()[0]==0,
      "metrics_unique":db.execute("SELECT COUNT(*) FROM (SELECT symbol,source_timestamp_ms,COUNT(*) c FROM metrics GROUP BY symbol,source_timestamp_ms HAVING c>1)").fetchone()[0]==0,
      "metrics_plus_5m":db.execute("SELECT COUNT(*) FROM metrics WHERE available_at_ms-source_timestamp_ms!=300000").fetchone()[0]==0,
      "contract_after_close":db.execute("SELECT COUNT(*) FROM contract_1m WHERE available_at_ms<=close_time_ms").fetchone()[0]==0,
      "resampled_after_close":db.execute("SELECT COUNT(*) FROM contract_resampled WHERE available_at_ms<=close_time_ms").fetchone()[0]==0
    }
    report={"generated_utc":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"start":args.start,"end":args.end,"stats":stats,"checks":checks,"pass":all(checks.values())}
    db.execute("PRAGMA wal_checkpoint(TRUNCATE)");db.commit();db.close()
    report["database_sha256"]=db_sha(dbpath)
    (out/"PERIOD_NORMALIZATION_QC.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2),flush=True)
    if not report["pass"]:raise SystemExit(2)

if __name__=="__main__":main()
