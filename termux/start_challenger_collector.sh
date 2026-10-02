#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$HERE/logs"
PID_FILE="$HERE/challenger_collector.pid"
READY_FILE="$HERE/challenger_ready.json"
HEARTBEAT_FILE="$HERE/challenger_heartbeat.json"
mkdir -p "$LOG_DIR"

if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    echo "BLOQUEADO: ya existe un proceso Challenger vivo PID=$PID"
    python "$HERE/xrp_challenger_collector.py" --status-json || true
    exit 2
  fi
  rm -f "$PID_FILE"
fi

if [ ! -f "$HERE/challenger_activation.json" ]; then
  echo "BLOQUEADO: falta $HERE/challenger_activation.json"
  echo "Ejecuta primero el deployment gate V3.2 con --write-activation."
  exit 2
fi

rm -f "$READY_FILE" "$HEARTBEAT_FILE"

cd "$HERE/.."
nohup python -u termux/xrp_challenger_collector.py \
  >> "$LOG_DIR/challenger_stdout.log" 2>&1 &
PID=$!
echo "$PID" > "$PID_FILE"

# PID vivo no significa READY. Esperamos el handshake completo:
# activation + runtime marker + receptor recovery + ready marker.
for _ in $(seq 1 120); do
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "FALLO: el proceso Challenger termino antes de quedar READY."
    tail -n 80 "$LOG_DIR/challenger_stdout.log" 2>/dev/null || true
    rm -f "$PID_FILE" "$READY_FILE"
    exit 1
  fi

  STATUS_JSON="$(python termux/xrp_challenger_collector.py --status-json 2>/dev/null || true)"
  if printf '%s\n' "$STATUS_JSON" | grep -q '"status": "RUNNING_READY"'; then
    echo "XRP Challenger RUNNING_READY PID=$PID"
    printf '%s\n' "$STATUS_JSON"
    exit 0
  fi
  sleep 1
done

echo "FALLO: timeout esperando RUNNING_READY; se detiene para evitar estado ambiguo."
kill "$PID" 2>/dev/null || true
sleep 1
kill -9 "$PID" 2>/dev/null || true
rm -f "$PID_FILE" "$READY_FILE"
tail -n 80 "$LOG_DIR/challenger_stdout.log" 2>/dev/null || true
exit 1
