#!/data/data/com.termux/files/usr/bin/bash
set -u
BASE="$HOME/solv-xrp-market-data/termux"
PIDFILE="$BASE/collector.pid"
mkdir -p "$BASE/logs"

if [ -f "$PIDFILE" ]; then
  PID="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [ -n "${PID:-}" ] && kill -0 "$PID" 2>/dev/null; then
    echo "Collector ya está activo. PID=$PID"
    exit 0
  fi
  rm -f "$PIDFILE"
fi

termux-wake-lock >/dev/null 2>&1 || true
cd "$BASE"
nohup python scheduler.py >> "$BASE/logs/scheduler.out" 2>&1 &
PID=$!
echo "$PID" > "$PIDFILE"
echo "Collector iniciado. PID=$PID"
echo "Log: $BASE/logs/collector.log"
