import cv2 as cv
import numpy as np
import logging
import json
from dataclasses import dataclass
from pathlib import Path
from argparse import ArgumentParser
from camera import run_calibration
from config import TestbedConfig


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
        default="",
        help="Path for a config file"
    )

    args = argparser.parse_args()

    # sanity check
    assert isinstance(args.config_file, str), "config_file is not a string"
    
    testbed_config = TestbedConfig(file_path=args.config_file)

    run_calibration()

