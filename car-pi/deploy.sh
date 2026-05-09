#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "Usage: $0 <pi-username> <pi-hostname> <pi-password> <car_id>"
  exit 1
fi

PI_USERNAME="$1"
PI_HOST="$2"
PI_PASSWORD="$3"
CAR_ID="$4"
WS_HOST="pop-os"
WS_PORT=8765
REMOTE_DIR="~/auto-planning-software-testbed"
SCRIPT_DIR=$(realpath "$(dirname "$0")")

SSH="sshpass -p $PI_PASSWORD ssh -o StrictHostKeyChecking=no $PI_USERNAME@$PI_HOST"
SCP="sshpass -p $PI_PASSWORD scp -o StrictHostKeyChecking=no"

echo "[deploy] Creating remote directory..."
$SSH "mkdir -p $REMOTE_DIR"

echo "[deploy] Copying car.py..."
$SCP "$SCRIPT_DIR/car.py" "$PI_USERNAME@$PI_HOST:$REMOTE_DIR/car.py"

echo "[deploy] Writing config.json..."
$SSH "cat > $REMOTE_DIR/config.json" <<EOF
{
  "ws_host": "$WS_HOST",
  "ws_port": $WS_PORT,
  "car_id": "$CAR_ID"
}
EOF

echo "[deploy] Installing system dependencies..."
$SSH "sudo apt install -y python3-lgpio swig python3.13-dev liblgpio-dev"

echo "[deploy] Ensuring uv is installed..."
$SSH 'command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh'

echo "[deploy] Setting up Python environment..."
$SSH "cd $REMOTE_DIR && ~/.local/bin/uv init --bare 2>/dev/null || true && ~/.local/bin/uv add websocket-client gpiozero lgpio"

echo ""
echo "[deploy] Done. To run the car:"
echo "  ssh $PI_USERNAME@$PI_HOST"
echo "  cd $REMOTE_DIR && uv run python car.py"
echo ""
