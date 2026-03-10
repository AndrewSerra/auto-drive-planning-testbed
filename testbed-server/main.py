import cv2 as cv
import numpy as np
import logging
import json
from dataclasses import dataclass
from pathlib import Path
from argparse import ArgumentParser
from camera import run_calibration

@dataclass(frozen=True)
class Config:
    grid_num_cols: int
    grid_num_rows: int


def load_config(file_path: str | None) -> Config:
    logger.info("Loading config...")

    loaded_config = {}

    if file_path is not None:
        file = Path(file_path)
        config_exists = True

        if file.suffix != ".json":
            config_exists = False
            logger.warning(f"File '{file}' is not a json file, using defaults")
        elif not file.exists():
            config_exists = False
            logger.warning(f"Could not find config file {file}, using defaults")

        if config_exists:   
            with open(file_path, 'r') as f:
                loaded_config = json.load(f)

    config = {
        "grid": {
            "num_cols": 10,
            "num_rows": 10,
        }
    }

    config.update(loaded_config)

    return Config(
        grid_num_cols=config["grid"]["num_cols"],
        grid_num_rows=config["grid"]["num_rows"],
    )

if __name__ == "__main__":
    logger = logging.getLogger("testbed")
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(ch)

    argparser = ArgumentParser(
        prog="testbed-server",
        description="A server for testing planning algorithmns"
    )

    argparser.add_argument(
        '-c',
        '--config_file',
        type=str,
        help="Path for a config file"
    )

    args = argparser.parse_args()

    config = load_config(args.config_file)

    H = run_calibration()

