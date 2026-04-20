"""
Simulated car client: connects to the sim server, registers, and receives
CarCommandMessage. Mirrors the behavior of the real car (car.ino).

Usage:
    python -m car-sim.sim          # uses CAR_ID = "car_1"
"""
import logging
import signal
from threading import Event

from websockets.sync.client import connect
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

from notifier.model import AgentRegistrationMessage, CarCommandMessage, ResponseMessage

_logger = logging.getLogger("car-sim")

CAR_ID = "1"
SERVER_URL = "ws://localhost:8765"


def run(stop_event: Event) -> None:
    _logger.info(f"[{CAR_ID}] Connecting to {SERVER_URL}")
    try:
        with connect(SERVER_URL) as ws:
            ws.send(AgentRegistrationMessage(id=CAR_ID).model_dump_json())
            resp = ResponseMessage.model_validate_json(ws.recv())
            if not resp.is_success:
                _logger.error(f"[{CAR_ID}] Registration failed: {resp.message}")
                return

            _logger.info(f"[{CAR_ID}] Registered. Waiting for commands...")

            while not stop_event.is_set():
                raw = ws.recv()
                cmd = CarCommandMessage.model_validate_json(raw)
                if cmd.car_id != CAR_ID:
                    continue
                _logger.info(
                    f"[{CAR_ID}] CMD forward={cmd.forward} steering={cmd.steering:+.2f}"
                )

    except (ConnectionClosedOK, ConnectionClosedError) as e:
        _logger.info(f"[{CAR_ID}] Disconnected: {e}")


def main() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    stop_event = Event()
    signal.signal(signal.SIGINT, lambda _s, _f: stop_event.set())
    signal.signal(signal.SIGTERM, lambda _s, _f: stop_event.set())

    run(stop_event)


if __name__ == "__main__":
    main()
