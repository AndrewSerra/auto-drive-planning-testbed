import cv2 as cv
import numpy as np
import logging
from queue import SimpleQueue
from dataclasses import dataclass
from typing import Optional
from pydantic import BaseModel
from threading import Event

_logger = logging.getLogger("testbed")


class DetectedChange(BaseModel):
    car_id: str
    pos_x: float
    pos_y: float
    is_inbounds: bool

@dataclass
class AgentDetection:
    pos_x: float
    pos_y: float

    def __init__(self, pos_x: float, pos_y: float) -> None:
        self.pos_x = pos_x
        self.pos_y = pos_y

    def change_mag(self, detection: 'AgentDetection') -> float:
        diff_x = self.pos_x - detection.pos_x
        diff_y = self.pos_y - detection.pos_y
        return np.sqrt(diff_x ** 2 + diff_y ** 2)

class MotionVec:
    magnitude: float
    angle: float

    def __init__(self, prev_detection: AgentDetection, next_detection: AgentDetection) -> None:
        delta_x = next_detection.pos_x - prev_detection.pos_x
        delta_y = -1 * (next_detection.pos_y - prev_detection.pos_y)

        self.magnitude = np.sqrt(delta_x ** 2 + delta_y ** 2)
        self.angle = np.degrees(np.arctan2(delta_y, delta_x))

    def __str__(self) -> str:
        return f"{self.magnitude} at {self.angle} deg"

class PositionTrack:

    _detections: list[AgentDetection]
    _curr_vec: Optional[MotionVec]
    _has_significant_change: bool

    _SIG_MAG_CHANGE_THRESH: float = 1.0

    def __init__(self, init_detection: AgentDetection) -> None:
        self._detections = [init_detection]
        self._curr_vec = None
        self._has_significant_change = True

    def update(self, detection: AgentDetection) -> None:
        prev = self._detections[-1]
        self._detections.append(detection)
        change_magnitude = prev.change_mag(detection)
        self._has_significant_change = change_magnitude >= self._SIG_MAG_CHANGE_THRESH
        self._curr_vec = MotionVec(prev, detection)

    @property
    def vector(self) -> Optional[MotionVec]:
        return self._curr_vec

    @property
    def has_significant_change(self) -> bool:
        return self._has_significant_change

    @property
    def position(self) -> tuple[float, float]:
        detection = self._detections[-1]
        return detection.pos_x, detection.pos_y

class AgentTracker:

    _cam: cv.VideoCapture
    _output_queue: SimpleQueue | None

    _H: np.ndarray
    _stop_event: Event

    _motion_vec_lookup: dict[str, PositionTrack]

    def __init__(self, H: np.ndarray, stop_event: Event, output_queue: SimpleQueue | None = None) -> None:
        assert H.shape == (3,3), f"incorrect shape for H {H.shape}, expected (3,3)"

        self._cam = cv.VideoCapture(0)

        if not self._cam.isOpened():
            raise Exception("cannot open camera feed")

        self._output_queue = output_queue
        self._H = H
        self._stop_event = stop_event
        self._motion_vec_lookup: dict[str, PositionTrack] = {}

    def _get_april_tag_center(self, tag: np.ndarray) -> np.ndarray:
        assert tag.shape == (4, 2), f"tag shape expected (4, 2), received {tag.shape}"
        # Calculate center of tag
        m1, b1 = np.polyfit([tag[0][0], tag[2][0]], [tag[0][1], tag[2][1]], 1)
        m2, b2 = np.polyfit([tag[1][0], tag[3][0]], [tag[1][1], tag[3][1]], 1)

        x = (b1 - b2) / (m2 - m1)
        y = (m2 * b1 - m1 * b2) / (m2 - m1)

        return np.array([x, y, 1])
    
    def _draw_motion_vec(self, frame: np.ndarray, detection: AgentDetection, vec: MotionVec) -> None:
        start = (int(detection.pos_x), int(detection.pos_y))
        angle_rad = np.radians(vec.angle)
        # Flip y back to image coords (y increases downward)
        end_x = int(detection.pos_x + vec.magnitude * np.cos(angle_rad))
        end_y = int(detection.pos_y - vec.magnitude * np.sin(angle_rad))
        cv.arrowedLine(frame, start, (end_x, end_y), (0, 255, 0), 2, tipLength=0.3)

    def _update_motion_tracker(self, car_id: str, detection: AgentDetection) -> None:
        if car_id not in self._motion_vec_lookup:
            self._motion_vec_lookup[car_id] = PositionTrack(detection)
        else:
            self._motion_vec_lookup[car_id].update(detection)

    def start_tracking(self) -> None:
        detector_params = cv.aruco.DetectorParameters()
        predef_dict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_APRILTAG_16h5)
        detector = cv.aruco.ArucoDetector(predef_dict, detector_params)

        while True:
            if self._stop_event.is_set():
                break

            ret, frame = self._cam.read()

            if not ret:
                break

            corners, ids, _ = detector.detectMarkers(frame)

            # TODO: Remove after debugging
            # if ids is not None:
            #     cv.aruco.drawDetectedMarkers(frame, corners, ids)

            if ids is None:
                # cv.imshow('Camera Feed', frame)
                # if cv.waitKey(1) == ord('q'):
                #     self._cam.release()
                #     cv.destroyAllWindows()
                #     break
                continue

            # Remove wrapper dimension
            corners_unwrap, ids_unwrap = corners[0], ids[0]
            centers = [self._get_april_tag_center(tag) for tag in corners_unwrap]

            for i in range(len(ids_unwrap)):
                car_id = ids_unwrap[i]
                p = self._H @ centers[i]
                self._update_motion_tracker(
                    car_id,
                    AgentDetection(
                        pos_x=p[0] / p[2],
                        pos_y=p[1] / p[2],
                    )
                )

                if self._motion_vec_lookup[car_id].has_significant_change:
                    _logger.info(f"Detected significant movement in car {car_id}.")
                    pos_tracker_car = self._motion_vec_lookup[car_id]
                    x, y = pos_tracker_car.position

                    self._output_queue.put(
                        DetectedChange(
                            car_id=str(car_id),
                            pos_x=x,
                            pos_y=y,
                            is_inbounds=True
                        )
                    )
                # vec = self._motion_vec_lookup[ids_unwrap[i]].vector
                # if vec is not None:
                #     self._draw_motion_vec(frame, AgentDetection(centers[i][0], centers[i][1]), vec)

            # cv.imshow('Camera Feed', frame)
            # if cv.waitKey(1) == ord('q'):
            #     self._cam.release()
            #     cv.destroyAllWindows()
            #     break


if __name__ == "__main__":
    AgentTracker(np.array([
        [1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0]
    ])).start_tracking()
