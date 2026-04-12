from __future__ import annotations

from typing import TypeAlias

import numpy as np

XPoint: TypeAlias = int  # Grid col index
YPoint: TypeAlias = int  # Grid row index
Angle: TypeAlias = int   # Heading in degrees: 0=East, 90=North, 180=West, 270=South
Config: TypeAlias = tuple[YPoint, XPoint, Angle]  # (row, col, angle)
PlanPoint: TypeAlias = tuple[Config, float]        # (agent state, unix timestamp)

Obstacles: TypeAlias = frozenset[tuple[int, int]]       # blocked (row, col) cells
GridSpacing: TypeAlias = tuple[np.ndarray, np.ndarray]  # (horizontal_space, vertical_space)

_SearchNode: TypeAlias = tuple[int, int]  # (row, col) — internal use only

# (drow, dcol, result_angle): 4-directional actions
_ACTIONS: list[tuple[int, int, int]] = [
    (-1,  0, 90),   # North: row decreases
    ( 1,  0, 270),  # South: row increases
    ( 0,  1, 0),    # East:  col increases
    ( 0, -1, 180),  # West:  col decreases
]


def _heuristic(node: _SearchNode, goal: _SearchNode) -> float:
    return abs(node[0] - goal[0]) + abs(node[1] - goal[1])


def _direction_angle(from_node: _SearchNode, to_node: _SearchNode) -> Angle:
    drow = to_node[0] - from_node[0]
    dcol = to_node[1] - from_node[1]
    for action_drow, action_dcol, angle in _ACTIONS:
        if drow == action_drow and dcol == action_dcol:
            return angle
    raise ValueError(f"non-adjacent nodes: {from_node} -> {to_node}")


def _validate_config(
    cfg: Config,
    num_rows: int,
    num_cols: int,
    obstacles: Obstacles,
    label: str,
) -> None:
    row, col, _ = cfg
    if not (0 <= row < num_rows and 0 <= col < num_cols):
        raise ValueError(
            f"{label} ({row}, {col}) is outside grid bounds "
            f"(num_rows={num_rows}, num_cols={num_cols})"
        )
    if (row, col) in obstacles:
        raise ValueError(f"{label} ({row}, {col}) is inside an obstacle")
