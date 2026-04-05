import json
import threading
import time
import asyncio
from queue import SimpleQueue
from websockets.sync.client import connect
from .server import NotifierServer

SERVER_URL = "ws://localhost:8765"


def _start_server():
    asyncio.run(NotifierServer(queue=SimpleQueue(), stop_event=threading.Event(), port=8765).run_server())


thread = threading.Thread(target=_start_server, daemon=True)
thread.start()
time.sleep(0.3)


def _send_recv(websocket, payload: dict) -> dict:
    websocket.send(json.dumps(payload))
    return json.loads(websocket.recv())


def test_agent_registration():
    with connect(SERVER_URL) as ws:
        resp = _send_recv(ws, {"id": "agent_1", "connection_type": "agent"})
        ws.close()
    assert resp["is_success"] is True, f"expected is_success=True, got {resp}"
    assert resp["message"], f"expected a message, got {resp}"


def test_display_registration():
    with connect(SERVER_URL) as ws:
        resp = _send_recv(ws, {"id": "display_1", "connection_type": "display"})
        ws.close()
    assert resp["is_success"] is True, f"expected is_success=True, got {resp}"
    assert resp["message"], f"expected a message, got {resp}"


def test_invalid_bad_connection_type():
    with connect(SERVER_URL) as ws:
        resp = _send_recv(ws, {"id": "x", "connection_type": "car"})
        ws.close()
    assert resp["is_success"] is False, f"expected is_success=False, got {resp}"


def test_invalid_missing_id():
    with connect(SERVER_URL) as ws:
        resp = _send_recv(ws, {"connection_type": "agent"})
    assert resp["is_success"] is False, f"expected is_success=False, got {resp}"


_ALL_TESTS = [
    test_agent_registration,
    test_display_registration,
    test_invalid_bad_connection_type,
    test_invalid_missing_id,
]

if __name__ == "__main__":
    passed = 0
    failed = 0
    for test_fn in _ALL_TESTS:
        try:
            test_fn()
            print(f"PASS  {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"FAIL  {test_fn.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
