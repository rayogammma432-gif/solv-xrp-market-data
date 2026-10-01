# XRP Challenger Deployment Gate V1

## Purpose

This is the final local gate before enabling the independent XRP Challenger V3.1 collector.

It does not change research rules.

Frozen forward start:
- `2026-10-01T06:00:00Z`

## Required order

1. Motorola pulls the exact validated deployment commit.
2. Deploy `apps-script/XRP_Challenger_Receptor.gs` as a **separate** Apps Script Web App.
3. Set its Script Property:
   - `CHALLENGER_SHARED_SECRET`
4. Put the dedicated web-app URL and secret in local `termux/config.json` under:
   - `challenger.web_app_url`
   - `challenger.shared_secret`
5. Do not reuse CURRENT's XRP URL or secret.
6. Run:
   - `python termux/challenger_deployment_gate.py`
7. The gate must report:
   - `PASS_DEPLOYMENT_GATE`
   - receptor revision `XRP_RECEPTOR_CHALLENGER_V1_R2`
   - workbook ID `14mVe2XXcsVBCojZSbp6A7qQKO2RFpovLtKntOYFDwvA`
   - exact current Git SHA
8. If that passes, run:
   - `python termux/challenger_deployment_gate.py --write-activation`
9. Then start:
   - `bash termux/start_challenger_collector.sh`
10. Verify:
   - `bash termux/status_challenger_collector.sh`

## Fail-closed conditions

The gate refuses activation when:
- fewer than 10 minutes remain before the frozen start;
- tracked repository files are dirty;
- Challenger URL equals CURRENT URL;
- Challenger secret equals CURRENT secret;
- placeholders remain in config;
- receptor revision is wrong;
- receptor storage ID is wrong;
- generated activation fails the collector's own activation validator;
- an activation file already exists.

If any of these occurs after the safe deployment window:
- do **not** backfill V3.1 as prospective;
- create a new forward version/start.

## Scientific boundary

Passing this deployment gate does not authorize trading.

The collector remains:
- shadow research only;
- no orders;
- no SIGNALS;
- no Telegram trade alerts.

The 2026 historical holdout remains locked.
