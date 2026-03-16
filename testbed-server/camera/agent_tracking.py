import cv2 as cv
import numpy as np
from queue import SimpleQueue
from dataclasses import dataclass
from typing import Optional

@dataclass
class AgentDetection:
    pos_x: int
    pos_y: int

    def __init__(self, pos_x: int, pos_y: int) -> None:
        self.pos_x = pos_x
        self.pos_y = pos_y

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

    def __init__(self, init_detection: AgentDetection) -> None:
        self._detections = [init_detection]
        self._curr_vec = None

    def update(self, detection: AgentDetection) -> None:
        prev = self._detections[-1]
        self._detections.append(detection)
        self._curr_vec = MotionVec(prev, detection)

    @property
    def vector(self) -> Optional[MotionVec]:
        return self._curr_vec

class AgentTracker:

    _cam: cv.VideoCapture
    _output_queue: SimpleQueue | None

    _motion_vec_lookup: dict[str, PositionTrack]

    def __init__(self, H: np.ndarray, output_queue: SimpleQueue | None = None) -> None:
        assert H.shape == (3,3), f"incorrect shape for H {H.shape}, expected (3,3)"

        self._cam = cv.VideoCapture(0)

        if not self._cam.isOpened():
            raise Exception("cannot open camera feed")

        self._output_queue = output_queue
        self._motion_vec_lookup = {}

    def _get_april_tag_center(self, tag: np.ndarray) -> np.ndarray:
        assert tag.shape == (4, 2), f"tag shape expected (4, 2), received {tag.shape}"
        # Calculate center of tag
        m1, b1 = np.polyfit([tag[0][0], tag[2][0]], [tag[0][1], tag[2][1]], 1)
        m2, b2 = np.polyfit([tag[1][0], tag[3][0]], [tag[1][1], tag[3][1]], 1)

        x = (b1 - b2) / (m2 - m1)
        y = (m2 * b1 - m1 * b2) / (m2 - m1)

        return np.array([x, y])
    
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
            ret, frame = self._cam.read()

            if not ret:
                break

            corners, ids, _ = detector.detectMarkers(frame)

            # TODO: Remove after debugging
            if ids is not None:
                cv.aruco.drawDetectedMarkers(frame, corners, ids)

            if ids is None:
                cv.imshow('Camera Feed', frame)
                if cv.waitKey(1) == ord('q'):
                    self._cam.release()
                    cv.destroyAllWindows()
                    break
                continue

            # Remove wrapper dimension
            corners_unwrap, ids_unwrap = corners[0], ids[0]
            centers = [self._get_april_tag_center(tag) for tag in corners_unwrap]

            for i in range(len(ids_unwrap)):
                self._update_motion_tracker(
                    ids_unwrap[i],
                    AgentDetection(
                        pos_x=centers[i][0],
                        pos_y=centers[i][1],
                    )
                )
                vec = self._motion_vec_lookup[ids_unwrap[i]].vector
                if vec is not None:
                    self._draw_motion_vec(frame, AgentDetection(centers[i][0], centers[i][1]), vec)

            cv.imshow('Camera Feed', frame)
            if cv.waitKey(1) == ord('q'):
                self._cam.release()
                cv.destroyAllWindows()
                break


if __name__ == "__main__":
    AgentTracker(np.array([
        [1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0]
    ])).start_tracking()
