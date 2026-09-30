from __future__ import annotations
import calendar, csv, hashlib, io, json, math, os, urllib.error, urllib.request, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE='https://data.binance.vision/data/futures/um'
SYMBOLS=['XRPUSDT','BTCUSDT']
START='2020-01'
END='2026-08'
UA='solv-xrp-derivatives-audit/1.0'

def months(start=START,end=END):
    y,m=map(int,start.split('-')); ey,em=map(int,end.split('-'))
    while (y,m)<=(ey,em):
        yield f'{y:04d}-{m:02d}'
        m+=1
        if m==13: y+=1; m=1

def days(start='2020-01-01',end='2026-08-31'):
    d=datetime.fromisoformat(start).date(); e=datetime.fromisoformat(end).date()
    while d<=e:
        yield d.isoformat(); d+=timedelta(days=1)

def req(url,method='GET',timeout=30):
    return urllib.request.urlopen(urllib.request.Request(url,method=method,headers={'User-Agent':UA}),timeout=timeout)

def probe(url):
    try:
        with req(url,'HEAD',20) as r:
            return {'exists':True,'status':getattr(r,'status',200),'size':int(r.headers.get('Content-Length') or 0) or None}
    except urllib.error.HTTPError as e:
        return {'exists':False,'status':e.code,'size':None}
    except Exception as e:
        return {'exists':False,'status':None,'size':None,'error':repr(e)}

def fetch(url):
    with req(url,'GET',120) as r: return r.read()

def checksum(zip_url,blob=None):
    if blob is None: blob=fetch(zip_url)
    c=fetch(zip_url+'.CHECKSUM').decode('utf-8','replace').strip().splitlines()[0]
    expected=c.split()[0].lower(); actual=hashlib.sha256(blob).hexdigest().lower()
    return {'ok':expected==actual,'expected':expected,'actual':actual,'line':c}

def unzip_rows(blob):
    z=zipfile.ZipFile(io.BytesIO(blob)); names=[n for n in z.namelist() if n.lower().endswith('.csv')]
    if not names: raise RuntimeError('no csv in zip')
    with z.open(names[0]) as f:
        rr=list(csv.reader(io.TextIOWrapper(f,encoding='utf-8-sig',newline='')))
    header=None
    if rr and rr[0]:
        try: float(rr[0][0])
        except Exception: header=rr.pop(0)
    return header,rr

def iso_ms(ms):
    try:return datetime.fromtimestamp(int(float(ms))/1000,tz=timezone.utc).isoformat().replace('+00:00','Z')
    except:return None

def monthly_url(kind,symbol,month,interval='1m'):
    if kind=='fundingRate':
        return f'{BASE}/monthly/fundingRate/{symbol}/{symbol}-fundingRate-{month}.zip'
    return f'{BASE}/monthly/{kind}/{symbol}/{interval}/{symbol}-{interval}-{month}.zip'

def metric_url(symbol,day):
    return f'{BASE}/daily/metrics/{symbol}/{symbol}-metrics-{day}.zip'

def find_time_col(header,rows,candidates):
    if header:
        h=[x.strip().lower() for x in header]
        for c in candidates:
            if c in h:return h.index(c)
    # fallback: first column for kline/metrics in public archive; funding often calc_time first
    return 0

def audit_time_rows(header,rows,expected_step_ms=None,time_candidates=()):
    if not rows:return {'rows':0,'header':header,'error':'empty'}
    ix=find_time_col(header,rows,[x.lower() for x in time_candidates])
    vals=[]
    bad_time=0
    for r in rows:
        try: vals.append(int(float(r[ix])))
        except: bad_time+=1
    dup=len(vals)-len(set(vals))
    nonmono=sum(b<=a for a,b in zip(vals,vals[1:]))
    offgrid=0; gaps=[]
    if expected_step_ms:
        offgrid=sum(v%expected_step_ms!=0 for v in vals)
        gaps=[(a,b,(b-a)//expected_step_ms) for a,b in zip(vals,vals[1:]) if b-a!=expected_step_ms]
    return {'rows':len(rows),'header':header,'time_col_index':ix,'first_iso':iso_ms(vals[0]) if vals else None,
            'last_iso':iso_ms(vals[-1]) if vals else None,'bad_time':bad_time,'duplicates':dup,'nonmonotonic':nonmono,
            'offgrid':offgrid,'gap_count':len(gaps),'gap_examples':[{'from':iso_ms(a),'to':iso_ms(b),'steps':n} for a,b,n in gaps[:10]]}

def audit_monthly_family(kind):
    result={'kind':kind,'symbols':{}}
    for s in SYMBOLS:
        inv=[]
        for mo in months():
            u=monthly_url(kind,s,mo)
            p=probe(u); inv.append({'month':mo,'url':u,**p})
        available=[x['month'] for x in inv if x['exists']]
        missing_inside=[]
        if available:
            lo=available[0]; hi=available[-1]; inspan=False
            aset=set(available)
            for mo in months():
                if mo==lo: inspan=True
                if inspan and mo not in aset: missing_inside.append(mo)
                if mo==hi: break
        samples={}
        candidates=[]
        if available:
            candidates=[available[0]]
            for x in ['2023-01','2026-08']:
                if x in set(available) and x not in candidates:candidates.append(x)
            if available[-1] not in candidates:candidates.append(available[-1])
        for mo in candidates:
            u=monthly_url(kind,s,mo)
            rec={'month':mo,'url':u}
            try:
                b=fetch(u); rec['checksum']=checksum(u,b); h,rr=unzip_rows(b)
                if kind=='fundingRate':
                    rec['audit']=audit_time_rows(h,rr,None,('calc_time','fundingtime','funding_time','time'))
                else:
                    rec['audit']=audit_time_rows(h,rr,60000,('open_time','open time'))
            except Exception as e: rec['error']=repr(e)
            samples[mo]=rec
        result['symbols'][s]={'available_months':len(available),'first_available':available[0] if available else None,
                              'last_available':available[-1] if available else None,'missing_inside_span':missing_inside,
                              'inventory':inv,'samples':samples}
    return result

def select_premium_kind():
    candidates=['premiumIndexKlines','premiumPriceKlines']
    scores={}
    for kind in candidates:
        score=0
        for s in SYMBOLS:
            for mo in ['2020-02','2023-01','2026-08']:
                if probe(monthly_url(kind,s,mo))['exists']:score+=1
        scores[kind]=score
    best=max(scores,key=scores.get)
    return best,scores

def metrics_inventory_and_samples():
    all_days=list(days())
    out={'symbols':{}}
    for s in SYMBOLS:
        def one(d):
            u=metric_url(s,d); p=probe(u); return d,u,p
        inv=[]
        with ThreadPoolExecutor(max_workers=32) as ex:
            futs=[ex.submit(one,d) for d in all_days]
            for f in as_completed(futs):
                d,u,p=f.result(); inv.append({'date':d,'url':u,**p})
        inv.sort(key=lambda x:x['date'])
        avail=[x['date'] for x in inv if x['exists']]
        missing=[]
        if avail:
            aset=set(avail); d=datetime.fromisoformat(avail[0]).date(); e=datetime.fromisoformat(avail[-1]).date()
            while d<=e:
                if d.isoformat() not in aset:missing.append(d.isoformat())
                d+=timedelta(days=1)
        sample_dates=[]
        for d in [avail[0] if avail else None,'2023-09-12','2024-02-16','2025-07-22','2026-06-24','2026-06-25','2026-06-26','2026-08-31',avail[-1] if avail else None]:
            if d and d in set(avail) and d not in sample_dates:sample_dates.append(d)
        samples={}
        for d in sample_dates:
            u=metric_url(s,d); rec={'date':d,'url':u}
            try:
                b=fetch(u); rec['checksum']=checksum(u,b); h,rr=unzip_rows(b)
                rec['audit']=audit_time_rows(h,rr,300000,('create_time','create time','timestamp','time'))
            except Exception as e:rec['error']=repr(e)
            samples[d]=rec
        out['symbols'][s]={'available_days':len(avail),'first_available':avail[0] if avail else None,'last_available':avail[-1] if avail else None,
                           'missing_days_inside_span':missing,'inventory':inv,'samples':samples}
    return out

def main():
    premium,scores=select_premium_kind()
    report={'generated_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
            'scope':'XRPUSDT/BTCUSDT USD-M derivative archive audit through 2026-08',
            'premium_path_probe':scores,'selected_premium_family':premium,'families':{}}
    for kind in ['fundingRate','markPriceKlines','indexPriceKlines',premium]:
        print('AUDIT',kind,flush=True); report['families'][kind]=audit_monthly_family(kind)
    print('AUDIT metrics inventory',flush=True); report['metrics']=metrics_inventory_and_samples()

    out=Path('audit-output'); out.mkdir(exist_ok=True)
    (out/'XRP_BTC_DERIVATIVES_AUDIT_V1.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

    lines=['# XRP + BTC Derivatives Historical Audit V1','',f"Generated: {report['generated_utc']}",'',
           f"Premium archive family selected: `{premium}` (probe scores {scores})",'','## Monthly families','',
           '| Family | Symbol | Available months | First | Last | Missing months inside span |','|---|---|---:|---|---|---:|']
    review=False
    for kind,fam in report['families'].items():
        for s,v in fam['symbols'].items():
            lines.append(f"| {kind} | {s} | {v['available_months']} | {v['first_available']} | {v['last_available']} | {len(v['missing_inside_span'])} |")
            if v['missing_inside_span']:review=True
            for mo,rec in v['samples'].items():
                if rec.get('error') or not rec.get('checksum',{}).get('ok'):review=True
                a=rec.get('audit',{})
                if kind!='fundingRate' and any(a.get(k,0) for k in ['duplicates','nonmonotonic','offgrid','gap_count','bad_time']):review=True
    lines+=['','## Metrics daily archive','',
            '| Symbol | Available days | First | Last | Missing days inside span |','|---|---:|---|---|---:|']
    for s,v in report['metrics']['symbols'].items():
        lines.append(f"| {s} | {v['available_days']} | {v['first_available']} | {v['last_available']} | {len(v['missing_days_inside_span'])} |")
        if v['missing_days_inside_span']:review=True
    lines+=['','### Metrics controlled-date checks','']
    for s,v in report['metrics']['symbols'].items():
        lines.append(f'#### {s}')
        for d,rec in v['samples'].items():
            if rec.get('error'):
                lines.append(f"- {d}: ERROR {rec['error']}");review=True;continue
            a=rec['audit']; ok=rec['checksum']['ok'] and not any(a.get(k,0) for k in ['duplicates','nonmonotonic','offgrid','gap_count','bad_time'])
            lines.append(f"- {d}: checksum={'PASS' if rec['checksum']['ok'] else 'FAIL'} rows={a.get('rows')} range={a.get('first_iso')}→{a.get('last_iso')} dup={a.get('duplicates')} gaps={a.get('gap_count')} offgrid={a.get('offgrid')} => {'PASS' if ok else 'REVIEW'}")
            if not ok:review=True
        lines.append('')
    lines+=['## Provisional result','', '**REVIEW_REQUIRED**' if review else '**PASS_COVERAGE_AND_SAMPLES**','',
            'This audit establishes archive coverage and controlled integrity samples. A dataset with known sparse metrics may still be usable with explicit missingness, but no gap may be interpolated as observed information.',
            '']
    (out/'XRP_BTC_DERIVATIVES_AUDIT_V1.md').write_text('\n'.join(lines),encoding='utf-8')
    print('\n'.join(lines),flush=True)

if __name__=='__main__':
    main()
