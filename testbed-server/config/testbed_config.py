import logging
import json
from pathlib import Path

_logger = logging.getLogger("testbed")

class TestbedConfig:
    _instance = None

    _grid_num_cols: int = 10
    _grid_num_rows: int = 10

    _field_length: float = 0.0  # physical width of field (maps to image width)
    _field_depth: float = 0.0   # physical height of field (maps to image height)
    _image_width: int = 0       # pixel width of transformed image
    _image_height: int = 0      # pixel height of transformed image

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, file_path: str = ""):
        if self._initialized:
            return
        self._initialized = True

        self._load_config(file_path)

    def _load_config(self, file_path: str = "") -> None:
        _logger.info("Loading config...")

        loaded_config = {}

        if file_path.strip() != "":
            file = Path(file_path)
            config_exists = True

            if file.suffix != ".json":
                config_exists = False
                _logger.warning(f"File '{file}' is not a json file, using defaults")
            elif not file.exists():
                config_exists = False
                _logger.warning(f"Could not find config file {file}, using defaults")

            if config_exists:
                with open(file_path, 'r') as f:
                    loaded_config = json.load(f)

        config = {
            "grid": {
                "num_cols": self._grid_num_cols,
                "num_rows": self._grid_num_rows,
            },
            "dimensions": {
                "field": {"length": self._field_length, "depth": self._field_depth},
                "image": {"width": self._image_width, "height": self._image_height},
            },
        }

        config.update(loaded_config)

        self._grid_num_cols = config["grid"]["num_cols"]
        self._grid_num_rows = config["grid"]["num_rows"]

        self._field_length = config["dimensions"]["field"]["length"]
        self._field_depth = config["dimensions"]["field"]["depth"]
        self._image_width = config["dimensions"]["image"]["width"]
        self._image_height = config["dimensions"]["image"]["height"]

    # --- grid ---

    @property
    def grid_size(self) -> tuple[int, int]:
        return self.grid_num_rows, self.grid_num_cols

    @property
    def grid_num_cols(self) -> int:
        return self._grid_num_cols

    @grid_num_cols.setter
    def grid_num_cols(self, value: int) -> None:
        assert isinstance(value, int), f"number of grid columns, must be int, received '{type(value)}'"
        self._grid_num_cols = value

    @property
    def grid_num_rows(self) -> int:
        return self._grid_num_rows

    @grid_num_rows.setter
    def grid_num_rows(self, value: int) -> None:
        assert isinstance(value, int), f"number of grid rows, must be int, received '{type(value)}'"
        self._grid_num_rows = value

    # --- dimensions ---

    @property
    def field_length(self) -> float:
        """Physical length of the field (x axis, maps to image width)."""
        return self._field_length

    @property
    def field_depth(self) -> float:
        """Physical depth of the field (y axis, maps to image height)."""
        return self._field_depth

    @property
    def image_width(self) -> int:
        """Pixel width of the transformed (bird's-eye-view) image."""
        return self._image_width

    @property
    def image_height(self) -> int:
        """Pixel height of the transformed (bird's-eye-view) image."""
        return self._image_height

    # --- coordinate mapping ---

    @property
    def pixels_per_unit_x(self) -> float:
        """Pixels per physical unit along x (length → image width)."""
        if self._field_length == 0:
            raise ValueError("field.length is not configured")
        return self._image_width / self._field_length

    @property
    def pixels_per_unit_y(self) -> float:
        """Pixels per physical unit along y (depth → image height)."""
        if self._field_depth == 0:
            raise ValueError("field.depth is not configured")
        return self._image_height / self._field_depth

    def field_to_pixel(self, x: float, y: float) -> tuple[float, float]:
        """Convert physical field coordinates to image pixel coordinates.

        Args:
            x: Physical distance along the field length axis.
            y: Physical distance along the field depth axis.

        Returns:
            (pixel_x, pixel_y) in the transformed image.
        """
        return x * self.pixels_per_unit_x, y * self.pixels_per_unit_y

    def pixel_to_field(self, pixel_x: float, pixel_y: float) -> tuple[float, float]:
        """Convert image pixel coordinates to physical field coordinates.

        Args:
            pixel_x: X position in the transformed image.
            pixel_y: Y position in the transformed image.

        Returns:
            (x, y) physical coordinates on the field.
        """
        return pixel_x / self.pixels_per_unit_x, pixel_y / self.pixels_per_unit_y
