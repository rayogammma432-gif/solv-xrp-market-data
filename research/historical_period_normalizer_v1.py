from __future__ import annotations
import argparse, hashlib, json, sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import historical_normalizer_v1 as n

COVERAGE_START={"XRPUSDT":"2021-12","BTCUSDT":"2020-09"}

def load_metrics_fast(db,symbol,month,max_workers=16):
    def fetch_day(day):
        url=n.daily_metric_url(symbol,day)
        blob,sh,line=n.fetch_verified(url)
        header,raw=n.unzip_csv(blob)
        if not header: raise RuntimeError("metrics expected header")
        idx={x.strip():i for i,x in enumerate(header)}
        parsed=[]
        for r in raw:
            ts=n.parse_dt_ms(r[idx["create_time"]])
            vals=[];missing=False;zero=False
            for col in n.METCOLS:
                x=r[idx[col]].strip() if idx[col]<len(r) else ""
                if x=="":
                    vals.append(None);missing=True
                else:
                    v=float(x);vals.append(v)
                    if col in ("sum_open_interest","sum_open_interest_value") and v<=0:zero=True
            parsed.append((ts,tuple(vals),missing,zero))
        return day,url,sh,line,len(raw),parsed

    days=n.month_days(month)
    results=[]
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs={ex.submit(fetch_day,d):d for d in days}
        for fut in as_completed(futs):
            d=futs[fut]
            try:results.append(fut.result())
            except Exception as e:
                db.execute("INSERT INTO normalization_events VALUES(?,?,?,?,?)",
                           (symbol,"metrics","SOURCE_FILE_UNAVAILABLE",None,json.dumps({"day":d,"error":repr(e)},sort_keys=True)))
    results.sort(key=lambda x:x[0])
    seen={};raw_total=0;identical_removed=0;conflicting=0
    for day,url,sh,line,nraw,parsed in results:
        raw_total+=nraw
        n.record_source(db,url,"metrics",symbol,"daily",sh,line,nraw)
        for ts,tup,missing,zero in parsed:
            old=seen.get(ts)
            if old:
                if old[0]==tup:
                    identical_removed+=1
                    seen[ts]=(old[0],old[1],old[2],old[3],old[4],1)
                else:
                    conflicting+=1
                    seen[ts]=("CONFLICT",None,None,True,False,0)
                    db.execute("INSERT INTO normalization_events VALUES(?,?,?,?,?)",
                               (symbol,"metrics","CONFLICTING_DUPLICATE",ts,json.dumps({"day":day},sort_keys=True)))
            else:
                seen[ts]=(tup,url,sh,missing,zero,0)
    normalized=0
    for ts in sorted(seen):
        tup,sf,sh,missing,zero,dedup=seen[ts]
        if tup=="CONFLICT":continue
        db.execute("""INSERT INTO metrics VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (symbol,ts,ts+300000,*tup,sf,sh,dedup,int(zero),int(missing),n.NORM))
        normalized+=1
    return {"raw":raw_total,"normalized":normalized,"identical_removed":identical_removed,"conflicting_excluded":conflicting}

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
                ms=load_metrics_fast(db,s,mo)
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
