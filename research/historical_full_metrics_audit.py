from __future__ import annotations
import csv, hashlib, io, json, urllib.parse, urllib.request, xml.etree.ElementTree as ET, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta, date
from pathlib import Path

BUCKET='https://s3-ap-northeast-1.amazonaws.com/data.binance.vision'
DATA='https://data.binance.vision/'
SYMBOLS=['XRPUSDT','BTCUSDT']
UA='solv-xrp-full-metrics-audit/1.0'
COLS=['create_time','symbol','sum_open_interest','sum_open_interest_value','count_toptrader_long_short_ratio','sum_toptrader_long_short_ratio','count_long_short_ratio','sum_taker_long_short_vol_ratio']

def fetch(u,timeout=60):
    req=urllib.request.Request(u,headers={'User-Agent':UA})
    with urllib.request.urlopen(req,timeout=timeout) as r:return r.read()

def list_keys(prefix):
    keys=[];token=None
    while True:
        p={'list-type':'2','prefix':prefix,'max-keys':'1000'}
        if token:p['continuation-token']=token
        root=ET.fromstring(fetch(BUCKET+'?'+urllib.parse.urlencode(p),120))
        ns={'s3':'http://s3.amazonaws.com/doc/2006-03-01/'}
        for c in root.findall('s3:Contents',ns):
            k=c.find('s3:Key',ns)
            if k is not None and k.text:keys.append(k.text)
        if root.findtext('s3:IsTruncated',default='false',namespaces=ns).lower()!='true':break
        token=root.findtext('s3:NextContinuationToken',default=None,namespaces=ns)
    return keys

def parse_time(x):
    dt=datetime.fromisoformat(x.strip().replace('Z','+00:00'))
    if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def process(key):
    u=DATA+key
    out={'key':key}
    try:
        b=fetch(u);line=fetch(u+'.CHECKSUM').decode('utf-8','replace').strip().splitlines()[0]
        exp=line.split()[0].lower();act=hashlib.sha256(b).hexdigest().lower();out['checksum_ok']=exp==act
        z=zipfile.ZipFile(io.BytesIO(b));n=[x for x in z.namelist() if x.endswith('.csv')][0]
        with z.open(n) as f:rr=list(csv.reader(io.TextIOWrapper(f,encoding='utf-8-sig')))
        header=[x.strip() for x in rr.pop(0)]
        h={x:i for i,x in enumerate(header)}
        file_date=key.rsplit('-',3)[-3]+'-'+key.rsplit('-',2)[-2]+'-'+key.rsplit('-',1)[-1][:2] if False else None
        import re
        m=re.search(r'metrics-(\d{4}-\d{2}-\d{2})\.zip$',key);fd=m.group(1)
        ts=[];bad=0;empty=Counter();zeros=Counter()
        rows_data=[]
        for row in rr:
            try:t=parse_time(row[h['create_time']]);ts.append(t)
            except:bad+=1;continue
            vals={}
            for col in COLS[2:]:
                v=row[h[col]].strip() if h.get(col) is not None and h[col]<len(row) else ''
                if v=='':empty[col]+=1
                else:
                    try:
                        if float(v)==0:zeros[col]+=1
                    except:pass
                vals[col]=v
            rows_data.append((t,tuple(vals[c] for c in COLS[2:])))
        secs=[int(t.timestamp()) for t in ts]
        out.update({
            'date':fd,'rows':len(rr),'bad_time':bad,'duplicates_within':len(secs)-len(set(secs)),
            'nonmonotonic':sum(b<=a for a,b in zip(secs,secs[1:])),
            'offgrid':sum((t.minute%5)!=0 or t.second!=0 or t.microsecond!=0 for t in ts),
            'out_of_file_day':sum(t.date().isoformat()!=fd for t in ts),
            'first':ts[0].isoformat().replace('+00:00','Z') if ts else None,
            'last':ts[-1].isoformat().replace('+00:00','Z') if ts else None,
            'empty':dict(empty),'zeros':dict(zeros),
            'points':[(int(t.timestamp()), vals) for t,vals in rows_data]
        })
    except Exception as e:out['error']=repr(e)
    return out

def audit_symbol(s):
    prefix=f'data/futures/um/daily/metrics/{s}/'
    keys=[k for k in list_keys(prefix) if k.endswith('.zip') and '2020-01-01'<=k[-14:-4]<='2026-08-31']
    keys.sort()
    results=[]
    with ThreadPoolExecutor(max_workers=40) as ex:
        futs={ex.submit(process,k):k for k in keys}
        for i,f in enumerate(as_completed(futs),1):
            r=f.result();results.append(r)
            if i%200==0:print(s,'files',i,'/',len(keys),flush=True)
    results.sort(key=lambda x:x.get('date',''))
    failures=[r for r in results if r.get('error') or not r.get('checksum_ok')]
    row_total=sum(r.get('rows',0) for r in results)
    bad_time=sum(r.get('bad_time',0) for r in results)
    nonmono_files=sum(bool(r.get('nonmonotonic')) for r in results)
    outofday=sum(r.get('out_of_file_day',0) for r in results)
    offgrid=sum(r.get('offgrid',0) for r in results)
    empty=Counter();zeros=Counter()
    counts=Counter();value_sets=defaultdict(set);timestamp_files=defaultdict(set)
    within_dups=0
    for r in results:
        within_dups+=r.get('duplicates_within',0)
        empty.update(r.get('empty',{}));zeros.update(r.get('zeros',{}))
        for sec,vals in r.get('points',[]):
            counts[sec]+=1;value_sets[sec].add(tuple(vals));timestamp_files[sec].add(r.get('date'))
    unique=sorted(counts)
    global_dupe_timestamps=[x for x,c in counts.items() if c>1]
    identical_duplicate_rows=sum(max(0,counts[x]-1) for x in global_dupe_timestamps if len(value_sets[x])==1)
    conflicting_duplicate_timestamps=sum(1 for x in global_dupe_timestamps if len(value_sets[x])>1)
    expected=[]
    missing=[]
    if unique:
        x=unique[0];e=unique[-1]
        us=set(unique)
        while x<=e:
            if x not in us:missing.append(x)
            x+=300
    # compress missing into runs
    runs=[]
    for x in missing:
        if not runs or x!=runs[-1][-1]+300:runs.append([x])
        else:runs[-1].append(x)
    top=sorted(runs,key=len,reverse=True)[:30]
    def iso(sec):return datetime.fromtimestamp(sec,tz=timezone.utc).isoformat().replace('+00:00','Z')
    dup_examples=[{'time':iso(x),'count':counts[x],'distinct_value_rows':len(value_sets[x]),'file_dates':sorted(timestamp_files[x])} for x in sorted(global_dupe_timestamps)[:30]]
    return {
        'files':len(keys),'first_file':results[0].get('date') if results else None,'last_file':results[-1].get('date') if results else None,
        'checksum_or_download_failures':len(failures),'failure_examples':failures[:10],
        'rows':row_total,'unique_timestamps':len(unique),'first_timestamp':iso(unique[0]) if unique else None,'last_timestamp':iso(unique[-1]) if unique else None,
        'missing_5m_timestamps':len(missing),'missing_runs':len(runs),
        'largest_missing_runs':[{'start':iso(r[0]),'end':iso(r[-1]),'slots':len(r),'minutes':len(r)*5} for r in top],
        'duplicate_timestamps_global':len(global_dupe_timestamps),'duplicate_extra_rows':row_total-len(unique),
        'identical_duplicate_extra_rows':identical_duplicate_rows,'conflicting_duplicate_timestamps':conflicting_duplicate_timestamps,
        'duplicate_examples':dup_examples,'duplicates_within_files':within_dups,'files_nonmonotonic':nonmono_files,
        'out_of_file_day_rows':outofday,'offgrid_rows':offgrid,'bad_time_rows':bad_time,
        'empty_by_column':dict(empty),'zero_by_column':dict(zeros),
        'file_anomalies':[{'date':r.get('date'),'rows':r.get('rows'),'duplicates_within':r.get('duplicates_within'),'nonmonotonic':r.get('nonmonotonic'),'out_of_file_day':r.get('out_of_file_day'),'offgrid':r.get('offgrid')} for r in results if r.get('rows')!=288 or r.get('duplicates_within') or r.get('nonmonotonic') or r.get('out_of_file_day') or r.get('offgrid')][:100]
    }

def main():
    report={'generated_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'symbols':{}}
    for s in SYMBOLS:
        print('START',s,flush=True);report['symbols'][s]=audit_symbol(s);print('DONE',s,flush=True)
    out=Path('audit-output');out.mkdir(exist_ok=True)
    (out/'XRP_BTC_FULL_METRICS_AUDIT_V1.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    lines=['# XRP + BTC Full Metrics Audit V1','',f"Generated: {report['generated_utc']}",'',
           '| Symbol | Files | Rows | Unique timestamps | Missing 5m slots | Duplicate timestamps | Nonmonotonic files | Out-of-file-day rows | Checksum/download failures |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for s,v in report['symbols'].items():
        lines.append(f"| {s} | {v['files']} | {v['rows']} | {v['unique_timestamps']} | {v['missing_5m_timestamps']} | {v['duplicate_timestamps_global']} | {v['files_nonmonotonic']} | {v['out_of_file_day_rows']} | {v['checksum_or_download_failures']} |")
        lines += ['',f'## {s}',f"- coverage: {v['first_timestamp']} → {v['last_timestamp']}",f"- largest missing runs: `{v['largest_missing_runs'][:10]}`",f"- duplicate examples: `{v['duplicate_examples'][:10]}`",f"- empty fields: `{v['empty_by_column']}`",f"- zero fields: `{v['zero_by_column']}`",'']
    (out/'XRP_BTC_FULL_METRICS_AUDIT_V1.md').write_text('\n'.join(lines),encoding='utf-8')
    print('\n'.join(lines),flush=True)

if __name__=='__main__':main()
