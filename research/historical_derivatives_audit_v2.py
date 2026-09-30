from __future__ import annotations
import csv, hashlib, io, json, os, urllib.parse, urllib.request, xml.etree.ElementTree as ET, zipfile
from datetime import datetime, timezone
from pathlib import Path

BUCKET='https://s3-ap-northeast-1.amazonaws.com/data.binance.vision'
DATA='https://data.binance.vision/'
SYMBOLS=['XRPUSDT','BTCUSDT']
START_MONTH='2020-01'; END_MONTH='2026-08'
UA='solv-xrp-derivatives-audit/2.0'

def fetch(url,timeout=120):
    req=urllib.request.Request(url,headers={'User-Agent':UA})
    with urllib.request.urlopen(req,timeout=timeout) as r:return r.read()

def list_keys(prefix):
    keys=[]; token=None
    while True:
        params={'list-type':'2','prefix':prefix,'max-keys':'1000'}
        if token:params['continuation-token']=token
        u=BUCKET+'?'+urllib.parse.urlencode(params)
        root=ET.fromstring(fetch(u))
        ns={'s3':'http://s3.amazonaws.com/doc/2006-03-01/'}
        for c in root.findall('s3:Contents',ns):
            k=c.find('s3:Key',ns)
            if k is not None and k.text:keys.append(k.text)
        trunc=(root.findtext('s3:IsTruncated',default='false',namespaces=ns).lower()=='true')
        if not trunc:break
        token=root.findtext('s3:NextContinuationToken',default=None,namespaces=ns)
        if not token:raise RuntimeError('truncated S3 listing without continuation token')
    return keys

def check(blob,url):
    line=fetch(url+'.CHECKSUM').decode('utf-8','replace').strip().splitlines()[0]
    exp=line.split()[0].lower(); act=hashlib.sha256(blob).hexdigest().lower()
    return {'ok':exp==act,'expected':exp,'actual':act,'line':line}

def unzip_rows(blob):
    z=zipfile.ZipFile(io.BytesIO(blob)); names=[n for n in z.namelist() if n.lower().endswith('.csv')]
    if not names:raise RuntimeError('no csv')
    with z.open(names[0]) as f:rr=list(csv.reader(io.TextIOWrapper(f,encoding='utf-8-sig',newline='')))
    header=None
    if rr:
        try:float(rr[0][0])
        except:header=rr.pop(0)
    return header,rr

def iso_ms(v):
    try:return datetime.fromtimestamp(int(float(v))/1000,tz=timezone.utc).isoformat().replace('+00:00','Z')
    except:return None

def audit_ts(header,rows,step=None,candidates=()):
    if not rows:return {'rows':0,'header':header,'error':'empty'}
    ix=0
    if header:
        hh=[x.strip().lower() for x in header]
        for c in candidates:
            if c.lower() in hh:ix=hh.index(c.lower());break
    vals=[];bad=0
    for r in rows:
        try:vals.append(int(float(r[ix])))
        except:bad+=1
    dup=len(vals)-len(set(vals)); nonmono=sum(b<=a for a,b in zip(vals,vals[1:]))
    gaps=[];off=0
    if step:
        off=sum(v%step!=0 for v in vals)
        gaps=[(a,b) for a,b in zip(vals,vals[1:]) if b-a!=step]
    return {'rows':len(rows),'header':header,'time_col_index':ix,'first_iso':iso_ms(vals[0]) if vals else None,'last_iso':iso_ms(vals[-1]) if vals else None,
            'bad_time':bad,'duplicates':dup,'nonmonotonic':nonmono,'offgrid':off,'gap_count':len(gaps),
            'gap_examples':[{'from':iso_ms(a),'to':iso_ms(b),'delta_ms':b-a} for a,b in gaps[:12]]}

def in_month_range(name):
    import re
    m=re.search(r'(20\d\d-\d\d)\.zip$',name)
    return m.group(1) if m and START_MONTH<=m.group(1)<=END_MONTH else None

def monthly_family(kind,symbol,interval=None):
    prefix=f'data/futures/um/monthly/{kind}/{symbol}/'
    if interval:prefix+=f'{interval}/'
    keys=list_keys(prefix)
    z=[k for k in keys if k.endswith('.zip')]
    rows=[]
    for k in z:
        mo=in_month_range(k)
        if mo:rows.append((mo,k))
    rows.sort()
    return rows,keys

def sample_zip(key,kind):
    u=DATA+key;blob=fetch(u);h,rr=unzip_rows(blob)
    a=audit_ts(h,rr,None if kind=='fundingRate' else 60000,('calc_time','fundingtime','funding_time','open_time','open time'))
    return {'key':key,'checksum':check(blob,u),'audit':a}

def expected_months():
    y,m=map(int,START_MONTH.split('-'));ey,em=map(int,END_MONTH.split('-'));a=[]
    while (y,m)<=(ey,em):
        a.append(f'{y:04d}-{m:02d}');m+=1
        if m==13:y+=1;m=1
    return a

def choose_samples(rows):
    av=[x[0] for x in rows];chosen=[]
    for x in ([av[0]] if av else [])+['2023-01','2026-08']+([av[-1]] if av else []):
        if x in av and x not in chosen:chosen.append(x)
    mp={m:k for m,k in rows}
    return [(m,mp[m]) for m in chosen]

def metrics(symbol):
    prefix=f'data/futures/um/daily/metrics/{symbol}/'
    keys=list_keys(prefix)
    z=sorted(k for k in keys if k.endswith('.zip'))
    dates=[]
    import re
    for k in z:
        m=re.search(r'metrics-(20\d\d-\d\d-\d\d)\.zip$',k)
        if m and '2020-01-01'<=m.group(1)<='2026-08-31':dates.append((m.group(1),k))
    aset={d for d,k in dates};missing=[]
    if dates:
        from datetime import date,timedelta
        d=date.fromisoformat(dates[0][0]);e=date.fromisoformat(dates[-1][0])
        while d<=e:
            if d.isoformat() not in aset:missing.append(d.isoformat())
            d+=timedelta(days=1)
    candidates=[]
    for d in ([dates[0][0]] if dates else [])+['2023-09-12','2024-02-16','2024-04-08','2024-05-01','2025-07-21','2025-07-22','2026-06-24','2026-06-25','2026-06-26','2026-08-31']+([dates[-1][0]] if dates else []):
        if d in aset and d not in candidates:candidates.append(d)
    mp={d:k for d,k in dates};samples={}
    for d in candidates:
        k=mp[d];u=DATA+k;rec={'key':k}
        try:
            b=fetch(u);h,rr=unzip_rows(b);rec['checksum']=check(b,u);rec['audit']=audit_ts(h,rr,300000,('create_time','create time','timestamp','time'))
        except Exception as e:rec['error']=repr(e)
        samples[d]=rec
    return {'listed_zip_days':len(dates),'first':dates[0][0] if dates else None,'last':dates[-1][0] if dates else None,'missing_days_inside_span':missing,'samples':samples,'total_objects':len(keys)}

def main():
    # Determine actual premium family by listing official objects.
    premium_scores={}
    for kind in ['premiumIndexKlines','premiumPriceKlines']:
        score=0
        for s in SYMBOLS:
            try:score+=len(monthly_family(kind,s,'1m')[0])
            except Exception:pass
        premium_scores[kind]=score
    premium=max(premium_scores,key=premium_scores.get)

    report={'generated_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'premium_probe':premium_scores,'selected_premium':premium,'families':{},'metrics':{}}
    exp=set(expected_months())
    for kind in ['fundingRate','markPriceKlines','indexPriceKlines',premium]:
        report['families'][kind]={}
        for s in SYMBOLS:
            rows,_=monthly_family(kind,s,None if kind=='fundingRate' else '1m')
            av={m for m,k in rows};first=rows[0][0] if rows else None;last=rows[-1][0] if rows else None
            span_missing=[]
            if first and last:
                span_missing=sorted(m for m in exp if first<=m<=last and m not in av)
            samples={}
            for m,k in choose_samples(rows):
                try:samples[m]=sample_zip(k,kind)
                except Exception as e:samples[m]={'key':k,'error':repr(e)}
            report['families'][kind][s]={'months':len(rows),'first':first,'last':last,'missing_inside_span':span_missing,'samples':samples}
    for s in SYMBOLS:report['metrics'][s]=metrics(s)

    out=Path('audit-output');out.mkdir(exist_ok=True)
    (out/'XRP_BTC_DERIVATIVES_AUDIT_V2.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    lines=['# XRP + BTC Derivatives Historical Audit V2','',f"Generated: {report['generated_utc']}",f"Premium family: `{premium}` — probe {premium_scores}",'',
           '## Monthly archive coverage','',
           '| Family | Symbol | Months | First | Last | Missing inside span |','|---|---|---:|---|---|---:|']
    review=False
    for kind,sv in report['families'].items():
        for s,v in sv.items():
            lines.append(f"| {kind} | {s} | {v['months']} | {v['first']} | {v['last']} | {len(v['missing_inside_span'])} |")
            if v['missing_inside_span']:review=True
            for mo,r in v['samples'].items():
                a=r.get('audit',{});c=r.get('checksum',{})
                if r.get('error') or not c.get('ok') or (kind!='fundingRate' and any(a.get(x,0) for x in ['bad_time','duplicates','nonmonotonic','offgrid','gap_count'])):review=True
    lines+=['','## Metrics archive coverage','',
            '| Symbol | Daily ZIPs | First | Last | Missing days inside span |','|---|---:|---|---|---:|']
    for s,v in report['metrics'].items():
        lines.append(f"| {s} | {v['listed_zip_days']} | {v['first']} | {v['last']} | {len(v['missing_days_inside_span'])} |")
        if v['missing_days_inside_span']:review=True
    lines+=['','## Metrics controlled samples','']
    for s,v in report['metrics'].items():
        lines.append(f'### {s}')
        for d,r in v['samples'].items():
            if r.get('error'):
                lines.append(f"- {d}: ERROR `{r['error']}`");review=True;continue
            a=r['audit'];ok=r['checksum']['ok'] and not any(a.get(x,0) for x in ['bad_time','duplicates','nonmonotonic','offgrid','gap_count'])
            lines.append(f"- {d}: checksum={'PASS' if r['checksum']['ok'] else 'FAIL'}, rows={a['rows']}, {a['first_iso']} → {a['last_iso']}, dup={a['duplicates']}, gaps={a['gap_count']}, offgrid={a['offgrid']} => {'PASS' if ok else 'REVIEW'}")
            if not ok:review=True
        lines.append('')
    lines+=['## Result','', '**REVIEW_REQUIRED**' if review else '**PASS_COVERAGE_AND_SAMPLES**','',
            'No missing metrics slot is treated as observed data. The 2026 create_time convention is evaluated separately before feature joins.']
    (out/'XRP_BTC_DERIVATIVES_AUDIT_V2.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines),flush=True)

if __name__=='__main__':main()
