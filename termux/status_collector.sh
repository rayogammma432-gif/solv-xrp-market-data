#!/data/data/com.termux/files/usr/bin/bash
set -u
BASE="$HOME/solv-xrp-market-data/termux"
PIDFILE="$BASE/collector.pid"
if [ -f "$PIDFILE" ]; then
  PID="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [ -n "${PID:-}" ] && kill -0 "$PID" 2>/dev/null; then
    echo "ACTIVO - PID=$PID"
    tail -n 12 "$BASE/logs/collector.log" 2>/dev/null || true
    exit 0
  fi
fi
echo "DETENIDO"
exit 1
