import asyncio
from websockets.sync.client import connect
from .model import (
    Action,
    Topic,
    CarRegisterMessage,
    TopicSubscribeMessage,
    ResponseMessage,
)
from typing import Annotated, Union
from pydantic import Field
from threading import Thread
from .server import NotifierServer

Message = Annotated[
    Union[CarRegisterMessage, TopicSubscribeMessage],
    Field(discriminator="action")
]

def init_car(car_id: str):
    with connect("ws://localhost:8765") as ws:
        regsiter_msg = CarRegisterMessage(
            action=Action.REGISTER.value,
            car_id=car_id
        )

        subscribe_msg = TopicSubscribeMessage(
            action=Action.SUBSCRIBE.value,
            topics=[
                Topic.SYSTEM_WIDE,
                Topic.RECV_COMMAND,
            ]
        )

        ws.send(regsiter_msg.model_dump_json())

        resp = ResponseMessage.model_validate_json(ws.recv())

        if not resp.is_success:
            print(f"car '{car_id}' registration unsuccessful")
            print(f"{car_id} message: {resp.message}")
        else:
            print(f"car '{car_id}' registration sucess")

        ws.send(subscribe_msg.model_dump_json())

        resp = ResponseMessage.model_validate_json(ws.recv())

        if not resp.is_success:
            print(f"car '{car_id}' subscription unsuccessful")
            print(f"{car_id} message: {resp.message}")
        else:
            print(f"car '{car_id}' subscription success")


def run_server() -> None:
    asyncio.run(NotifierServer().run_server())

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

