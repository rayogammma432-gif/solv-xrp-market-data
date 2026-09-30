from __future__ import annotations
import csv, hashlib, io, json, os, urllib.request, zipfile
from datetime import datetime, timezone
from pathlib import Path

BASE='https://data.binance.vision/data/futures/um/daily/klines/XRPUSDT/1m'
DAYS=['2022-02-26','2022-02-27','2022-02-28','2022-04-01','2022-04-02']
COLS=['open_time','open','high','low','close','volume','close_time','quote_volume','trades','taker_buy_base','taker_buy_quote','ignore']

def u(day,checksum=False):
    n=f'XRPUSDT-1m-{day}.zip'+('.CHECKSUM' if checksum else '')
    return f'{BASE}/{n}'

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'solv-xrp-historical-audit/1.0'})
    with urllib.request.urlopen(req,timeout=60) as r: return r.read()

def rows(blob):
    z=zipfile.ZipFile(io.BytesIO(blob)); name=[x for x in z.namelist() if x.endswith('.csv')][0]
    with z.open(name) as f: rr=list(csv.reader(io.TextIOWrapper(f,encoding='utf-8')))
    if rr and not rr[0][0].isdigit(): rr=rr[1:]
    return rr

report={'generated_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'days':{}}
ok_all=True
for day in DAYS:
    rec={}
    try:
        zb=get(u(day)); cb=get(u(day,True)); line=cb.decode().strip().splitlines()[0]
        exp=line.split()[0].lower(); act=hashlib.sha256(zb).hexdigest().lower()
        rr=rows(zb); ts=[int(r[0]) for r in rr]
        rec={'available':True,'checksum_ok':exp==act,'rows':len(rr),'first_open':datetime.fromtimestamp(ts[0]/1000,tz=timezone.utc).isoformat().replace('+00:00','Z'),'last_open':datetime.fromtimestamp(ts[-1]/1000,tz=timezone.utc).isoformat().replace('+00:00','Z'),'duplicates':len(ts)-len(set(ts)),'offgrid':sum(t%60000!=0 for t in ts),'gaps':sum((b-a)!=60000 for a,b in zip(ts,ts[1:]))}
        rec['pass']=rec['checksum_ok'] and rec['rows']==1440 and rec['duplicates']==0 and rec['offgrid']==0 and rec['gaps']==0
        ok_all=ok_all and rec['pass']
    except Exception as e:
        rec={'available':False,'pass':False,'error':repr(e)}; ok_all=False
    report['days'][day]=rec
report['result']='RECOVERABLE_FROM_DAILY' if ok_all else 'NOT_FULLY_RECOVERABLE'
Path('audit-output').mkdir(exist_ok=True)
Path('audit-output/XRP_2022_GAP_RECOVERY_V1.json').write_text(json.dumps(report,indent=2))
md=['# XRP 2022 Monthly Gap Recovery Audit V1','',f"Result: **{report['result']}**",'','| Day | Available | Checksum | Rows | Duplicates | Gaps | Result |','|---|---|---|---:|---:|---:|---|']
for d,r in report['days'].items():
    md.append(f"| {d} | {r.get('available')} | {r.get('checksum_ok','-')} | {r.get('rows','-')} | {r.get('duplicates','-')} | {r.get('gaps','-')} | {'PASS' if r.get('pass') else 'FAIL'} |")
md += ['','If all five days pass, the normalized XRP 1m dataset may replace the missing monthly slots with these official daily Binance archives while recording file-level provenance and checksums.']
Path('audit-output/XRP_2022_GAP_RECOVERY_V1.md').write_text('\n'.join(md)+'\n')
print('\n'.join(md))
