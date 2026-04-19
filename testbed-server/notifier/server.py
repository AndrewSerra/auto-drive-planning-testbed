import asyncio
import logging
from queue import SimpleQueue
from typing import Sequence, Optional, Union, cast
from websockets.asyncio.server import serve, ServerConnection
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
from pydantic import ValidationError
from threading import Event

from camera.agent_tracking import DetectedChange
from .model import (
    AgentRegistrationMessage,
    DisplayRegistrationMessage,
    CarCommandMessage,
    server_reg_msg_type_adapter,
    ResponseMessage,
    Topic,
)

_logger = logging.getLogger("testbed")


class NotifierServer:

    _port: int
    _active_connections: int
    _active_ids: list[str]
    _incoming_queue: SimpleQueue
    _stop_event: Event

    _subscriptions: dict[Topic, set]
    _websockets: dict[str, ServerConnection]

    def __init__(self, queue: SimpleQueue, stop_event: Event, port: int = 8765):
        self._port = port
        self._incoming_queue = queue
        self._active_connections = 0
        self._active_ids = []
        self._subscriptions: dict[Topic, set] = {topic: set() for topic in Topic}
        self._websockets: dict[str, ServerConnection] = {}
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

    def _unsubscribe(self, id: str) -> None:
        for topic_set in self._subscriptions.values():
            topic_set.discard(id)

    async def _broadcast_to_topic(self, topic: Topic, payload: str) -> None:
        for sub_id in list(self._subscriptions[topic]):
            ws = self._websockets.get(sub_id)
            if ws is None:
                continue
            try:
                await ws.send(payload)
            except Exception:
                pass

    async def _queue_consumer(self) -> None:
        while not self._stop_event.is_set():
            try:
                item = self._incoming_queue.get_nowait()
                if isinstance(item, DetectedChange):
                    await self._broadcast_to_topic(Topic.RECV_POSITION, item.model_dump_json())
                elif isinstance(item, CarCommandMessage):
                    ws = self._websockets.get(item.car_id)
                    if ws is not None:
                        try:
                            await ws.send(item.model_dump_json())
                        except Exception:
                            pass
            except Exception:
                pass
            await asyncio.sleep(0.05)

    async def _handle_conn(self, websocket: ServerConnection) -> None:
        self._active_connections += 1

        connected_id: Optional[str] = None
        conn_t: Optional[str] = None
        running = True

        _logger.info(f"new connection received: {websocket.remote_address}")
        try:
            while running and not self._stop_event.is_set():
                if connected_id is None:
                    try:
                        message = cast(Union[AgentRegistrationMessage, DisplayRegistrationMessage], server_reg_msg_type_adapter.validate_json(await websocket.recv()))
                        _logger.info("Received 'init' request")

                        if message.id in self._active_ids:
                            _logger.info(f"Register id '{message.id}' already in active ids")
                            await websocket.send(ResponseMessage(
                                is_success=False,
                                message="id already active"
                            ).model_dump_json())
                            running = False
                            continue

                        connected_id = message.id
                        conn_t = message.connection_type

                        self._active_ids.append(connected_id)
                        self._websockets[connected_id] = websocket

                        if conn_t == "agent":
                            _logger.info("Subscribing agent to 'RECV_COMMAND' and 'SYSTEM_WIDE'")
                            self._subscribe_to(connected_id, [Topic.RECV_COMMAND, Topic.SYSTEM_WIDE])
                        elif conn_t == "display":
                            _logger.info("Subscribing display to 'RECV_POSITION' and 'SYSTEM_WIDE'")
                            self._subscribe_to(connected_id, [Topic.RECV_POSITION, Topic.SYSTEM_WIDE])
                        else:
                            _logger.error("sanity check, should never reach here. invalid connection type")
                            raise Exception(f"invalid connection type: {conn_t}")

                        _logger.info(f"Successfully initialized '{conn_t}' id '{connected_id}'")
                        await websocket.send(ResponseMessage(
                            is_success=True,
                            message="registered"
                        ).model_dump_json())

                    except ValidationError:
                        _logger.info("Could not validate server registration message. Closing connection.")
                        await websocket.send(ResponseMessage(
                            is_success=False,
                            message="invalid registration message format"
                        ).model_dump_json())
                        running = False

                    except Exception:
                        running = False

                else:
                    await websocket.wait_closed()
                    running = False

        except ConnectionClosedOK:
            _logger.info("connection closed successfully")

        except ConnectionClosedError as e:
            _logger.error(f"connection closed unexpectedly: {e}")

        finally:
            self._active_connections -= 1
            if connected_id is not None:
                self._active_ids.remove(connected_id)
                self._websockets.pop(connected_id, None)
                self._unsubscribe(connected_id)

    async def run_server(self):
        async with serve(self._handle_conn, "0.0.0.0", self._port):
            asyncio.create_task(self._queue_consumer())
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
    stop_event = Event()
    stop_event.clear()

    _signal_handler = lambda signal, frame: stop_event.set()
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    asyncio.run(NotifierServer(q, stop_event).run_server())
