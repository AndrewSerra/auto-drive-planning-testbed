import logging
import json
from pathlib import Path

_logger = logging.getLogger("testbed")

class TestbedConfig:
    _instance = None

    _grid_num_cols: int = 10
    _grid_num_rows: int = 10

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
            }
        }

        config.update(loaded_config)

        self._grid_num_cols = config["grid"]["num_cols"]
        self._grid_num_rows = config["grid"]["num_rows"]

    @property
    def grid_num_cols(self) -> int:
        return self._grid_num_cols

    @grid_num_cols.setter
    def grid_num_cols(self, value: int) -> None:
        self._grid_num_cols = value

    @property
    def grid_num_rows(self) -> int:
        return self._grid_num_rows

    @grid_num_rows.setter
    def grid_num_rows(self, value: int) -> None:
        self._grid_num_rows = value
