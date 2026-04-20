import cv2 as cv
import numpy as np
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from enum import IntEnum
from .boundary import GridSpacing
from .utils import _capture_frame

_logger = logging.getLogger("testbed")

# This is the index of the point to use from an april tag.
# Position in the tuple defines id of the tag, the value is the index of the corner of the april tag.
# Each april tag has 4 corners, values are related to the corner of a single tag
_INNER_TAG_CORNER_IDX = (
    1,  # For tag with id 0 -- Bottom Left
    3,  # For tag with id 1 -- Top Right
    2,  # For tag with id 2 -- Top Left
    0,  # For tag with id 3 -- Bottom Right
)

_TAG_VERTICAL_EDGE_RIGHT    = (1, 2)
_TAG_VERTICAL_EDGE_LEFT     = (0, 3)
_TAG_HORIZONTAL_EDGE_BOTTOM = (2, 3)
_TAG_HORIZONTAL_EDGE_TOP    = (0, 1)

class _TagID(IntEnum):
    TOP_LEFT = 2
    TOP_RIGHT = 1
    BOTTOM_RIGHT = 3
    BOTTOM_LEFT = 0

@dataclass(frozen=True)
class FieldCorners:
    top_left: np.ndarray
    top_right: np.ndarray
    bottom_right: np.ndarray
    bottom_left: np.ndarray

    @classmethod
    def from_iterable(cls, corners: Sequence) -> "FieldCorners":
        '''
        Follows the clockwise order of the sequence when assigning corners, starting from top left
        '''
        assert len(corners) == 4, f"length of sequence is not 4, passed length {len(corners)}"
        return cls(corners[0], corners[1], corners[2], corners[3])

    def __iter__(self):
        for corner in [self.top_left, self.top_right, self.bottom_right, self.bottom_left]:
            yield corner

def _to_line(a: np.typing.NDArray[np.float32], b: np.typing.NDArray[np.float32]) -> np.typing.NDArray[np.float32]:
    assert isinstance(a, np.ndarray) and a.shape == (2,) and a.dtype == np.float32
    assert isinstance(b, np.ndarray) and b.shape == (2,) and b.dtype == np.float32
    pa = np.array([a[0], a[1], 1.0], dtype=np.float32)
    pb = np.array([b[0], b[1], 1.0], dtype=np.float32)
    return np.cross(pa, pb)

def _intersect(l1: np.typing.NDArray[np.float32], l2: np.typing.NDArray[np.float32]) -> np.typing.NDArray[np.float32]:
    assert isinstance(l1, np.ndarray) and l1.shape == (3,) and l1.dtype == np.float32
    assert isinstance(l2, np.ndarray) and l2.shape == (3,) and l2.dtype == np.float32
    p = np.cross(l1, l2)
    return (p[:2] / p[2]).astype(np.float32)

def _complete_missing(tags: dict[_TagID, np.ndarray | None]) -> FieldCorners:
    '''
    Expects the corners of a field. This will be length of 4. Tags dictionary contains a tag id associated with points from a april tag.
    '''
    assert len(tags) == 4, "expected number of items in list to be 4 to complete missing tags"
    # this will be the inner points of april tags to define field, top left is the start of the list
    inner_points: list[np.ndarray | None] = [None, None, None, None]
    # index of this list represent the tag_id and the value in the slot is the index corresponding in index_points
    tag_id_to_idx: list[int] = [3, 1, 0, 2]

    # A dictionary to fill in missing corners of the field
    # The keys represent the tag id, not the index in a list, values are the ids that should exist for a line
    _TAG_ID_CONNECTED_CORNERS: dict[_TagID, tuple[_TagID, _TagID]] = {
        _TagID.TOP_LEFT:     (_TagID.BOTTOM_LEFT,  _TagID.TOP_RIGHT),
        _TagID.TOP_RIGHT:    (_TagID.TOP_LEFT,     _TagID.BOTTOM_RIGHT),
        _TagID.BOTTOM_RIGHT: (_TagID.TOP_RIGHT,    _TagID.BOTTOM_LEFT),
        _TagID.BOTTOM_LEFT:  (_TagID.BOTTOM_RIGHT, _TagID.TOP_LEFT),
    }
     
    # Complete the missing corners
    for corner in tags.items():
        tag_id, points = corner

        if points is None:
            _logger.debug(f"Found missing corner! Tag ID point to compute: {tag_id}")
            c1, c2 = _TAG_ID_CONNECTED_CORNERS[tag_id]
            c1_pts, c2_pts = tags[c1], tags[c2]
            assert c1_pts is not None and c2_pts is not None, "expected connected corners to be not None"

            if tag_id == _TagID.TOP_LEFT:
                l1 = _to_line(c1_pts[_TAG_VERTICAL_EDGE_RIGHT[0]].flatten(), c1_pts[_TAG_VERTICAL_EDGE_RIGHT[1]].flatten())
                l2 = _to_line(c2_pts[_TAG_HORIZONTAL_EDGE_BOTTOM[0]].flatten(), c2_pts[_TAG_HORIZONTAL_EDGE_BOTTOM[1]].flatten())
                inner_points[tag_id_to_idx[tag_id]] = np.array(_intersect(l1, l2))
            elif tag_id == _TagID.TOP_RIGHT:
                l1 = _to_line(c1_pts[_TAG_HORIZONTAL_EDGE_BOTTOM[0]].flatten(), c1_pts[_TAG_HORIZONTAL_EDGE_BOTTOM[1]].flatten())
                l2 = _to_line(c2_pts[_TAG_VERTICAL_EDGE_LEFT[0]].flatten(), c2_pts[_TAG_VERTICAL_EDGE_LEFT[1]].flatten())
                inner_points[tag_id_to_idx[tag_id]] = np.array(_intersect(l1, l2))
            elif tag_id == _TagID.BOTTOM_RIGHT:
                l1 = _to_line(c1_pts[_TAG_VERTICAL_EDGE_LEFT[0]].flatten(), c1_pts[_TAG_VERTICAL_EDGE_LEFT[1]].flatten())
                l2 = _to_line(c2_pts[_TAG_HORIZONTAL_EDGE_TOP[0]].flatten(), c2_pts[_TAG_HORIZONTAL_EDGE_TOP[1]].flatten())
                inner_points[tag_id_to_idx[tag_id]] = np.array(_intersect(l1, l2))
            elif tag_id == _TagID.BOTTOM_LEFT:
                l1 = _to_line(c1_pts[_TAG_HORIZONTAL_EDGE_TOP[0]].flatten(), c1_pts[_TAG_HORIZONTAL_EDGE_TOP[1]].flatten())
                l2 = _to_line(c2_pts[_TAG_VERTICAL_EDGE_RIGHT[0]].flatten(), c2_pts[_TAG_VERTICAL_EDGE_RIGHT[1]].flatten())
                inner_points[tag_id_to_idx[tag_id]] = np.array(_intersect(l1, l2))
        else:
            inner_points[tag_id_to_idx[tag_id]] = np.array(points[_INNER_TAG_CORNER_IDX[tag_id]])


    return FieldCorners.from_iterable(inner_points)

def _calculate_homography_matrix(image: np.ndarray) -> np.ndarray:
    # Detect april tags
    _logger.info("Starting april tag detection.")

    ## configure detector
    _logger.debug("Configuring detector for april tag detection.")
    detector_params = cv.aruco.DetectorParameters()
    predef_dict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_APRILTAG_36H11)
    detector = cv.aruco.ArucoDetector(predef_dict, detector_params)

    ## detect tags
    tags, tag_ids, _ = detector.detectMarkers(image)
    tag_cnt = len(tags)
    _logger.debug(f"Detected {tag_cnt} tags. Ids found: {tag_ids.flatten()}.")
    
    # to map the tag ids to the april tag points
    tag_id_pts_map: dict[_TagID, np.ndarray | None] = {
        _TagID.TOP_LEFT: None,
        _TagID.TOP_RIGHT: None,
        _TagID.BOTTOM_RIGHT: None,
        _TagID.BOTTOM_LEFT: None
    }

    for i in range(tag_cnt):
        try:
            tag_id_pts_map[_TagID(tag_ids[i][0])] = tags[i][0]
        except KeyError:
            _logger.error(f"unknown tag id found: {_TagID(tag_ids[i][0])}")

    # assure all possible configurations are correct
    if tag_cnt == 2:
        assert (tag_id_pts_map[_TagID.BOTTOM_LEFT] is not None and tag_id_pts_map[_TagID.TOP_RIGHT] is not None) or \
                (tag_id_pts_map[_TagID.BOTTOM_RIGHT] is not None and tag_id_pts_map[_TagID.TOP_LEFT] is not None), \
                "For two tags, they have to be opposite corners."
    elif tag_cnt == 3:
        # Check only one tag is missing
        assert sum(v is None for v in tag_id_pts_map.values()) == 1
    elif tag_cnt == 4:
        # Check all corners are found
        assert all(tag_id_pts_map.values())
    else:
        raise Exception(f"invalid number of tags in setup: {tag_cnt}")

    # Fill missing corners depending on april tag count
    unprojected = _complete_missing(tag_id_pts_map)

    # Find homography matrix
    img_h, img_w, _ = image.shape

    point_destinations: list[tuple[int, int]] = [
        (0,     0),
        (img_w, 0),
        (img_w, img_h),
        (0,     img_h)
    ]

    assert np.array(unprojected).all(), "unprojected has None values"

    src_pts = np.array([pt.flatten() for pt in unprojected], dtype=np.float32)
    dst_pts = np.array(point_destinations, dtype=np.float32)
    homography_mat, _ = cv.findHomography(src_pts, dst_pts)

    return homography_mat

def _compute_grid(image_shape: tuple[int, int], grid_size: tuple[int, int]) -> GridSpacing:
    img_h, img_w = image_shape
    num_rows, num_cols = grid_size
    horizontal_space = np.linspace(0, img_w, num_cols + 1).astype(int)
    vertical_space   = np.linspace(0, img_h, num_rows + 1).astype(int)
    return horizontal_space, vertical_space

def run_calibration(grid_size: tuple[int, int]) -> tuple[np.ndarray, GridSpacing]:
    '''
    grid size is a integer pair of format <num_rows, num_cols>
    '''
    image = _capture_frame()

    # image_path = "/Users/andrewserra/GithubProjects/auto-planning-software-testbed/IMG_7969.JPG"
    # image = cv.imread(image_path)

    # if image is None:
    #     raise Exception("image not found")

    homography_mat = _calculate_homography_matrix(image)

    img_h, img_w, _ = image.shape
    projection = cv.warpPerspective(image, homography_mat, (img_w, img_h))

    # cv.imshow("project", projection)

    grid = _compute_grid(projection.shape[:2], grid_size)

    return homography_mat, grid
