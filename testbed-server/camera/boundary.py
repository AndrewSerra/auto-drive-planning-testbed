import cv2 as cv
import numpy as np
import logging
from typing import TypeAlias

_logger = logging.getLogger("testbed")

GridSpacing: TypeAlias = tuple[np.ndarray, np.ndarray]
Boundary: TypeAlias = np.ndarray

def _get_workspace_grid(image_shape: tuple, num_rows: int, num_cols: int) -> GridSpacing:
    '''
    expected image shape is (image_h, image_w)
    '''
    assert len(image_shape) == 2, "image shape must have 2 dimensions, format (image_h, image_w)"

    img_h, img_w = image_shape
    # There is a plus one here because given number of items in the linspace.
    # We want givent number of spacing, so we need to add 1 for proper grouping.
    vertical_space = np.linspace(0, img_h, num_rows + 1).astype(int)
    horizontal_space = np.linspace(0, img_w, num_cols + 1).astype(int)

    return horizontal_space, vertical_space

def _detect_execution_boundary(image: np.ndarray, grid_size: tuple[int, int]) -> tuple[Boundary, GridSpacing]:
    '''
    grid size is a integer pair of format <num_rows, num_cols>
    '''
    _logger.info("Starting execution area boundary detection.")

    grid: GridSpacing = _get_workspace_grid(image.shape, grid_size[0], grid_size[1])

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
        return Boundary(np.array([])), GridSpacing()

    epsilon = 0.005 * cv.arcLength(inner_contour, True)
    approx_boundary = cv.approxPolyDP(inner_contour, epsilon, True)

    return approx_boundary, grid

def _get_agent_grid_pos(grid_space: GridSpacing, position: tuple[int, int]) -> tuple[int, int]:
    '''
    find where the agent is in the gridspace.
    returns the index of the grid the car is found in
    '''
    row_space, col_space = grid_space
    x_pos, y_pos = position

    assert x_pos > 0 and x_pos < col_space[-1], "agent out of bounds in x coords"
    assert y_pos > 0 and y_pos < row_space[-1], "agent out of bounds in y coords"

    grid_pos_x, grid_pos_y = -1, -1
    curr_idx_x, curr_idx_y = len(col_space) - 1, len(row_space) - 1

    while (grid_pos_x == -1 or grid_pos_y == -1) and (curr_idx_x > 0 and curr_idx_y > 0):
        if grid_pos_x == -1:
            if x_pos < col_space[curr_idx_x]:
                curr_idx_x -= 1
            else:
                grid_pos_x = curr_idx_x

        if grid_pos_y == -1:
            if y_pos < row_space[curr_idx_y]:
                curr_idx_y -= 1
            else:
                grid_pos_y = curr_idx_y

    return grid_pos_x, grid_pos_y
