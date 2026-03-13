import logging
from queue import SimpleQueue
from typing import Annotated, Union, Sequence
from websockets.asyncio.server import serve, ServerConnection
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
from pydantic import Field, TypeAdapter, ValidationError
from .model import (
    CarRegisterMessage, TopicSubscribeMessage, CarCommandMessage, ResponseMessage,
    CarState,
    Topic
)

_logger = logging.getLogger("testbed")

AnyMessage = Annotated[
    Union[CarRegisterMessage, TopicSubscribeMessage, CarCommandMessage],
    Field(discriminator="action")
]

class NotifierServer:

    _port: int
    _active_connections: int
    _incoming_queue: SimpleQueue

    _message_adapter = TypeAdapter(AnyMessage)
    _state: dict[str, CarState]
    _subscriptions: dict[Topic, set]

    def __init__(self, queue: SimpleQueue, port: int = 8765):
        self._port = port
        self._incoming_queue = queue
        self._active_connections = 0
        self._state: dict[str, CarState] = {}
        self._subscriptions: dict[Topic, set] = {topic: set() for topic in Topic}

    def _register_car(self, car_id: str):
        if car_id in self._state:
            _logger.warning(f"car id '{car_id}' already registered")
            return
        _logger.info(f"car id '{car_id}' registered")
        self._state[car_id] = CarState(
            is_registered=True
        )
    
    def _subscribe_topic(self, car_id: str, topics: Sequence[Topic]):
        if not isinstance(topics, Sequence) or not all(isinstance(t, Topic) for t in topics):
            raise TypeError(f"expected 'Sequence[Topic]' received {type(topics)}")
        for topic in topics:
            if car_id in self._subscriptions[topic]:
                _logger.warning(f"Car {car_id} is already subscribed to '{topic.value}'")
                continue
            _logger.warning(f"Car {car_id} is subscribed to '{topic.value}'")
            self._subscriptions[topic].add(car_id)

    async def _handle_conn(self, websocket: ServerConnection) -> None:
        car_id = None
        init_complete = False
        self._active_connections += 1

        while not init_complete:
            try:
                raw = await websocket.recv()
                msg = self._message_adapter.validate_json(raw)

                if isinstance(msg, CarRegisterMessage):
                    if car_id is None:
                        self._register_car(msg.car_id)
                        car_id = msg.car_id
                        await websocket.send(ResponseMessage(
                            is_success=True,
                            message="registered",
                        ).model_dump_json())
                    else:
                        _logger.warning(f"car with id '{car_id}' is already registered")
                        await websocket.send(ResponseMessage(
                            is_success=True,
                            message="already registered",
                        ).model_dump_json())
                elif isinstance(msg, TopicSubscribeMessage):
                    if car_id is None:
                        _logger.warning(f"car attempted to subscribe before registering")
                        await websocket.send(ResponseMessage(
                            is_success=True,
                            message="already subscribed",
                        ).model_dump_json())
                        continue
                    self._subscribe_topic(car_id, msg.topics)
                    await websocket.send(ResponseMessage(
                            is_success=True,
                            message="subscribed",
                        ).model_dump_json())
                    init_complete = True
            except ValidationError as e:
                await websocket.send(ResponseMessage(
                    is_success=False,
                    message=f"{e.json()}",
                ).model_dump_json())
            except ConnectionClosedOK:
                _logger.error(f"connection closed successfully")
                return
            except ConnectionClosedError as e:
                _logger.error(f"connection closed unexpectedly: {e}")
                return

        while True:
            try:
                await websocket.wait_closed()
            except ValidationError as e:
                await websocket.send(ResponseMessage(
                    is_success=False,
                    message=f"{e.json()}",
                ).model_dump_json())
            except ConnectionClosedOK:
                _logger.error(f"connection closed successfully")
                break
            except ConnectionClosedError as e:
                _logger.error(f"connection closed unexpectedly: {e}")
                break

        self._active_connections -= 1

    async def run_server(self):
        async with serve(self._handle_conn, "localhost", self._port) as server:
            await server.serve_forever()
