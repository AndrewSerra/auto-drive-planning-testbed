import asyncio
import logging
import websockets
from websockets.asyncio.server import serve, ServerConnection
from websockets.exceptions import ConnectionClosedOK
from typing import Callable


_logger = logging.getLogger("testbed")


class NotifierServer:

    _port: int
    # _active_connections: int

    def __init__(self, port: int = 8765):
        self._port = port
        self._active_connections = 0

    # def _incr_active_connections() -> None:


    async def _handle_conn(self, websocket: Callable[ServerConnection, None]) -> None:
        self._active_connections += 1

        while True:
            try:
                message = await websocket.recv()
            except ConnectionClosedOK:
                break

        self._active_connections -= 1

    async def run_server(self):
        async with serve(self._handle_conn, "localhost", self._port) as server:
            await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(NotifierServer().run_server())