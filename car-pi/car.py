import json
import signal
import sys
import time
from pathlib import Path

import websocket
from gpiozero import Device, Servo
from gpiozero.pins.lgpio import LGPIOFactory

Device.pin_factory = LGPIOFactory()

STEERING_PIN = 18
ESC_PIN = 19
ESC_NEUTRAL = 0.0
ESC_FORWARD = 0.044
ESC_BACKWARD = -0.033

# Match Arduino Servo library pulse widths so ESC calibration is preserved
_MIN_PW = 544e-6
_MAX_PW = 2400e-6

CONFIG_FILE = Path(__file__).parent / "config.json"

cfg = json.loads(CONFIG_FILE.read_text())
WS_HOST = cfg["ws_host"]
WS_PORT = cfg["ws_port"]
CAR_ID = str(cfg["car_id"])

steering_servo = Servo(STEERING_PIN, min_pulse_width=_MIN_PW, max_pulse_width=_MAX_PW)
esc = Servo(ESC_PIN, min_pulse_width=_MIN_PW, max_pulse_width=_MAX_PW)

CONNECTING = "CONNECTING"
OPERATING = "OPERATING"
ERROR = "ERROR"
state = CONNECTING


def drive_stop():
    esc.value = ESC_NEUTRAL


def drive_forward():
    esc.value = ESC_FORWARD


def steer(value: float):
    steering_servo.value = max(-1.0, min(1.0, value))


def handle_command(data: dict):
    if str(data.get("car_id")) != CAR_ID:
        return
    forward = data.get("forward", False)
    steering = float(data.get("steering", 0.0))
    steer(steering)
    if forward:
        drive_forward()
    else:
        drive_stop()
    print(f"[CMD] forward={forward} steering={steering:.2f}")


def on_open(ws):
    global state
    state = CONNECTING
    print(f"[WS] Connected. Registering as car {CAR_ID}.")
    ws.send(json.dumps({"id": CAR_ID, "connection_type": "agent"}))


def on_message(ws, message):
    global state
    print(f"[WS] Message: {message}")
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        return

    if "is_success" in data:
        if data["is_success"]:
            state = OPERATING
            print("[WS] Registration successful. Operating.")
        else:
            state = ERROR
            print(f"[WS] Registration rejected: {data.get('message')}")
    elif "forward" in data and state == OPERATING:
        handle_command(data)


def on_error(ws, error):
    global state
    print(f"[WS] Error: {error}")
    state = ERROR


def on_close(ws, close_status_code, close_msg):
    global state
    print("[WS] Disconnected.")
    state = CONNECTING


def _shutdown(sig, frame):
    print("\n[Boot] Shutting down.")
    drive_stop()
    sys.exit(0)


signal.signal(signal.SIGINT, _shutdown)
signal.signal(signal.SIGTERM, _shutdown)

drive_stop()
print("[Boot] Car system starting.")
print("[Boot] Steering self-test: left → right → center")
steer(-1.0)
time.sleep(0.5)
steer(1.0)
time.sleep(0.5)
steer(0.0)

while True:
    state = CONNECTING
    ws = websocket.WebSocketApp(
        f"ws://{WS_HOST}:{WS_PORT}/",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    ws.run_forever()
    delay = 5 if state == ERROR else 1
    print(f"[WS] Reconnecting in {delay}s...")
    time.sleep(delay)
