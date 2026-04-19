from threading import Lock


class FieldState:
    def __init__(self) -> None:
        self._lock = Lock()
        self._states: dict[str, tuple[int, int, float]] = {}  # car_id -> (row, col, angle)

    def update(self, car_id: str, row: int, col: int, angle: float) -> None:
        with self._lock:
            self._states[car_id] = (row, col, angle)

    def get(self, car_id: str) -> tuple[int, int, float] | None:
        with self._lock:
            return self._states.get(car_id)

    def snapshot(self) -> dict[str, tuple[int, int, float]]:
        with self._lock:
            return dict(self._states)
