from __future__ import annotations
import argparse, hashlib, json, sqlite3
from pathlib import Path
import historical_normalizer_v1 as n

METRICS_START={"XRPUSDT":"2021-12","BTCUSDT":"2020-09"}

def month_range(start,end):
    y,m=map(int,start.split("-")); ey,em=map(int,end.split("-"))
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
    ap.add_argument("--start-month",required=True)
    ap.add_argument("--end-month",required=True)
    ap.add_argument("--outdir",default="window-output")
    args=ap.parse_args()
    months=list(month_range(args.start_month,args.end_month))
    out=Path(args.outdir);out.mkdir(parents=True,exist_ok=True)
    dbpath=out/f"XRP_BTC_NORMALIZED_{args.start_month}_{args.end_month}_{n.NORM}.sqlite"
    if dbpath.exists():dbpath.unlink()
    db=sqlite3.connect(dbpath);n.init_db(db)
    stats={}
    for s in n.SYMBOLS:
        stats[s]={"months":{}}
        for mo in months:
            print("normalize",s,mo,flush=True)
            st={}
            st["contract_1m"]=n.load_contract(db,s,mo)
            for fam in ("markPriceKlines","indexPriceKlines","premiumIndexKlines"):
                st[fam]=n.load_aux(db,s,mo,fam)
            st["funding"]=n.load_funding(db,s,mo)
            if mo>=METRICS_START[s]:
                st["metrics"]=n.load_metrics(db,s,mo)
            else:
                st["metrics"]={"raw":0,"normalized":0,"identical_removed":0,"conflicting_excluded":0,"not_available_by_policy":True}
            stats[s]["months"][mo]=st
            db.commit()
        print("resample",s,flush=True)
        n.resample_contract(db,s);db.commit()

    checks={}
    checks["contract_available_after_close"]=db.execute("SELECT COUNT(*) FROM contract_1m WHERE available_at_ms<=close_time_ms").fetchone()[0]==0
    checks["resampled_available_after_close"]=db.execute("SELECT COUNT(*) FROM contract_resampled WHERE available_at_ms<=close_time_ms").fetchone()[0]==0
    checks["metrics_plus_5m"]=db.execute("SELECT COUNT(*) FROM metrics WHERE available_at_ms-source_timestamp_ms!=300000").fetchone()[0]==0
    checks["funding_not_future_shifted"]=db.execute("SELECT COUNT(*) FROM funding WHERE available_at_ms!=source_timestamp_ms").fetchone()[0]==0
    checks["metrics_unique"]=db.execute("SELECT COUNT(*) FROM (SELECT symbol,source_timestamp_ms,COUNT(*) c FROM metrics GROUP BY symbol,source_timestamp_ms HAVING c>1)").fetchone()[0]==0
    checks["contract_unique"]=db.execute("SELECT COUNT(*) FROM (SELECT symbol,open_time_ms,COUNT(*) c FROM contract_1m GROUP BY symbol,open_time_ms HAVING c>1)").fetchone()[0]==0
    summary={"normalization_version":n.NORM,"start_month":args.start_month,"end_month":args.end_month,
             "months":months,"checks":checks,"pass":all(checks.values()),"stats":stats,"counts":{}}
    for s in n.SYMBOLS:
        summary["counts"][s]={}
        for table in ("contract_1m","funding","metrics"):
            summary["counts"][s][table]=db.execute(f"SELECT COUNT(*) FROM {table} WHERE symbol=?",(s,)).fetchone()[0]
        summary["counts"][s]["resampled"]={tf:db.execute("SELECT COUNT(*) FROM contract_resampled WHERE symbol=? AND timeframe=?",(s,tf)).fetchone()[0] for tf in n.TF_MIN}
    db.execute("PRAGMA wal_checkpoint(TRUNCATE)");db.commit();db.close()
    summary["database_sha256"]=db_sha(dbpath)
    (out/"WINDOW_NORMALIZATION_QC.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps({"pass":summary["pass"],"counts":summary["counts"],"database_sha256":summary["database_sha256"]},indent=2),flush=True)
    if not summary["pass"]:raise SystemExit(2)

if __name__=="__main__":main()
