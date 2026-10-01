#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$HERE/challenger_collector.pid"
echo "=== XRP Challenger Collector ==="
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
[ -f "$HERE/challenger_activation.json" ] && echo "activation=present" || echo "activation=missing"
[ -f "$HERE/challenger_runtime.json" ] && echo "runtime_marker=present" || echo "runtime_marker=missing"
[ -f "$HERE/challenger_forward_state.json" ] && echo "state=present" || echo "state=missing"
echo "--- latest log ---"
tail -n 25 "$HERE/logs/challenger_collector.log" 2>/dev/null || true
tail -n 25 "$HERE/logs/challenger_stdout.log" 2>/dev/null || true
