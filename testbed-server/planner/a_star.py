from __future__ import annotations

import heapq
import time

import cv2 as cv
import numpy as np

from .types import (
    XPoint, YPoint, Angle, Config, PlanPoint,
    Obstacles, GridSpacing, _SearchNode, _ACTIONS,
    _heuristic, _direction_angle, _validate_config,
)


def boundary_contour_to_obstacles(
    contour: np.ndarray,
    grid_spacing: GridSpacing,
    grid_size: tuple[int, int],
) -> Obstacles:
    """Convert a boundary contour to a set of blocked grid cells.

    Any grid cell whose center lies outside the contour polygon is treated as
    an obstacle. Returns frozenset() if the contour is empty (boundary
    detection failed).

    Args:
        contour:      np.ndarray of shape (N, 1, 2), output of cv.approxPolyDP.
        grid_spacing: (horizontal_space, vertical_space) pixel-position arrays
                      from the camera boundary module.
        grid_size:    (num_rows, num_cols) from TestbedConfig.grid_size.

    Returns:
        frozenset of (row_idx, col_idx) tuples for cells outside the boundary.
    """
    if contour is None or contour.size == 0:
        return frozenset()

    num_rows, num_cols = grid_size
    horizontal_space, vertical_space = grid_spacing
    blocked: set[tuple[int, int]] = set()

    for row in range(num_rows):
        cy = float((vertical_space[row] + vertical_space[row + 1]) / 2)
        for col in range(num_cols):
            cx = float((horizontal_space[col] + horizontal_space[col + 1]) / 2)
            result = cv.pointPolygonTest(contour, (cx, cy), measureDist=False)
            if result < 0:  # point is outside the contour
                blocked.add((row, col))

    return frozenset(blocked)


def plan(
    start: Config,
    goal: Config,
    grid_size: tuple[int, int],
    obstacles: Obstacles,
    *,
    cell_travel_time_s: float = 1.0,
    start_time: float | None = None,
) -> list[PlanPoint]:
    """Compute a collision-free path from start to goal using A*.

    Searches in (row, col) 2D space. Angle in Config is populated from the
    movement direction at each step; the goal angle is applied to the final
    PlanPoint.

    Args:
        start:               Starting Config (row, col, angle).
        goal:                Goal Config (row, col, angle).
        grid_size:           (num_rows, num_cols) from TestbedConfig.grid_size.
        obstacles:           Set of blocked (row, col) cells.
        cell_travel_time_s:  Seconds per grid cell traversal (default 1.0).
        start_time:          Unix timestamp for the first PlanPoint. Defaults
                             to time.time() at call time.

    Returns:
        Ordered list of PlanPoints from start to goal (inclusive). Returns []
        if no path exists.

    Raises:
        ValueError: If start or goal is outside the grid or inside an obstacle.
    """
    if start_time is None:
        start_time = time.time()

    num_rows, num_cols = grid_size
    _validate_config(start, num_rows, num_cols, obstacles, "start")
    _validate_config(goal, num_rows, num_cols, obstacles, "goal")

    start_rc: _SearchNode = (start[0], start[1])
    goal_rc: _SearchNode = (goal[0], goal[1])

    if start_rc == goal_rc:
        return [(goal, start_time)]

    counter = 0
    heap: list[tuple[float, int, _SearchNode]] = []
    heapq.heappush(heap, (_heuristic(start_rc, goal_rc), counter, start_rc))

    g_score: dict[_SearchNode, float] = {start_rc: 0.0}
    came_from: dict[_SearchNode, _SearchNode | None] = {start_rc: None}
    closed: set[_SearchNode] = set()

    while heap:
        _, _, current = heapq.heappop(heap)

        if current == goal_rc:
            return _reconstruct_path(
                came_from, current, start, goal,
                start_time, cell_travel_time_s,
            )

        if current in closed:
            continue
        closed.add(current)

        for drow, dcol, _ in _ACTIONS:
            neighbor: _SearchNode = (current[0] + drow, current[1] + dcol)
            nrow, ncol = neighbor

            if not (0 <= nrow < num_rows and 0 <= ncol < num_cols):
                continue
            if neighbor in obstacles:
                continue

            tentative_g = g_score[current] + 1.0
            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                g_score[neighbor] = tentative_g
                came_from[neighbor] = current
                f = tentative_g + _heuristic(neighbor, goal_rc)
                counter += 1
                heapq.heappush(heap, (f, counter, neighbor))

    return []


def _reconstruct_path(
    came_from: dict[_SearchNode, _SearchNode | None],
    goal_node: _SearchNode,
    start: Config,
    goal: Config,
    start_time: float,
    cell_travel_time_s: float,
) -> list[PlanPoint]:
    path: list[_SearchNode] = []
    node: _SearchNode | None = goal_node
    while node is not None:
        path.append(node)
        node = came_from[node]
    path.reverse()

    result: list[PlanPoint] = []
    for i, node in enumerate(path):
        if i == 0:
            angle = start[2]
        elif i == len(path) - 1:
            angle = goal[2]
        else:
            angle = _direction_angle(path[i - 1], node)

        config: Config = (node[0], node[1], angle)
        timestamp = start_time + i * cell_travel_time_s
        result.append((config, timestamp))

    return result
