import sys
import asyncio
import logging
import signal
from argparse import ArgumentParser
from queue import SimpleQueue
from threading import Thread, Event

from config.testbed_config import TestbedConfig
from camera.calibration import run_calibration
from camera.agent_tracking import AgentTracker
from control.control import Controller
from control.field_state import FieldState
from notifier.server import NotifierServer
from planner.types import Obstacles


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
        '-c', '--config_file',
        type=str, default="",
        help="Path for a config file"
    )
    args = argparser.parse_args()
    assert isinstance(args.config_file, str), "config_file is not a string"

    stop_event = Event()
    stop_event.clear()

    _signal_handler = lambda signal, frame: stop_event.set()
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    testbed_config = TestbedConfig(file_path=args.config_file)

    static_obstacles: Obstacles = frozenset(
        (row, col) for row, col in testbed_config.static_obstacles
    )

    detection_q: SimpleQueue = SimpleQueue()
    notifier_q: SimpleQueue = SimpleQueue()
    field_state = FieldState()

    H, boundary, grid_spacing = run_calibration(testbed_config.grid_size)

    agent_tracker = AgentTracker(H, grid_spacing, stop_event, detection_q)
    controller = Controller(
        detection_q=detection_q,
        notifier_q=notifier_q,
        config=testbed_config,
        obstacles=static_obstacles,
        field_state=field_state,
        stop_event=stop_event,
    )
    notifier_server = NotifierServer(queue=notifier_q, stop_event=stop_event)

    threads = [
        Thread(target=agent_tracker.start_tracking),
        Thread(target=controller.run),
        Thread(target=lambda: asyncio.run(notifier_server.run_server())),
    ]

    threads[2].start()  # start notifier server to get displays running and cars connected

    is_resp_invalid = True
    pre_start_res = ""

    while is_resp_invalid:
        res = input("should the program start 'y' for being 'q' for exit. y/q?").strip()
        if res not in ['y', 'q']:
            print(f"invalid response '{res}', only 'y' to begin,  'q' to exit")
        elif res == 'q':
            print("Quitting program...")
            sys.exit()
        else:
            for count in range(5, 0, -1):
                print(f"Starting in {count}")
            is_resp_invalid = False

    for t in threads:
        if not t.is_alive():
            t.start()

    for t in threads:
        t.join()
