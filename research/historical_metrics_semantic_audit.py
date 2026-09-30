from __future__ import annotations
import csv, hashlib, io, json, urllib.request, zipfile
from datetime import datetime, timezone
from pathlib import Path

BASE='https://data.binance.vision/data/futures/um/daily/metrics'
SYMBOLS=['XRPUSDT','BTCUSDT']
DATES=['2020-09-01','2021-12-01','2023-09-12','2024-02-16','2024-04-08','2024-05-01','2025-07-21','2025-07-22','2026-06-24','2026-06-25','2026-06-26','2026-08-31']
UA='solv-xrp-metrics-semantic-audit/1.0'

def fetch(u):
    req=urllib.request.Request(u,headers={'User-Agent':UA})
    with urllib.request.urlopen(req,timeout=60) as r:return r.read()

def url(s,d):
    return f'{BASE}/{s}/{s}-metrics-{d}.zip'

def parse_time(x):
    x=x.strip()
    try:
        n=float(x)
        if n>1e12:return datetime.fromtimestamp(n/1000,tz=timezone.utc)
        if n>1e9:return datetime.fromtimestamp(n,tz=timezone.utc)
    except:pass
    x=x.replace('Z','+00:00')
    try:
        dt=datetime.fromisoformat(x)
    except:
        for fmt in ['%Y-%m-%d %H:%M:%S','%Y-%m-%d %H:%M:%S.%f']:
            try:dt=datetime.strptime(x,fmt);break
            except:dt=None
        if dt is None:raise ValueError(x)
    if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def one(s,d):
    u=url(s,d)
    try:
        b=fetch(u)
    except Exception as e:return {'available':False,'error':repr(e)}
    chk=fetch(u+'.CHECKSUM').decode().strip().splitlines()[0];exp=chk.split()[0].lower();act=hashlib.sha256(b).hexdigest().lower()
    z=zipfile.ZipFile(io.BytesIO(b));n=[x for x in z.namelist() if x.endswith('.csv')][0]
    with z.open(n) as f:r=list(csv.reader(io.TextIOWrapper(f,encoding='utf-8-sig')))
    header=r.pop(0); ix=[x.strip().lower() for x in header].index('create_time')
    raw=[row[ix] for row in r]; ts=[];bad=[]
    for x in raw:
        try:ts.append(parse_time(x))
        except:bad.append(x)
    vals=[int(x.timestamp()) for x in ts]
    dup=len(vals)-len(set(vals)); nonmono=sum(b<=a for a,b in zip(vals,vals[1:]))
    deltas=[b-a for a,b in zip(vals,vals[1:])]
    from collections import Counter
    dc=Counter(deltas)
    gaps=[(a,b,int((b-a).total_seconds())) for a,b in zip(ts,ts[1:]) if int((b-a).total_seconds())!=300]
    offgrid=sum((x.minute%5)!=0 or x.second!=0 or x.microsecond!=0 for x in ts)
    return {'available':True,'checksum_ok':exp==act,'rows':len(r),'header':header,
            'first_raw':raw[:5],'last_raw':raw[-5:],
            'first_iso':ts[0].isoformat().replace('+00:00','Z') if ts else None,
            'last_iso':ts[-1].isoformat().replace('+00:00','Z') if ts else None,
            'bad_time':len(bad),'duplicates':dup,'nonmonotonic':nonmono,'off_5m_grid':offgrid,
            'delta_seconds_counts':{str(k):v for k,v in sorted(dc.items())},
            'non_5m_transitions':[{'from':a.isoformat().replace('+00:00','Z'),'to':b.isoformat().replace('+00:00','Z'),'seconds':sec} for a,b,sec in gaps[:30]]}

report={'generated_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'samples':{}}
for s in SYMBOLS:
    report['samples'][s]={}
    for d in DATES:
        x=one(s,d)
        if x.get('available') or d in ['2020-09-01','2021-12-01'] or d>='2023-01-01':
            report['samples'][s][d]=x
            print(s,d,json.dumps(x),flush=True)
Path('audit-output').mkdir(exist_ok=True)
Path('audit-output/XRP_BTC_METRICS_SEMANTIC_AUDIT_V1.json').write_text(json.dumps(report,indent=2))
