import logging
from queue import SimpleQueue
from typing import Annotated, Union, Sequence
from websockets.asyncio.server import serve, ServerConnection
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
from pydantic import Field, TypeAdapter, ValidationError
from .model import (
    ServerRegistrationMessage, ResponseMessage,
    ConnType,
    Topic
)

_logger = logging.getLogger("testbed")

class NotifierServer:

    _port: int
    _active_connections: int
    _incoming_queue: SimpleQueue

    _subscriptions: dict[Topic, set]

    def __init__(self, queue: SimpleQueue, port: int = 8765):
        self._port = port
        self._incoming_queue = queue
        self._active_connections = 0
        self._subscriptions: dict[Topic, set] = {topic: set() for topic in Topic}

    def _subscribe_to(self, id: str, topics: Sequence[Topic]) -> None:
        assert isinstance(topics, Sequence) and \
                all([type(topic) == Topic for topic in topics]), \
                "incorrect type received to subscribed to"
        
        topics_str = ",".join([topic.value for topic in topics])
        _logger.info(f"registering id '{id}' to {topics_str}")

        for topic in topics:
            if topic == Topic.RECV_COMMAND:
                self._subscriptions[Topic.RECV_COMMAND].add(id)
            elif topic == Topic.RECV_POSITION:
                self._subscriptions[Topic.RECV_POSITION].add(id)
            elif topic == Topic.SYSTEM_WIDE:
                self._subscriptions[Topic.SYSTEM_WIDE].add(id)
            

    async def _handle_conn(self, websocket: ServerConnection) -> None:
        id: str = ""
        conn_t: ConnType = "agent"
        init_complete = False
        self._active_connections += 1

        while not init_complete:
            try:
                message = ServerRegistrationMessage.model_validate_json(await websocket.recv())
                id, conn_t = message.id, message.connection_type

                # TODO: check if there is ids already in the system
                if conn_t == "display":
                    self._subscribe_to(id, [Topic.RECV_POSITION, Topic.SYSTEM_WIDE])
                    init_complete = True
                    await websocket.send(
                        ResponseMessage(is_success=True, message=f"display '{id}' initialized").model_dump_json())
                elif conn_t == "agent":
                    self._subscribe_to(id, [Topic.RECV_COMMAND, Topic.SYSTEM_WIDE])
                    init_complete = True
                    await websocket.send(
                        ResponseMessage(is_success=True, message=f"car '{id}' initialized").model_dump_json())
            except ValidationError as e:
                _logger.error(f"invalid message: {e}")
                await websocket.send(
                    ResponseMessage(is_success=False, message=f"{e.json()}").model_dump_json())

        while True:
            try:
                await websocket.wait_closed()

                if conn_t == "display":
                    pass
                elif conn_t == "agent":
                    pass
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

if __name__ == "__main__":
    NotifierServer().run_server()