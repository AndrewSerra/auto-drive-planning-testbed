"""
Simulation server: replaces the camera + agent tracker.

Generates DetectedChange for each car moving toward its goal (as if seen by a
camera), feeds the Controller, and broadcasts CarCommandMessage to connected
sim.py car clients via WebSocket.

Usage:
    python -m car-sim.server config.json
"""
import asyncio
import logging
import math
import random
import signal
import sys
import time
from queue import SimpleQueue
from threading import Event, Thread

from camera.agent_tracking import DetectedChange
from config.testbed_config import TestbedConfig
from control.control import Controller
from control.field_state import FieldState
from notifier.server import NotifierServer
from planner.types import Obstacles

_logger = logging.getLogger("car-sim-server")

TICK_S = 1.0  # seconds between position updates — matches cell_travel_time_s


class _SimCar:
    def __init__(self, aid: str, row: int, col: int, sink_row: int, sink_col: int) -> None:
        self.aid = aid
        self.row = row
        self.col = col
        self._sink_row = sink_row
        self._sink_col = sink_col

    @property
    def at_goal(self) -> bool:
        return self.row == self._sink_row and self.col == self._sink_col

    def reset(self, num_rows: int, num_cols: int) -> None:
        self.row = random.randint(0, num_rows - 1)
        self.col = random.randint(0, num_cols - 1)

    def step(self) -> tuple[int, int, float] | None:
        """Move one cell toward sink. Returns (new_row, new_col, angle) or None if at goal."""
        dr = self._sink_row - self.row
        dc = self._sink_col - self.col
        if dr == 0 and dc == 0:
            return None

        if abs(dr) >= abs(dc):
            step_dr = 1 if dr > 0 else -1
            step_dc = 0
        else:
            step_dr = 0
            step_dc = 1 if dc > 0 else -1

        self.row += step_dr
        self.col += step_dc
        angle = math.degrees(math.atan2(-step_dr, step_dc)) % 360
        return self.row, self.col, angle


def _to_world(val: int, total: int) -> float:
    return (val / (total - 1)) * 100.0 - 50.0


def _sim_loop(cars: list[_SimCar], detection_q: SimpleQueue, stop_event: Event, num_rows: int, num_cols: int) -> None:
    # Report initial positions to bootstrap planning
    for car in cars:
        detection_q.put(DetectedChange(
            car_id=car.aid,
            pos_x=_to_world(car.col, num_cols),
            pos_y=_to_world(car.row, num_rows),
            grid_row=car.row,
            grid_col=car.col,
            angle=0.0,
        ))

    while not stop_event.is_set():
        time.sleep(TICK_S)
        for car in cars:
            result = car.step()
            if result is None:
                car.reset(num_rows, num_cols)
                continue
            new_row, new_col, angle = result
            detection_q.put(DetectedChange(
                car_id=car.aid,
                pos_x=_to_world(new_col, num_cols),
                pos_y=_to_world(new_row, num_rows),
                grid_row=new_row,
                grid_col=new_col,
                angle=angle,
            ))
            _logger.debug(f"[{car.aid}] ({new_row}, {new_col}) angle={angle:.1f}°")


def main() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    config_path = sys.argv[1] if len(sys.argv) > 1 else ""
    cfg = TestbedConfig(config_path)
    num_rows, num_cols = cfg.grid_size
    _logger.info(f"Grid {num_rows}x{num_cols}, {len(cfg.agents)} agent(s)")

    stop_event = Event()
    signal.signal(signal.SIGINT, lambda _s, _f: stop_event.set())
    signal.signal(signal.SIGTERM, lambda _s, _f: stop_event.set())

    static_obstacles: Obstacles = frozenset(
        (row, col) for row, col in cfg.static_obstacles
    )

    sim_cars = [
        _SimCar(
            aid=a.aid,
            row=random.randint(0, num_rows - 1),
            col=random.randint(0, num_cols - 1),
            sink_row=a.sink[0],
            sink_col=a.sink[1],
        )
        for a in cfg.agents
    ]
    for car in sim_cars:
        _logger.info(f"[{car.aid}] start=({car.row},{car.col}) sink=({car._sink_row},{car._sink_col})")

    detection_q: SimpleQueue = SimpleQueue()
    notifier_q: SimpleQueue = SimpleQueue()
    field_state = FieldState()

    controller = Controller(
        detection_q=detection_q,
        notifier_q=notifier_q,
        config=cfg,
        obstacles=static_obstacles,
        field_state=field_state,
        stop_event=stop_event,
        cell_travel_time_s=TICK_S,
    )
    notifier_server = NotifierServer(queue=notifier_q, stop_event=stop_event, num_rows=num_rows, num_cols=num_cols)

    threads = [
        Thread(target=lambda: asyncio.run(notifier_server.run_server())),
        Thread(target=controller.run),
        Thread(target=_sim_loop, args=(sim_cars, detection_q, stop_event, num_rows, num_cols)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
