from __future__ import annotations

import logging
import math
import time
from queue import SimpleQueue
from threading import Event

from typing import Protocol

from camera.agent_tracking import DetectedChange
from config.testbed_config import AgentConfig
from control.field_state import FieldState
from notifier.model import CarCommandMessage
from planner import sipp
from planner.types import Config, Obstacles, PlanPoint

_logger = logging.getLogger("testbed")


class _PlannerConfig(Protocol):
    @property
    def agents(self) -> list[AgentConfig]: ...
    @property
    def grid_size(self) -> tuple[int, int]: ...


def _heading_error(current: float, target: float) -> float:
    """Signed shortest-path heading error in [-180, 180]. Inputs in [0, 360)."""
    return (target - current + 180) % 360 - 180


class Controller:

    def __init__(
        self,
        detection_q: SimpleQueue,
        notifier_q: SimpleQueue,
        config: _PlannerConfig,
        obstacles: Obstacles,
        field_state: FieldState,
        stop_event: Event,
        cell_travel_time_s: float = 1.0,
    ) -> None:
        self._detection_q = detection_q
        self._notifier_q = notifier_q
        self._config = config
        self._obstacles = obstacles
        self._field_state = field_state
        self._stop_event = stop_event
        self._cell_travel_time_s = cell_travel_time_s

        self._agent_sinks: dict[str, tuple[int, int]] = {
            agent.aid: agent.sink for agent in config.agents
        }
        self._cached_plans: dict[str, list[PlanPoint]] = {}

    def run(self) -> None:
        while not self._stop_event.is_set():
            if self._detection_q.empty():
                time.sleep(0.05)
                continue

            change: DetectedChange = self._detection_q.get()
            self._notifier_q.put(change)  # forward to display clients

            car_id = change.car_id
            row, col, angle = change.grid_row, change.grid_col, change.angle
            self._field_state.update(car_id, row, col, angle)

            if car_id not in self._agent_sinks:
                _logger.warning(f"No sink configured for '{car_id}', skipping planning")
                continue

            sink = self._agent_sinks[car_id]
            cardinal_angle = round(angle / 90) * 90 % 360
            start: Config = (row, col, cardinal_angle)
            goal: Config = (sink[0], sink[1], 0)

            dynamic_obstacles = [
                self._cached_plans[oid]
                for oid in self._cached_plans
                if oid != car_id and self._cached_plans[oid]
            ]

            plan = sipp.plan(
                start=start,
                goal=goal,
                grid_size=self._config.grid_size,
                obstacles=self._obstacles,
                dynamic_obstacles=dynamic_obstacles,
                cell_travel_time_s=self._cell_travel_time_s,
            )

            if not plan:
                _logger.warning(f"No plan found for '{car_id}'")
                self._cached_plans[car_id] = []
                continue

            self._cached_plans[car_id] = plan

            if len(plan) < 2:
                self._notifier_q.put(
                    CarCommandMessage(car_id=car_id, forward=False, steering=0.0)
                )
                continue

            next_row, next_col, _ = plan[1][0]
            dr = next_row - row
            dc = next_col - col
            target_heading = math.degrees(math.atan2(-dr, dc)) % 360

            err = _heading_error(angle, target_heading)
            steering = max(-1.0, min(1.0, err / 90.0))

            _logger.info(
                f"{car_id}: heading={angle:.1f}° target={target_heading:.1f}° "
                f"err={err:.1f}° steering={steering:.2f}"
            )

            self._notifier_q.put(
                CarCommandMessage(car_id=car_id, forward=True, steering=steering)
            )
