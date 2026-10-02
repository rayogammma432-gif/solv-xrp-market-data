#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$HERE/challenger_v2_collector.pid"
ACTIVATION="$HERE/challenger_v2_activation.json"
RUNTIME="$HERE/challenger_v2_runtime.json"
STATE="$HERE/challenger_v2_forward_state.json"
HEARTBEAT="$HERE/challenger_v2_heartbeat.json"
echo "=== XRP Challenger Collector V2 ==="
if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    echo "status=RUNNING pid=$PID"
  else
    echo "status=STALE_PID"
  fi
else
  echo "status=STOPPED"
fi
[ -f "$ACTIVATION" ] && echo "activation_v2=present" || echo "activation_v2=missing"
[ -f "$RUNTIME" ] && echo "runtime_v2=present" || echo "runtime_v2=missing"
[ -f "$STATE" ] && echo "state_v2=present" || echo "state_v2=missing"
if [ -f "$HEARTBEAT" ]; then
  python - "$HEARTBEAT" <<'PY'
import json, sys
from datetime import datetime, timezone
p=sys.argv[1]
d=json.load(open(p, encoding="utf-8"))
ts=d.get("heartbeat_utc")
age="unknown"
try:
    dt=datetime.fromisoformat(str(ts).replace("Z","+00:00"))
    age=max(0,int((datetime.now(timezone.utc)-dt).total_seconds()))
except Exception:
    pass
print("heartbeat_v2=present")
print("phase="+str(d.get("phase","UNKNOWN")))
print("heartbeat_utc="+str(ts))
print("heartbeat_age_seconds="+str(age))
print("formal_start_utc="+str(d.get("formal_start_utc","")))
if d.get("error"):
    print("heartbeat_error="+str(d.get("error")))
PY
else
  echo "heartbeat_v2=missing"
fi
echo "--- current V2 log only ---"
tail -n 25 "$HERE/logs/challenger_v2_collector.log" 2>/dev/null || true
tail -n 25 "$HERE/logs/challenger_v2_stdout.log" 2>/dev/null || true
