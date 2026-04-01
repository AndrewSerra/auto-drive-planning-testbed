import cv2 as cv
import numpy as np
import logging

_logger = logging.getLogger("testbed")

def _get_workspace_grid(image_shape: tuple, num_rows: int, num_cols: int):
    '''
    expected image shape is (image_h, image_w)
    '''
    assert len(image_shape) == 2, "image shape must have 2 dimensions, format (image_h, image_w)"

    img_h, img_w = image_shape
    vertical_space = np.linspace(0, img_h, num_rows)
    horizontal_space = np.linspace(0, img_w, num_cols)

def _detect_execution_boundary(image: np.ndarray) -> np.ndarray:
    _logger.info("Starting execution area boundary detection.")

    boundary_color_low = np.array([30, 170, 180])
    boundary_color_high = np.array([114, 255, 255])

    blur = cv.GaussianBlur(image, (3, 3), sigmaX=0.5, sigmaY=0.5)
    mask = cv.inRange(blur, boundary_color_low, boundary_color_high)

    # cv.imshow("boundary mask", mask)

    # kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (15, 15))
    # mask = cv.morphologyEx(mask, cv.MORPH_CLOSE, kernel)
    # mask = cv.morphologyEx(mask, cv.MORPH_OPEN, kernel)

    # cv.imshow("boundary mask morph", mask)

    contours, hierarchy = cv.findContours(mask, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)

    # Find the largest inner contour (has a parent in hierarchy)
    inner_contour = None
    max_area = 0
    min_area = 5000.0
    for i, contour in enumerate(contours):
        if hierarchy[0][i][3] >= 0:  # has parent → inner contour
            area = cv.contourArea(contour)
            if area >= min_area and area > max_area:
                max_area = area
                inner_contour = contour

    if inner_contour is None:
        return np.array([])

    epsilon = 0.005 * cv.arcLength(inner_contour, True)
    approx = cv.approxPolyDP(inner_contour, epsilon, True)

    return approx
