#!/data/data/com.termux/files/usr/bin/bash
set -u
BASE="$HOME/solv-xrp-market-data/termux"
PIDFILE="$BASE/collector.pid"

if [ ! -f "$PIDFILE" ]; then
  echo "No hay PID registrado."
  termux-wake-unlock >/dev/null 2>&1 || true
  exit 0
fi

PID="$(cat "$PIDFILE" 2>/dev/null || true)"
if [ -n "${PID:-}" ] && kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  sleep 1
  echo "Collector detenido. PID=$PID"
else
  echo "El proceso ya no estaba activo."
fi
rm -f "$PIDFILE"
termux-wake-unlock >/dev/null 2>&1 || true
