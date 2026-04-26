#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 <hostname> <password> <car_id>"
  exit 1
fi

HOST="$1"
PASSWORD="$2"
CAR_ID="$3"
WS_HOST="192.168.1.160"
WS_PORT=8765
REMOTE_DIR="~/auto-planning-software-testbed/car-pi"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

SSH="sshpass -p $PASSWORD ssh -o StrictHostKeyChecking=no pi@$HOST"
SCP="sshpass -p $PASSWORD scp -o StrictHostKeyChecking=no"

echo "[deploy] Creating remote directory..."
$SSH "mkdir -p $REMOTE_DIR"

echo "[deploy] Copying car.py..."
$SCP "$SCRIPT_DIR/car.py" "pi@$HOST:$REMOTE_DIR/car.py"

echo "[deploy] Writing config.json..."
$SSH "cat > $REMOTE_DIR/config.json" <<EOF
{
  "ws_host": "$WS_HOST",
  "ws_port": $WS_PORT,
  "car_id": "$CAR_ID"
}
EOF

echo "[deploy] Ensuring uv is installed..."
$SSH 'command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh'

echo "[deploy] Setting up Python environment..."
$SSH "cd $REMOTE_DIR && ~/.local/bin/uv init --bare 2>/dev/null || true && ~/.local/bin/uv add websocket-client gpiozero"

echo ""
echo "[deploy] Done. To run the car:"
echo "  ssh pi@$HOST"
echo "  cd $REMOTE_DIR && uv run python car.py"
echo ""
echo "[deploy] Note: if gpiozero raises a pin factory error, run on the Pi:"
echo "  sudo apt install python3-lgpio"
