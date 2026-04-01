import logging
import signal
import time
from argparse import ArgumentParser
from queue import SimpleQueue
from threading import Thread, Event

from config import TestbedConfig
from camera import AgentTracker, run_calibration
from notifier import NotifierServer


def print_q(q: SimpleQueue, event: Event) -> None:
    
    while not event.is_set():
        if q.empty():
            time.sleep(0.1)
            continue

        item = q.get()

        print(item)


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
    

    stop_event = Event() # used for graceful shutdown
    stop_event.clear()

    _signal_handler = lambda signal, frame: stop_event.set()
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # Start of all system processes
    testbed_config = TestbedConfig(file_path=args.config_file)

    agent_track_out_q = SimpleQueue()

    H, boundary = run_calibration()

    agent_tracker = AgentTracker(H, stop_event, output_queue=agent_track_out_q)
    # notifier_server = NotifierServer(agent_track_out_q)

    agent_track_thread = Thread(target=agent_tracker.start_tracking)
    # notifier_serv_thread = Thread(target=notifier_server.run_server)
    print_q_thread = Thread(target=print_q, args=(agent_track_out_q, stop_event))

    threads = [
        agent_track_thread,
        print_q_thread,
        # notifier_serv_thread
    ]

    for t in threads:
        t.start()

    for t in threads:
        t.join()