from __future__ import annotations
import argparse, calendar, csv, hashlib, io, json, math, os, urllib.error, urllib.request, zipfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

BASE='https://data.binance.vision/data/futures/um/monthly'
COLS=['open_time','open','high','low','close','volume','close_time','quote_volume','trades','taker_buy_base','taker_buy_quote','ignore']
NUMERIC=['open','high','low','close','volume','quote_volume','taker_buy_base','taker_buy_quote']

@dataclass
class FileProbe:
    symbol:str; interval:str; month:str; url:str; exists:bool; status:Optional[int]; size:Optional[int]; error:Optional[str]=None

def url(symbol, interval, month, checksum=False):
    name=f'{symbol}-{interval}-{month}.zip'
    if checksum: name += '.CHECKSUM'
    return f'{BASE}/klines/{symbol}/{interval}/{name}'

def request(u, method='GET', timeout=30):
    req=urllib.request.Request(u, method=method, headers={'User-Agent':'solv-xrp-historical-audit/1.0'})
    return urllib.request.urlopen(req, timeout=timeout)

def probe(symbol, interval, month):
    u=url(symbol,interval,month)
    try:
        with request(u,'HEAD',20) as r:
            return FileProbe(symbol,interval,month,u,True,getattr(r,'status',200),int(r.headers.get('Content-Length') or 0) or None)
    except urllib.error.HTTPError as e:
        return FileProbe(symbol,interval,month,u,False,e.code,None,str(e))
    except Exception:
        try:
            req=urllib.request.Request(u,headers={'Range':'bytes=0-0','User-Agent':'solv-xrp-historical-audit/1.0'})
            with urllib.request.urlopen(req,timeout=20) as r:
                return FileProbe(symbol,interval,month,u,True,getattr(r,'status',200),int(r.headers.get('Content-Length') or 0) or None)
        except urllib.error.HTTPError as e2:
            return FileProbe(symbol,interval,month,u,False,e2.code,None,str(e2))
        except Exception as e2:
            return FileProbe(symbol,interval,month,u,False,None,None,repr(e2))

def fetch_bytes(u):
    with request(u,'GET',120) as r: return r.read()

def verify_checksum(zip_bytes, checksum_bytes, expected_name):
    txt=checksum_bytes.decode('utf-8','replace').strip().splitlines()[0]
    expected=txt.split()[0].lower()
    actual=hashlib.sha256(zip_bytes).hexdigest().lower()
    return {'expected':expected,'actual':actual,'ok':expected==actual,'line':txt,'filename_matches':expected_name in txt}

def read_zip_csv(blob):
    z=zipfile.ZipFile(io.BytesIO(blob))
    names=[n for n in z.namelist() if n.lower().endswith('.csv')]
    if not names: raise RuntimeError('zip has no csv')
    with z.open(names[0]) as f:
        text=io.TextIOWrapper(f,encoding='utf-8',newline='')
        rows=list(csv.reader(text))
    if rows and rows[0] and not rows[0][0].lstrip('-').isdigit(): rows=rows[1:]
    return rows

def normalize_rows(rows):
    out=[]
    for idx,r in enumerate(rows,1):
        if len(r)<12: continue
        try:
            d=dict(zip(COLS,r[:12]))
            d['open_time']=int(d['open_time']); d['close_time']=int(d['close_time']); d['trades']=int(float(d['trades']))
            for c in NUMERIC: d[c]=float(d[c])
            out.append(d)
        except Exception as e:
            raise RuntimeError(f'bad row {idx}: {r[:4]} {e}')
    return out

def audit_1m(rows, month):
    times=[r['open_time'] for r in rows]
    dup=len(times)-len(set(times))
    offgrid=sum(1 for t in times if t%60000!=0)
    nonmono=sum(1 for a,b in zip(times,times[1:]) if b<=a)
    gaps=[]
    for a,b in zip(times,times[1:]):
        if b-a!=60000: gaps.append({'from':a,'to':b,'delta_min':(b-a)/60000})
    bad_ohlc=0; bad_vol=0; bad_close_time=0
    for r in rows:
        if r['high'] < max(r['open'],r['close'],r['low']) or r['low'] > min(r['open'],r['close'],r['high']): bad_ohlc+=1
        if r['volume']<0 or r['quote_volume']<0 or r['taker_buy_base']<0 or r['taker_buy_quote']<0: bad_vol+=1
        if r['close_time'] < r['open_time']: bad_close_time+=1
    y,m=map(int,month.split('-')); expected=calendar.monthrange(y,m)[1]*1440
    return {'rows':len(rows),'expected_full_month_rows':expected,'row_delta_vs_full_month':len(rows)-expected,'first_open_time':times[0] if times else None,'last_open_time':times[-1] if times else None,'duplicates':dup,'offgrid':offgrid,'nonmonotonic':nonmono,'gap_count':len(gaps),'gap_examples':gaps[:20],'bad_ohlc':bad_ohlc,'bad_volume':bad_vol,'bad_close_time':bad_close_time}

def aggregate(rows, interval_min):
    bucket_ms=interval_min*60000; groups={}
    for r in rows:
        b=(r['open_time']//bucket_ms)*bucket_ms
        g=groups.get(b)
        if g is None:
            groups[b]={'open_time':b,'open':r['open'],'high':r['high'],'low':r['low'],'close':r['close'],'volume':r['volume'],'quote_volume':r['quote_volume'],'trades':r['trades'],'taker_buy_base':r['taker_buy_base'],'taker_buy_quote':r['taker_buy_quote'],'n':1}
        else:
            g['high']=max(g['high'],r['high']); g['low']=min(g['low'],r['low']); g['close']=r['close']
            g['volume']+=r['volume']; g['quote_volume']+=r['quote_volume']; g['trades']+=r['trades']
            g['taker_buy_base']+=r['taker_buy_base']; g['taker_buy_quote']+=r['taker_buy_quote']; g['n']+=1
    return [groups[k] for k in sorted(groups)]

def compare_native(one_min_rows, native_rows, interval_min, tol=1e-8):
    agg={r['open_time']:r for r in aggregate(one_min_rows,interval_min) if r['n']==interval_min}
    nat={r['open_time']:r for r in native_rows}
    common=sorted(set(agg)&set(nat)); mismatches=[]
    fields=['open','high','low','close','volume','quote_volume','taker_buy_base','taker_buy_quote']
    for t in common:
        bad={}
        for f in fields:
            a=agg[t][f]; b=nat[t][f]
            if not math.isclose(a,b,rel_tol=1e-9,abs_tol=tol): bad[f]={'resampled':a,'native':b,'diff':a-b}
        if agg[t]['trades']!=nat[t]['trades']: bad['trades']={'resampled':agg[t]['trades'],'native':nat[t]['trades']}
        if bad and len(mismatches)<20: mismatches.append({'open_time':t,'fields':bad})
    return {'resampled_complete_bars':len(agg),'native_bars':len(nat),'common_bars':len(common),'missing_in_native':len(set(agg)-set(nat)),'missing_in_resampled':len(set(nat)-set(agg)),'mismatch_count_sampled':len(mismatches),'mismatch_examples':mismatches,'all_common_match':len(mismatches)==0}

def month_range(start,end):
    y,m=map(int,start.split('-')); ey,em=map(int,end.split('-'))
    while (y,m)<=(ey,em):
        yield f'{y:04d}-{m:02d}'
        m+=1
        if m==13: y+=1; m=1

def dt(ms):
    return datetime.fromtimestamp(ms/1000,tz=timezone.utc).isoformat().replace('+00:00','Z') if ms is not None else None

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',default='historical/audit/XRP_BTC_DATA_AUDIT_V1.json'); args=ap.parse_args()
    inventory=[]; end='2026-08'
    for s in ['XRPUSDT','BTCUSDT']:
        for mo in month_range('2020-01',end): inventory.append(asdict(probe(s,'1m',mo)))
    samples={}; sample_months=['2020-02','2026-08']; tf_map={'5m':5,'15m':15,'1h':60,'4h':240}
    for s in ['XRPUSDT','BTCUSDT']:
        samples[s]={}
        for mo in sample_months:
            item={'month':mo}
            try:
                zu=url(s,'1m',mo); zb=fetch_bytes(zu); cb=fetch_bytes(url(s,'1m',mo,True))
                item['checksum']=verify_checksum(zb,cb,os.path.basename(zu))
                rows=normalize_rows(read_zip_csv(zb)); qa=audit_1m(rows,mo)
                qa['first_open_iso']=dt(qa['first_open_time']); qa['last_open_iso']=dt(qa['last_open_time']); item['audit_1m']=qa
                item['resample_validation']={}
                for tf,mins in tf_map.items():
                    nz=fetch_bytes(url(s,tf,mo)); nc=fetch_bytes(url(s,tf,mo,True))
                    chk=verify_checksum(nz,nc,os.path.basename(url(s,tf,mo)))
                    item['resample_validation'][tf]={'checksum':chk,'comparison':compare_native(rows,normalize_rows(read_zip_csv(nz)),mins)}
            except Exception as e:
                item['error']=repr(e)
            samples[s][mo]=item
    inv_summary={}
    for s in ['XRPUSDT','BTCUSDT']:
        rows=[x for x in inventory if x['symbol']==s]; missing=[x['month'] for x in rows if not x['exists']]
        inv_summary[s]={'months_checked':len(rows),'months_available':sum(x['exists'] for x in rows),'months_missing':missing,'first_available':next((x['month'] for x in rows if x['exists']),None),'last_available':next((x['month'] for x in reversed(rows) if x['exists']),None)}
    report={'generated_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'scope':'XRPUSDT + BTCUSDT USD-M Futures 1m through 2026-08','inventory_summary':inv_summary,'inventory':inventory,'samples':samples}
    out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    md=out.with_suffix('.md')
    lines=['# XRP + BTC Historical Data Audit V1','',f"Generated: {report['generated_utc']}",'','## Inventory','', '| Symbol | Months checked | Available | Missing | First | Last |','|---|---:|---:|---:|---|---|']
    for s,v in inv_summary.items(): lines.append(f"| {s} | {v['months_checked']} | {v['months_available']} | {len(v['months_missing'])} | {v['first_available']} | {v['last_available']} |")
    lines += ['','## Controlled samples','']; overall=True
    for s in samples:
        for mo,it in samples[s].items():
            lines += [f'### {s} {mo}']
            if 'error' in it:
                lines += [f"- ERROR: `{it['error']}`",'']; overall=False; continue
            q=it['audit_1m']; c=it['checksum']
            lines += [f"- checksum: {'PASS' if c['ok'] else 'FAIL'}",f"- rows: {q['rows']} (full-month expected {q['expected_full_month_rows']})",f"- range: {q['first_open_iso']} → {q['last_open_iso']}",f"- duplicates: {q['duplicates']}; gaps: {q['gap_count']}; off-grid: {q['offgrid']}; bad OHLC: {q['bad_ohlc']}; bad volume: {q['bad_volume']}"]
            if not c['ok'] or any(q[k] for k in ['duplicates','gap_count','offgrid','bad_ohlc','bad_volume','nonmonotonic']): overall=False
            for tf,rv in it['resample_validation'].items():
                cp=rv['comparison']; ok=rv['checksum']['ok'] and cp['all_common_match'] and cp['missing_in_native']==0 and cp['missing_in_resampled']==0
                lines.append(f"- resample {tf}: {'PASS' if ok else 'REVIEW'}; common={cp['common_bars']}, missing native={cp['missing_in_native']}, missing resampled={cp['missing_in_resampled']}, sampled mismatches={cp['mismatch_count_sampled']}")
                if not ok: overall=False
            lines.append('')
    lines += ['## Provisional result','', '**PASS_SAMPLE**' if overall else '**REVIEW_REQUIRED**','', 'This report validates a controlled sample and monthly-file availability inventory. It is not yet a full row-by-row audit of every historical month.']
    md.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(md.read_text())

if __name__=='__main__': main()
