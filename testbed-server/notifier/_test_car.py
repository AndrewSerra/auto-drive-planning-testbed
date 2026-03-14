import asyncio
from queue import SimpleQueue
from websockets.sync.client import connect
from .model import (
    Action,
    Topic,
    ServerRegistrationMessage,
    ResponseMessage,
)
from threading import Thread
from .server import NotifierServer


def init_car(car_id: str):
    with connect("ws://localhost:8765") as ws:
        reg_msg = ServerRegistrationMessage(
            action=Action.INITIALIZE.value,
            id=car_id,
            connection_type="agent"
        )
        ws.send(reg_msg.model_dump_json())
        resp = ResponseMessage.model_validate_json(ws.recv())
        if not resp.is_success:
            print(f"car '{car_id}' registration unsuccessful: {resp.message}")
        else:
            print(f"car '{car_id}' registration success")


def run_server() -> None:
    asyncio.run(NotifierServer(queue=SimpleQueue()).run_server())

if __name__ == "__main__":
    import time
    import logging
    logging.basicConfig(level=logging.INFO)
    cars = (
        "car_1",
        "car_2",
        "car_3",
        "car_4",
        "car_5"
    )

    threads: list[Thread] = []

    server_thread = Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    for car in cars:
        t = Thread(target=init_car, args=(car,))
        threads.append(t)

    for t in threads:
        t.start()

    for t in threads:
        t.join()
