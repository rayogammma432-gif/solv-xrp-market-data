from __future__ import annotations
import argparse, csv, hashlib, io, json, math, sqlite3, urllib.request, zipfile
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE="https://data.binance.vision/data/futures/um"
SYMBOLS=("XRPUSDT","BTCUSDT")
NORM="HIST_NORM_V1"
UA="solv-xrp-historical-normalizer/1.0"
RECOVERY={
    "XRPUSDT":{
        "2022-02":["2022-02-26","2022-02-27","2022-02-28"],
        "2022-04":["2022-04-01","2022-04-02"],
    }
}
TF_MIN={"5m":5,"15m":15,"1h":60,"4h":240,"1d":1440}

def get(url, timeout=120):
    req=urllib.request.Request(url,headers={"User-Agent":UA})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.read()

def sha256(b): return hashlib.sha256(b).hexdigest()

def fetch_verified(url):
    blob=get(url)
    line=get(url+".CHECKSUM").decode("utf-8","replace").strip().splitlines()[0]
    expected=line.split()[0].lower()
    actual=sha256(blob)
    if expected != actual:
        raise RuntimeError(f"checksum mismatch {url}: expected {expected} actual {actual}")
    return blob,actual,line

def unzip_csv(blob):
    z=zipfile.ZipFile(io.BytesIO(blob))
    names=[n for n in z.namelist() if n.lower().endswith(".csv")]
    if len(names)!=1:
        raise RuntimeError(f"expected 1 csv, got {names}")
    with z.open(names[0]) as f:
        rows=list(csv.reader(io.TextIOWrapper(f,encoding="utf-8-sig",newline="")))
    header=None
    if rows and rows[0]:
        try: float(rows[0][0])
        except Exception: header=[x.strip() for x in rows.pop(0)]
    return header,rows

def iso_ms(ms):
    return datetime.fromtimestamp(ms/1000,tz=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")

def parse_dt_ms(x):
    x=x.strip().replace("Z","+00:00")
    try:
        n=float(x)
        if n>1e12:return int(n)
        if n>1e9:return int(n*1000)
    except Exception: pass
    try:
        dt=datetime.fromisoformat(x)
    except Exception:
        dt=None
        for fmt in ("%Y-%m-%d %H:%M:%S.%f","%Y-%m-%d %H:%M:%S"):
            try:
                dt=datetime.strptime(x,fmt); break
            except Exception: pass
        if dt is None: raise ValueError(x)
    if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp()*1000)

def monthly_kline_url(family,symbol,interval,month):
    return f"{BASE}/monthly/{family}/{symbol}/{interval}/{symbol}-{interval}-{month}.zip"

def monthly_funding_url(symbol,month):
    return f"{BASE}/monthly/fundingRate/{symbol}/{symbol}-fundingRate-{month}.zip"

def daily_metric_url(symbol,day):
    return f"{BASE}/daily/metrics/{symbol}/{symbol}-metrics-{day}.zip"

def daily_contract_url(symbol,day):
    return f"{BASE}/daily/klines/{symbol}/1m/{symbol}-1m-{day}.zip"

def month_days(month):
    y,m=map(int,month.split("-"))
    start=datetime(y,m,1,tzinfo=timezone.utc)
    if m==12:end=datetime(y+1,1,1,tzinfo=timezone.utc)
    else:end=datetime(y,m+1,1,tzinfo=timezone.utc)
    d=start
    out=[]
    while d<end:
        out.append(d.strftime("%Y-%m-%d")); d+=timedelta(days=1)
    return out

def init_db(db):
    db.executescript("""
    PRAGMA journal_mode=WAL;
    PRAGMA synchronous=NORMAL;
    CREATE TABLE source_files(
      source_file TEXT PRIMARY KEY, dataset_family TEXT NOT NULL, symbol TEXT NOT NULL,
      source_granularity TEXT NOT NULL, sha256 TEXT NOT NULL, checksum_line TEXT NOT NULL,
      rows_raw INTEGER NOT NULL
    );
    CREATE TABLE contract_1m(
      symbol TEXT NOT NULL, open_time_ms INTEGER NOT NULL, close_time_ms INTEGER NOT NULL,
      source_timestamp_ms INTEGER NOT NULL, available_at_ms INTEGER NOT NULL,
      open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL, close REAL NOT NULL,
      volume REAL NOT NULL, quote_volume REAL NOT NULL, trades INTEGER NOT NULL,
      taker_buy_base REAL NOT NULL, taker_buy_quote REAL NOT NULL,
      source_file TEXT NOT NULL, source_sha256 TEXT NOT NULL,
      source_granularity TEXT NOT NULL, recovered_from_daily INTEGER NOT NULL,
      normalization_version TEXT NOT NULL,
      PRIMARY KEY(symbol,open_time_ms)
    );
    CREATE TABLE contract_resampled(
      symbol TEXT NOT NULL, timeframe TEXT NOT NULL, open_time_ms INTEGER NOT NULL,
      close_time_ms INTEGER NOT NULL, available_at_ms INTEGER NOT NULL,
      open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL, close REAL NOT NULL,
      volume REAL NOT NULL, quote_volume REAL NOT NULL, trades INTEGER NOT NULL,
      taker_buy_base REAL NOT NULL, taker_buy_quote REAL NOT NULL,
      component_rows INTEGER NOT NULL, normalization_version TEXT NOT NULL,
      PRIMARY KEY(symbol,timeframe,open_time_ms)
    );
    CREATE TABLE aux_kline_1m(
      symbol TEXT NOT NULL, family TEXT NOT NULL, open_time_ms INTEGER NOT NULL,
      close_time_ms INTEGER NOT NULL, source_timestamp_ms INTEGER NOT NULL,
      available_at_ms INTEGER NOT NULL,
      open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL, close REAL NOT NULL,
      source_file TEXT NOT NULL, source_sha256 TEXT NOT NULL,
      normalization_version TEXT NOT NULL,
      PRIMARY KEY(symbol,family,open_time_ms)
    );
    CREATE TABLE funding(
      symbol TEXT NOT NULL, source_timestamp_ms INTEGER NOT NULL, available_at_ms INTEGER NOT NULL,
      funding_interval_hours REAL, funding_rate REAL,
      source_file TEXT NOT NULL, source_sha256 TEXT NOT NULL,
      normalization_version TEXT NOT NULL,
      PRIMARY KEY(symbol,source_timestamp_ms)
    );
    CREATE TABLE metrics(
      symbol TEXT NOT NULL, source_timestamp_ms INTEGER NOT NULL, available_at_ms INTEGER NOT NULL,
      sum_open_interest REAL, sum_open_interest_value REAL,
      count_toptrader_long_short_ratio REAL, sum_toptrader_long_short_ratio REAL,
      count_long_short_ratio REAL, sum_taker_long_short_vol_ratio REAL,
      source_file TEXT NOT NULL, source_sha256 TEXT NOT NULL,
      dedup_identical INTEGER NOT NULL, source_zero INTEGER NOT NULL,
      source_missing_fields INTEGER NOT NULL, normalization_version TEXT NOT NULL,
      PRIMARY KEY(symbol,source_timestamp_ms)
    );
    CREATE TABLE normalization_events(
      symbol TEXT, dataset_family TEXT NOT NULL, event_type TEXT NOT NULL,
      source_timestamp_ms INTEGER, details_json TEXT NOT NULL
    );
    """)

def kline_rows(rows):
    out=[]
    for r in rows:
        if len(r)<12: continue
        out.append({
            "open_time":int(float(r[0])),"open":float(r[1]),"high":float(r[2]),"low":float(r[3]),"close":float(r[4]),
            "volume":float(r[5]),"close_time":int(float(r[6])),"quote_volume":float(r[7]),"trades":int(float(r[8])),
            "taker_buy_base":float(r[9]),"taker_buy_quote":float(r[10])
        })
    return out

def record_source(db,url,family,symbol,gran,sh,line,nrows):
    db.execute("INSERT OR REPLACE INTO source_files VALUES(?,?,?,?,?,?,?)",(url,family,symbol,gran,sh,line,nrows))

def load_contract(db,symbol,month):
    url=monthly_kline_url("klines",symbol,"1m",month)
    blob,sh,line=fetch_verified(url); h,raw=unzip_csv(blob); rows=kline_rows(raw)
    recovery=set(RECOVERY.get(symbol,{}).get(month,[]))
    # For known broken monthly XRP months, daily official files add absent timestamps.
    by_t={r["open_time"]:(r,url,sh,"monthly",0) for r in rows}
    record_source(db,url,"contract_1m",symbol,"monthly",sh,line,len(raw))
    for day in sorted(recovery):
        du=daily_contract_url(symbol,day); dbb,dsh,dline=fetch_verified(du); _,draw=unzip_csv(dbb); drows=kline_rows(draw)
        record_source(db,du,"contract_1m",symbol,"daily_recovery",dsh,dline,len(draw))
        for r in drows:
            if r["open_time"] in by_t:
                old=by_t[r["open_time"]][0]
                if any(not math.isclose(float(old[x]),float(r[x]),rel_tol=0,abs_tol=1e-12) for x in ("open","high","low","close","volume")):
                    raise RuntimeError(f"conflicting daily/monthly contract row {symbol} {iso_ms(r['open_time'])}")
                continue
            by_t[r["open_time"]]=(r,du,dsh,"daily_recovery",1)
    ordered=sorted(by_t.items())
    for t,(r,sf,ssh,gran,recovered) in ordered:
        db.execute("""INSERT INTO contract_1m VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (symbol,r["open_time"],r["close_time"],r["open_time"],r["close_time"]+1,
                    r["open"],r["high"],r["low"],r["close"],r["volume"],r["quote_volume"],r["trades"],
                    r["taker_buy_base"],r["taker_buy_quote"],sf,ssh,gran,recovered,NORM))
    return len(ordered)

def load_aux(db,symbol,month,family):
    url=monthly_kline_url(family,symbol,"1m",month)
    blob,sh,line=fetch_verified(url); _,raw=unzip_csv(blob); rows=kline_rows(raw)
    record_source(db,url,family,symbol,"monthly",sh,line,len(raw))
    for r in rows:
        db.execute("""INSERT INTO aux_kline_1m VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (symbol,family,r["open_time"],r["close_time"],r["open_time"],r["close_time"]+1,
                    r["open"],r["high"],r["low"],r["close"],url,sh,NORM))
    return len(rows)

def load_funding(db,symbol,month):
    url=monthly_funding_url(symbol,month)
    blob,sh,line=fetch_verified(url); header,raw=unzip_csv(blob)
    if not header: raise RuntimeError("funding expected header")
    idx={x.strip():i for i,x in enumerate(header)}
    tcol="calc_time" if "calc_time" in idx else header[0]
    ratecol="last_funding_rate" if "last_funding_rate" in idx else header[-1]
    intcol="funding_interval_hours" if "funding_interval_hours" in idx else None
    record_source(db,url,"fundingRate",symbol,"monthly",sh,line,len(raw))
    n=0
    for r in raw:
        ts=parse_dt_ms(r[idx[tcol]])
        interval=float(r[idx[intcol]]) if intcol and r[idx[intcol]].strip() else None
        rate=float(r[idx[ratecol]]) if r[idx[ratecol]].strip() else None
        db.execute("INSERT INTO funding VALUES(?,?,?,?,?,?,?,?)",(symbol,ts,ts,interval,rate,url,sh,NORM)); n+=1
    return n

METCOLS=("sum_open_interest","sum_open_interest_value","count_toptrader_long_short_ratio",
         "sum_toptrader_long_short_ratio","count_long_short_ratio","sum_taker_long_short_vol_ratio")

def load_metrics(db,symbol,month):
    seen={} # ts -> (values tuple, source file, sha, missing, zero, duplicate flag)
    raw_total=0; identical_removed=0; conflicting=0
    for day in month_days(month):
        url=daily_metric_url(symbol,day)
        try:
            blob,sh,line=fetch_verified(url)
        except Exception as e:
            db.execute("INSERT INTO normalization_events VALUES(?,?,?,?,?)",
                       (symbol,"metrics","SOURCE_FILE_UNAVAILABLE",None,json.dumps({"day":day,"error":repr(e)},sort_keys=True)))
            continue
        header,raw=unzip_csv(blob); raw_total+=len(raw)
        if not header: raise RuntimeError("metrics expected header")
        idx={x.strip():i for i,x in enumerate(header)}
        record_source(db,url,"metrics",symbol,"daily",sh,line,len(raw))
        for r in raw:
            ts=parse_dt_ms(r[idx["create_time"]])
            vals=[]; missing=False; zero=False
            for col in METCOLS:
                x=r[idx[col]].strip() if idx[col]<len(r) else ""
                if x=="":
                    vals.append(None); missing=True
                else:
                    v=float(x); vals.append(v)
                    if col in ("sum_open_interest","sum_open_interest_value") and v<=0: zero=True
            tup=tuple(vals)
            old=seen.get(ts)
            if old:
                if old[0]==tup:
                    identical_removed+=1
                    # preserve original provenance but set duplicate flag.
                    seen[ts]=(old[0],old[1],old[2],old[3],old[4],1)
                else:
                    conflicting+=1
                    seen[ts]=("CONFLICT",None,None,True,False,0)
                    db.execute("INSERT INTO normalization_events VALUES(?,?,?,?,?)",
                               (symbol,"metrics","CONFLICTING_DUPLICATE",ts,json.dumps({"day":day},sort_keys=True)))
            else:
                seen[ts]=(tup,url,sh,missing,zero,0)
    n=0
    for ts in sorted(seen):
        tup,sf,sh,missing,zero,dedup=seen[ts]
        if tup=="CONFLICT": continue
        db.execute("""INSERT INTO metrics VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (symbol,ts,ts+300000,*tup,sf,sh,dedup,int(zero),int(missing),NORM)); n+=1
    return {"raw":raw_total,"normalized":n,"identical_removed":identical_removed,"conflicting_excluded":conflicting}

def resample_contract(db,symbol):
    rows=db.execute("""SELECT open_time_ms,open,high,low,close,volume,quote_volume,trades,taker_buy_base,taker_buy_quote
                       FROM contract_1m WHERE symbol=? ORDER BY open_time_ms""",(symbol,)).fetchall()
    for tf,mins in TF_MIN.items():
        step=mins*60000; groups=defaultdict(list)
        for r in rows:
            bucket=(r[0]//step)*step; groups[bucket].append(r)
        for b in sorted(groups):
            g=groups[b]
            if len(g)!=mins:
                db.execute("INSERT INTO normalization_events VALUES(?,?,?,?,?)",
                           (symbol,"contract_resampled","INCOMPLETE_BUCKET",b,json.dumps({"timeframe":tf,"rows":len(g),"expected":mins},sort_keys=True)))
                continue
            # Require consecutive minutes inside bucket.
            if any(g[i+1][0]-g[i][0]!=60000 for i in range(len(g)-1)):
                db.execute("INSERT INTO normalization_events VALUES(?,?,?,?,?)",
                           (symbol,"contract_resampled","NONCONTIGUOUS_BUCKET",b,json.dumps({"timeframe":tf},sort_keys=True)))
                continue
            close_time=b+step-1
            db.execute("""INSERT INTO contract_resampled VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (symbol,tf,b,close_time,close_time+1,g[0][1],max(x[2] for x in g),min(x[3] for x in g),g[-1][4],
                        sum(x[5] for x in g),sum(x[6] for x in g),sum(x[7] for x in g),
                        sum(x[8] for x in g),sum(x[9] for x in g),len(g),NORM))

def qc(db,month):
    out={"month":month,"normalization_version":NORM,"symbols":{},"anti_lookahead":{}}
    for s in SYMBOLS:
        d={}
        for table in ("contract_1m","funding","metrics"):
            d[table]=db.execute(f"SELECT COUNT(*) FROM {table} WHERE symbol=?",(s,)).fetchone()[0]
        d["aux"]={fam:db.execute("SELECT COUNT(*) FROM aux_kline_1m WHERE symbol=? AND family=?",(s,fam)).fetchone()[0]
                  for fam in ("markPriceKlines","indexPriceKlines","premiumIndexKlines")}
        d["resampled"]={tf:db.execute("SELECT COUNT(*) FROM contract_resampled WHERE symbol=? AND timeframe=?",(s,tf)).fetchone()[0]
                        for tf in TF_MIN}
        d["events"]=db.execute("SELECT event_type,COUNT(*) FROM normalization_events WHERE symbol=? GROUP BY event_type",(s,)).fetchall()
        d["source_files"]=db.execute("SELECT COUNT(*) FROM source_files WHERE symbol=?",(s,)).fetchone()[0]
        out["symbols"][s]=d

    checks={}
    checks["contract_available_after_close"]=db.execute("SELECT COUNT(*) FROM contract_1m WHERE available_at_ms<=close_time_ms").fetchone()[0]==0
    checks["resampled_available_after_close"]=db.execute("SELECT COUNT(*) FROM contract_resampled WHERE available_at_ms<=close_time_ms").fetchone()[0]==0
    checks["metrics_plus_5m"]=db.execute("SELECT COUNT(*) FROM metrics WHERE available_at_ms-source_timestamp_ms!=300000").fetchone()[0]==0
    checks["funding_not_future_shifted"]=db.execute("SELECT COUNT(*) FROM funding WHERE available_at_ms!=source_timestamp_ms").fetchone()[0]==0
    checks["metrics_unique"]=db.execute("SELECT COUNT(*) FROM (SELECT symbol,source_timestamp_ms,COUNT(*) c FROM metrics GROUP BY symbol,source_timestamp_ms HAVING c>1)").fetchone()[0]==0
    checks["contract_unique"]=db.execute("SELECT COUNT(*) FROM (SELECT symbol,open_time_ms,COUNT(*) c FROM contract_1m GROUP BY symbol,open_time_ms HAVING c>1)").fetchone()[0]==0
    out["anti_lookahead"]=checks
    out["pass"]=all(checks.values())
    return out

def db_sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--month",default="2023-01")
    ap.add_argument("--outdir",default="audit-output")
    args=ap.parse_args()
    out=Path(args.outdir);out.mkdir(parents=True,exist_ok=True)
    dbpath=out/f"XRP_BTC_NORMALIZED_{args.month}_{NORM}.sqlite"
    if dbpath.exists():dbpath.unlink()
    db=sqlite3.connect(dbpath);init_db(db)
    load_stats={}
    for s in SYMBOLS:
        print("normalize",s,args.month,flush=True)
        load_stats[s]={}
        load_stats[s]["contract_1m"]=load_contract(db,s,args.month)
        for fam in ("markPriceKlines","indexPriceKlines","premiumIndexKlines"):
            load_stats[s][fam]=load_aux(db,s,args.month,fam)
        load_stats[s]["funding"]=load_funding(db,s,args.month)
        load_stats[s]["metrics"]=load_metrics(db,s,args.month)
        resample_contract(db,s)
        db.commit()
    qc_report=qc(db,args.month)
    qc_report["load_stats"]=load_stats
    qc_report["database_sha256"]=None
    qc_report["schema_version"]="HIST_NORMALIZED_SCHEMA_V1"
    db.execute("PRAGMA wal_checkpoint(TRUNCATE)");db.commit();db.close()
    qc_report["database_sha256"]=db_sha(dbpath)
    qcpath=out/f"XRP_BTC_NORMALIZATION_QC_{args.month}_{NORM}.json"
    qcpath.write_text(json.dumps(qc_report,indent=2),encoding="utf-8")
    md=[
        "# XRP + BTC Normalization Smoke Test V1","",
        f"Month: **{args.month}**",f"Normalization: **{NORM}**",
        f"Result: **{'PASS' if qc_report['pass'] else 'FAIL'}**","",
        f"SQLite SHA-256: `{qc_report['database_sha256']}`","",
        "## Counts","",
        "| Symbol | Contract 1m | Funding | Metrics | Mark 1m | Index 1m | Premium 1m | 5m | 15m | 1h | 4h | 1d |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for s,d in qc_report["symbols"].items():
        md.append(f"| {s} | {d['contract_1m']} | {d['funding']} | {d['metrics']} | {d['aux']['markPriceKlines']} | {d['aux']['indexPriceKlines']} | {d['aux']['premiumIndexKlines']} | {d['resampled']['5m']} | {d['resampled']['15m']} | {d['resampled']['1h']} | {d['resampled']['4h']} | {d['resampled']['1d']} |")
    md+=["","## Metrics normalization",""]
    for s,st in load_stats.items():
        m=st["metrics"]
        md.append(f"- {s}: raw={m['raw']}, normalized={m['normalized']}, identical duplicates removed={m['identical_removed']}, conflicting excluded={m['conflicting_excluded']}")
    md+=["","## Anti-look-ahead invariants",""]
    for k,v in qc_report["anti_lookahead"].items():md.append(f"- {k}: {'PASS' if v else 'FAIL'}")
    md+=["","## Notes","",
         "- This is a normalization smoke test, not a strategy backtest.",
         "- No outcomes, ANALYSES, SIGNALS, CURRENT-agent decisions, ALERT_FORWARD or ALERT_MFE_MAE are read.",
         "- The SQLite artifact is temporary validation output. Large historical datasets are not committed to Git.",
         ""]
    (out/f"XRP_BTC_NORMALIZATION_QC_{args.month}_{NORM}.md").write_text("\n".join(md),encoding="utf-8")
    print("\n".join(md),flush=True)
    if not qc_report["pass"]: raise SystemExit(2)

if __name__=="__main__":
    main()
