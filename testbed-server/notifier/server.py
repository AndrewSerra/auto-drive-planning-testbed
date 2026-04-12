import asyncio
import logging
from queue import SimpleQueue
from typing import Annotated, Union, Sequence, Literal, Optional
from websockets.asyncio.server import serve, ServerConnection
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
from pydantic import Field, TypeAdapter, ValidationError
from threading import Event
from dataclasses import dataclass

from .model import (
    ServerRegistrationMessage,
    server_reg_msg_type_adapter,
    ResponseMessage,
    Topic
)

_logger = logging.getLogger("testbed")

NotifierConnSMState = Literal['init', 'run']

class NotifierConnSM:
    _state: NotifierConnSMState

    _connected_id: Optional[str]
    _conn_t: Optional[Literal["agent", "display"]]

    def __init__(self) -> None:
        self._state = "init"
        self._connected_id = None
        self._conn_t = None

    @property
    def state(self) -> NotifierConnSMState:
        return self._state
    
    @property
    def connected_id(self) -> NotifierConnSMState:
        if self._state == "init":
            raise Exception("cannot get connected id before initialization")
        return self._connected_id

    @property
    def conn_t(self) -> NotifierConnSMState:
        if self._state == "init":
            raise Exception("cannot get connection type before initialization")
        return self._conn_t

    @property
    def is_initialized(self) -> bool:
        return self._state != "init"
    
    def initialize(self, registration_msg: ServerRegistrationMessage):
        self._connected_id = registration_msg.id
        self._conn_t = registration_msg.connection_type

        self._state = "run"

class NotifierServer:

    _port: int
    _active_connections: int
    _active_ids: list[str]
    _incoming_queue: SimpleQueue
    _stop_event: Event

    _subscriptions: dict[Topic, set]

    def __init__(self, queue: SimpleQueue, stop_event: Event, port: int = 8765):
        self._port = port
        self._incoming_queue = queue
        self._active_connections = 0
        self._active_ids = []
        self._subscriptions: dict[Topic, set] = {topic: set() for topic in Topic}
        self._stop_event = stop_event

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
        self._active_connections += 1

        sm = NotifierConnSM()
        running = True
        _logger.info(f"new connection received: {websocket.remote_address}")
        try:
            while(running and not self._stop_event.is_set()):
                if sm.state == "init":
                    try:
                        message = server_reg_msg_type_adapter.validate_json(await websocket.recv())
                        _logger.info("Received 'init' request")
                        sm.initialize(message)

                        if sm.connected_id in self._active_ids:
                            _logger.info(f"Register id '{sm.connected_id}' already in active ids")
                            await websocket.send(ResponseMessage(
                                is_success=False,
                                message="id already active"
                            ).model_dump_json())
                            running = False
                            await websocket.close()
                            continue

                        self._active_ids.append(sm.connected_id)
                        
                        if sm.conn_t == "agent":
                            _logger.info("Subscribing agent to 'RECV_COMMAND' and 'SYSTEM_WIDE'")
                            self._subscribe_to(
                                sm.connected_id,
                                [Topic.RECV_COMMAND, Topic.SYSTEM_WIDE]
                            )
                        elif sm.conn_t == "display":
                            _logger.info("Subscribing display to 'RECV_POSITION' and 'SYSTEM_WIDE'")
                            self._subscribe_to(
                                sm.connected_id,
                                [Topic.RECV_POSITION, Topic.SYSTEM_WIDE]
                            )
                        else:
                            _logger.error("sanity check, should never reach here. invalid connection type 'sm.conn_t")
                            raise Exception(f"invalid connection type: {sm.conn_t}")

                        _logger.info(f"Successfully initialized '{sm.conn_t}' id '{sm.connected_id}'")
                        await websocket.send(ResponseMessage(
                            is_success=True,
                            message="registered"
                        ).model_dump_json())

                    except ValidationError as e:
                        _logger.info(f"Could not validate server registration message. Closing connection.")
                        await websocket.send(ResponseMessage(
                            is_success=False,
                            message="invalid registration message format"
                        ).model_dump_json())
                        running = False
                        await websocket.close()

                    except Exception as e:
                        running = False
                        await websocket.close()

                elif sm.state == "run":
                    message = await websocket.recv()
                    _logger.info(f"received message from '{sm.connected_id}': {message}")
        
        except ConnectionClosedOK:
            _logger.info(f"connection closed successfully")
                
        except ConnectionClosedError as e:
            _logger.error(f"connection closed unexpectedly: {e}")

        self._active_connections -= 1

        if sm.is_initialized:
            self._active_ids.remove(sm.connected_id)

    async def run_server(self):
        async with serve(self._handle_conn, "0.0.0.0", self._port):
            while not self._stop_event.is_set():
                await asyncio.sleep(0.1)


if __name__ == "__main__":
    import signal
    import asyncio

    logger = logging.getLogger("testbed")
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(ch)

    q = SimpleQueue()
    stop_event = Event() # used for graceful shutdown
    stop_event.clear()

    _signal_handler = lambda signal, frame: stop_event.set()
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    asyncio.run(NotifierServer(q, stop_event).run_server())