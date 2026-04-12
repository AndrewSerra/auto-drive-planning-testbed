from __future__ import annotations

import heapq
import math
import time
from typing import TypeAlias

from .types import (
    Config, PlanPoint, Obstacles,
    _SearchNode, _ACTIONS,
    _heuristic, _direction_angle, _validate_config,
)

SafeInterval: TypeAlias = tuple[float, float]  # [t_start, t_end); t_end may be math.inf
_SippState: TypeAlias = tuple[int, int, int]   # (row, col, interval_index)


def plan(
    start: Config,
    goal: Config,
    grid_size: tuple[int, int],
    obstacles: Obstacles,
    dynamic_obstacles: list[list[PlanPoint]],
    *,
    cell_travel_time_s: float = 1.0,
    start_time: float | None = None,
) -> list[PlanPoint]:
    """Compute a collision-free path from start to goal using SIPP.

    Extends A* to handle dynamic obstacles (other agents with known planned
    paths). Each grid cell is assigned safe intervals — contiguous time windows
    during which it is unoccupied. The search state is (row, col, safe_interval_index),
    and g(state) is the actual arrival timestamp rather than a step count.

    An agent blocks its current cell for the duration between consecutive
    PlanPoints and occupies its final cell indefinitely.

    Args:
        start:                 Starting Config (row, col, angle).
        goal:                  Goal Config (row, col, angle).
        grid_size:             (num_rows, num_cols) from TestbedConfig.grid_size.
        obstacles:             Set of statically blocked (row, col) cells.
        dynamic_obstacles:     List of other agents' planned paths. Each path is
                               a list[PlanPoint] as returned by a_star.plan().
        cell_travel_time_s:    Seconds per grid cell traversal (default 1.0).
        start_time:            Unix timestamp for the first PlanPoint. Defaults
                               to time.time() at call time.

    Returns:
        Ordered list of PlanPoints from start to goal (inclusive). Timestamps
        reflect actual arrival times including any waiting. Returns [] if no
        path exists or if the start cell is occupied at start_time.

    Raises:
        ValueError: If start or goal is outside the grid or inside a static obstacle.
    """
    if start_time is None:
        start_time = time.time()

    num_rows, num_cols = grid_size
    _validate_config(start, num_rows, num_cols, obstacles, "start")
    _validate_config(goal, num_rows, num_cols, obstacles, "goal")

    start_rc: _SearchNode = (start[0], start[1])
    goal_rc: _SearchNode = (goal[0], goal[1])

    safe_intervals = _build_cell_safe_intervals(grid_size, obstacles, dynamic_obstacles)

    start_si_idx = _find_interval_at_time(safe_intervals[start_rc], start_time)
    if start_si_idx is None:
        return []  # start cell is occupied at start_time

    if start_rc == goal_rc:
        return [(goal, start_time)]

    start_state: _SippState = (start_rc[0], start_rc[1], start_si_idx)

    counter = 0
    h0 = _heuristic(start_rc, goal_rc) * cell_travel_time_s
    heap: list[tuple[float, int, _SippState]] = [(start_time + h0, counter, start_state)]

    g_score: dict[_SippState, float] = {start_state: start_time}
    came_from: dict[_SippState, _SippState | None] = {start_state: None}
    arrival_times: dict[_SippState, float] = {start_state: start_time}
    closed: set[_SippState] = set()

    while heap:
        _, _, current = heapq.heappop(heap)
        row, col, si_idx = current
        g = g_score[current]

        if (row, col) == goal_rc:
            return _reconstruct_path(came_from, arrival_times, current, start, goal)

        if current in closed:
            continue
        closed.add(current)

        si_end = safe_intervals[(row, col)][si_idx][1]
        t_arrive_latest = si_end + cell_travel_time_s

        for drow, dcol, _ in _ACTIONS:
            nrow, ncol = row + drow, col + dcol

            if not (0 <= nrow < num_rows and 0 <= ncol < num_cols):
                continue

            neighbor_sis = safe_intervals[(nrow, ncol)]
            if not neighbor_sis:
                continue

            t_arrive_earliest = g + cell_travel_time_s

            for nsi_idx, t_arrive in _reachable_arrivals(
                t_arrive_earliest, t_arrive_latest, neighbor_sis
            ):
                neighbor_state: _SippState = (nrow, ncol, nsi_idx)

                if t_arrive < g_score.get(neighbor_state, math.inf):
                    g_score[neighbor_state] = t_arrive
                    came_from[neighbor_state] = current
                    arrival_times[neighbor_state] = t_arrive
                    h = _heuristic((nrow, ncol), goal_rc) * cell_travel_time_s
                    counter += 1
                    heapq.heappush(heap, (t_arrive + h, counter, neighbor_state))

    return []


def _reconstruct_path(
    came_from: dict[_SippState, _SippState | None],
    arrival_times: dict[_SippState, float],
    goal_state: _SippState,
    start: Config,
    goal: Config,
) -> list[PlanPoint]:
    path: list[_SippState] = []
    state: _SippState | None = goal_state
    while state is not None:
        path.append(state)
        state = came_from[state]
    path.reverse()

    result: list[PlanPoint] = []
    for i, state in enumerate(path):
        row, col, _ = state
        if i == 0:
            angle = start[2]
        elif i == len(path) - 1:
            angle = goal[2]
        else:
            prev_row, prev_col, _ = path[i - 1]
            angle = _direction_angle((prev_row, prev_col), (row, col))

        config: Config = (row, col, angle)
        result.append((config, arrival_times[state]))

    return result


def _build_cell_safe_intervals(
    grid_size: tuple[int, int],
    obstacles: Obstacles,
    dynamic_obstacles: list[list[PlanPoint]],
) -> dict[tuple[int, int], list[SafeInterval]]:
    num_rows, num_cols = grid_size

    collision: dict[tuple[int, int], list[SafeInterval]] = {}
    for path in dynamic_obstacles:
        for i, (cfg, t_arrive) in enumerate(path):
            row, col, _ = cfg
            t_depart = path[i + 1][1] if i + 1 < len(path) else math.inf
            collision.setdefault((row, col), []).append((t_arrive, t_depart))

    safe: dict[tuple[int, int], list[SafeInterval]] = {}
    for row in range(num_rows):
        for col in range(num_cols):
            cell = (row, col)
            if cell in obstacles:
                safe[cell] = []
            else:
                safe[cell] = _complement(collision.get(cell, []))

    return safe


def _complement(collision_intervals: list[SafeInterval]) -> list[SafeInterval]:
    """Return the safe intervals as the complement of the collision intervals."""
    if not collision_intervals:
        return [(0.0, math.inf)]

    merged: list[SafeInterval] = []
    for interval in sorted(collision_intervals):
        if merged and interval[0] <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], interval[1]))
        else:
            merged.append(interval)

    safe: list[SafeInterval] = []
    t = 0.0
    for c_start, c_end in merged:
        if t < c_start:
            safe.append((t, c_start))
        t = c_end
        if t == math.inf:
            return safe
    safe.append((t, math.inf))
    return safe


def _find_interval_at_time(
    safe_intervals: list[SafeInterval],
    t: float,
) -> int | None:
    """Return the index of the safe interval containing t, or None."""
    for idx, (si_start, si_end) in enumerate(safe_intervals):
        if si_start <= t < si_end:
            return idx
    return None


def _reachable_arrivals(
    t_arrive_earliest: float,
    t_arrive_latest: float,
    safe_intervals: list[SafeInterval],
) -> list[tuple[int, float]]:
    """Return (si_idx, earliest_arrival) for every reachable safe interval.

    Safe intervals are sorted and non-overlapping, so iteration stops as soon
    as an interval starts after t_arrive_latest.
    """
    results: list[tuple[int, float]] = []
    for idx, (si_start, si_end) in enumerate(safe_intervals):
        if t_arrive_earliest >= si_end:
            continue
        if si_start > t_arrive_latest:
            break
        t_arrive = max(t_arrive_earliest, si_start)
        results.append((idx, t_arrive))
    return results
