#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$HERE/.."
LOG_DIR="$HERE/logs"
PID_FILE="$HERE/challenger_v2_collector.pid"
STDOUT_LOG="$LOG_DIR/challenger_v2_stdout.log"
ACTIVATION="$HERE/challenger_v2_activation.json"
RUNTIME="$HERE/challenger_v2_runtime.json"
HEARTBEAT="$HERE/challenger_v2_heartbeat.json"
mkdir -p "$LOG_DIR"

if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    echo "XRP Challenger V2 ya está corriendo PID=$PID"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

if [ ! -f "$ACTIVATION" ]; then
  echo "BLOQUEADO: falta $ACTIVATION"
  echo "Ejecuta primero: python termux/challenger_deployment_gate_v2.py --write-activation"
  exit 2
fi

cd "$ROOT"
echo "== V2 preflight =="
python termux/xrp_challenger_collector_v2.py --prelaunch-check --check-receptor

rm -f "$HEARTBEAT"
nohup python -u termux/xrp_challenger_collector_v2.py >> "$STDOUT_LOG" 2>&1 &
PID=$!
echo "$PID" > "$PID_FILE"

for _ in $(seq 1 20); do
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "BLOQUEADO: Challenger V2 terminó durante el arranque."
    tail -n 80 "$STDOUT_LOG" || true
    rm -f "$PID_FILE"
    exit 1
  fi
  if [ -f "$RUNTIME" ] && [ -f "$HEARTBEAT" ]; then
    PHASE="$(python -c 'import json; print(json.load(open("termux/challenger_v2_heartbeat.json")).get("phase","UNKNOWN"))')"
    echo "XRP Challenger V2 iniciado PID=$PID phase=$PHASE"
    exit 0
  fi
  sleep 1
done

echo "BLOQUEADO: proceso vivo pero no creó runtime marker + heartbeat en 20s."
tail -n 80 "$STDOUT_LOG" || true
kill "$PID" 2>/dev/null || true
rm -f "$PID_FILE"
exit 1
