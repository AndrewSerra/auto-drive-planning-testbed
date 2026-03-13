import logging
from argparse import ArgumentParser
from queue import SimpleQueue
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
        description="A server for testing planning algorithms"
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

    camera_to_planner = SimpleQueue()
    planner_to_notifier = SimpleQueue()

    # run_calibration()

