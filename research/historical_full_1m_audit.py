from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from historical_data_audit import url, fetch_bytes, verify_checksum, read_zip_csv, normalize_rows, audit_1m, month_range, dt

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',default='audit-output/XRP_BTC_FULL_1M_AUDIT_V1.json')
    args=ap.parse_args()
    symbols=['XRPUSDT','BTCUSDT']
    report={'generated_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'range':'2020-01..2026-08','symbols':{}}
    global_pass=True

    for symbol in symbols:
        months=[]
        prev_last=None
        totals={'months':0,'checksum_failures':0,'download_errors':0,'rows':0,'duplicates':0,'offgrid':0,'nonmonotonic':0,'internal_gaps':0,'cross_month_gaps':0,'bad_ohlc':0,'bad_volume':0,'bad_close_time':0,'unexpected_row_count_months':[]}
        first_ts=None; last_ts=None
        for month in month_range('2020-01','2026-08'):
            rec={'month':month}
            try:
                zu=url(symbol,'1m',month)
                zb=fetch_bytes(zu); cb=fetch_bytes(url(symbol,'1m',month,True))
                chk=verify_checksum(zb,cb,os.path.basename(zu)); rec['checksum']=chk
                if not chk['ok']: totals['checksum_failures']+=1; global_pass=False
                rows=normalize_rows(read_zip_csv(zb)); qa=audit_1m(rows,month)
                rec['audit']=qa
                if rows:
                    cur_first=rows[0]['open_time']; cur_last=rows[-1]['open_time']
                    rec['first_open_iso']=dt(cur_first); rec['last_open_iso']=dt(cur_last)
                    if first_ts is None: first_ts=cur_first
                    last_ts=cur_last
                    if prev_last is not None and cur_first-prev_last!=60000:
                        rec['cross_month_gap_from_prev_minutes']=(cur_first-prev_last)/60000
                        totals['cross_month_gaps']+=1; global_pass=False
                    prev_last=cur_last
                totals['rows']+=qa['rows']; totals['duplicates']+=qa['duplicates']; totals['offgrid']+=qa['offgrid']
                totals['nonmonotonic']+=qa['nonmonotonic']; totals['internal_gaps']+=qa['gap_count']; totals['bad_ohlc']+=qa['bad_ohlc']
                totals['bad_volume']+=qa['bad_volume']; totals['bad_close_time']+=qa['bad_close_time']
                # XRP Jan-2020 is listing month and may be intentionally partial.
                allowed_partial=(symbol=='XRPUSDT' and month=='2020-01')
                if qa['rows']!=qa['expected_full_month_rows'] and not allowed_partial:
                    totals['unexpected_row_count_months'].append({'month':month,'rows':qa['rows'],'expected':qa['expected_full_month_rows']})
                    global_pass=False
                if any(qa[k] for k in ['duplicates','offgrid','nonmonotonic','gap_count','bad_ohlc','bad_volume','bad_close_time']):
                    global_pass=False
            except Exception as e:
                rec['error']=repr(e); totals['download_errors']+=1; global_pass=False
            totals['months']+=1; months.append(rec)
            print(symbol,month,'OK' if 'error' not in rec else 'ERROR',flush=True)
        report['symbols'][symbol]={'summary':totals,'first_open_iso':dt(first_ts),'last_open_iso':dt(last_ts),'months':months}

    report['result']='PASS_FULL_1M' if global_pass else 'REVIEW_REQUIRED'
    out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    md=out.with_suffix('.md')
    lines=['# XRP + BTC Full 1m Historical Audit V1','',f"Generated: {report['generated_utc']}",f"Result: **{report['result']}**",'',
           '| Symbol | Months | Rows | Checksum failures | Download errors | Internal gaps | Cross-month gaps | Duplicates | Off-grid | Bad OHLC | Bad volume | Unexpected row-count months |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for s in symbols:
        v=report['symbols'][s]; q=v['summary']
        lines.append(f"| {s} | {q['months']} | {q['rows']} | {q['checksum_failures']} | {q['download_errors']} | {q['internal_gaps']} | {q['cross_month_gaps']} | {q['duplicates']} | {q['offgrid']} | {q['bad_ohlc']} | {q['bad_volume']} | {len(q['unexpected_row_count_months'])} |")
        lines += ['',f"## {s}",f"- range: {v['first_open_iso']} → {v['last_open_iso']}",f"- unexpected row-count months: `{q['unexpected_row_count_months']}`",'']
    lines += ['## Interpretation','',
              '- XRPUSDT 2020-01 is treated as a permitted partial listing month.',
              '- Every later month is expected to contain a complete 1-minute UTC grid.',
              '- No missing interval is interpolated or repaired by this audit.',
              '- This audit validates the canonical 1m layer only; derivative metrics (OI/funding/ratios) remain a separate audit.','']
    md.write_text('\n'.join(lines),encoding='utf-8')
    print(md.read_text(),flush=True)

if __name__=='__main__':
    main()
