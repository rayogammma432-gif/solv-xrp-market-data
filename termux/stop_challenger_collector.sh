#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$HERE/challenger_collector.pid"
if [ ! -f "$PID_FILE" ]; then
  echo "XRP Challenger collector no tiene PID registrado."
  exit 0
fi
PID="$(cat "$PID_FILE" 2>/dev/null || true)"
if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  for _ in 1 2 3 4 5; do
    kill -0 "$PID" 2>/dev/null || break
    sleep 1
  done
  if kill -0 "$PID" 2>/dev/null; then
    kill -9 "$PID"
  fi
fi
rm -f "$PID_FILE"
echo "XRP Challenger collector detenido."
