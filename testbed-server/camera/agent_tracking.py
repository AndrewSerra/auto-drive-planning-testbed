import time
import cv2 as cv
import numpy as np
from queue import Queue
from dataclasses import dataclass
from collections import Sequence

@dataclass(frozen=True)
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
        delta_y = next_detection.pos_y - prev_detection.pos_y

        self.magnitude = np.sqrt(delta_x ** 2, delta_y ** 2)
        self.angle = np.arctan2(delta_y, delta_x)

class PositionTrack:

    _car_id: str
    _prev_detection: AgentDetection
    _curr_vec: MotionVec

    def __init__(self, car_id: str, init_detection: AgentDetection) -> None:
        self._car_id = car_id
        self._prev_detection = init_detection

    def update_vector(self, detection: AgentDetection) -> None:
        self._curr_vec = MotionVec(self._prev_detection, detection)

class AgentTracker:

    _cam: cv.VideoCapture
    _output_queue: SimpleQueue

    _MAX_PROCESS_SIZE: int = 10

    def __init__(self, H: np.ndarray, output_queue: SimpleQueue = None) -> None:
        self._cam = cv.VideoCapture(0)

        if not self._cam.isOpened():
            raise Exception("cannot open camera feed")

        self._output_queue = output_queue

    def _determine_motion_vec(self, detections: Sequence[AgentDetection]) -> None:
        # TODO: Complete vector detection function
        pass

    def start_tracking(self) -> None:
        detector_params = cv.aruco.DetectorParameters()
        predef_dict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_APRILTAG_16h5)
        detector = cv.aruco.ArucoDetector(predef_dict, detector_params)

        processing_queue = Queue()

        while True:
            ret, frame = self._cam.read()

            if not ret:
                break

            corners, ids, _ = detector.detectMarkers(frame)

            if processing_queue.qsize() >= self._MAX_PROCESS_SIZE:
                detections = [processing_queue.get_nowait() for _ in range(self._MAX_PROCESS_SIZE)]
                vec = self._determine_motion_vec(detections)
                # TODO: Complete function

            # TODO: Remove after debugging
            if ids is not None:
                cv.aruco.drawDetectedMarkers(frame, corners, ids)
                for i in range(len(ids)):
                    print(f"Detected Tag ID: {ids[i][0]}")

            cv.imshow('Camera Feed', frame)

            if cv.waitKey(1) == ord('q'):
                self._cam.release()
                cv.destroyAllWindows()
                break

if __name__ == "__main__":
    AgentTracker().start_tracking()