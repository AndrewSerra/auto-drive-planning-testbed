import numpy as np
import cv2 as cv
import logging


_logger = logging.getLogger("testbed")

def _capture_frame() -> np.ndarray:
    capture = cv.VideoCapture(0)

    if not capture.isOpened():
        raise Exception("failed to open camera source")
    
    _logger.info("Capturing frame...")
    ret, frame = capture.read()

    capture.release()

    if not ret:
        raise Exception("failed to capture image")

    return frame
