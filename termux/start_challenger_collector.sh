#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$HERE/logs"
PID_FILE="$HERE/challenger_collector.pid"
mkdir -p "$LOG_DIR"

if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    echo "XRP Challenger collector ya está corriendo PID=$PID"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

if [ ! -f "$HERE/challenger_activation.json" ]; then
  echo "BLOQUEADO: falta $HERE/challenger_activation.json"
  echo "Usa challenger_activation.example.json solo después de verificar deployment pre-start."
  exit 2
fi

cd "$HERE/.."
nohup python -u termux/xrp_challenger_collector.py   >> "$LOG_DIR/challenger_stdout.log" 2>&1 &
PID=$!
echo "$PID" > "$PID_FILE"
sleep 2
if ! kill -0 "$PID" 2>/dev/null; then
  echo "El collector Challenger terminó durante el arranque."
  tail -n 80 "$LOG_DIR/challenger_stdout.log" || true
  rm -f "$PID_FILE"
  exit 1
fi
echo "XRP Challenger collector iniciado PID=$PID"
