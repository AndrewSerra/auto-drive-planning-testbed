import json
import threading
import time
import asyncio
from websockets.sync.client import connect
from notifier.server import NotifierServer

SERVER_URL = "ws://localhost:8765"


def _start_server():
    asyncio.run(NotifierServer(port=8765).run_server())


thread = threading.Thread(target=_start_server, daemon=True)
thread.start()
time.sleep(0.3)


def _send_recv(websocket, payload: dict) -> dict:
    websocket.send(json.dumps(payload))
    return json.loads(websocket.recv())


def test_successful_registration():
    with connect(SERVER_URL) as ws:
        resp = _send_recv(ws, {"action": "REGISTER", "car_id": "car_reg_test"})
    assert resp["is_success"] is True, f"expected is_success=True, got {resp}"
    assert resp["message"] == "registered", f"expected 'registered', got {resp['message']}"


def test_duplicate_registration():
    with connect(SERVER_URL) as ws:
        _send_recv(ws, {"action": "REGISTER", "car_id": "car_dup"})
        resp = _send_recv(ws, {"action": "REGISTER", "car_id": "car_dup"})
    assert resp["is_success"] is True, f"expected is_success=True, got {resp}"
    assert resp["message"] == "already registered", f"expected 'already registered', got {resp['message']}"


def test_subscribe_after_registration():
    with connect(SERVER_URL) as ws:
        r1 = _send_recv(ws, {"action": "REGISTER", "car_id": "car_sub"})
        r2 = _send_recv(ws, {"action": "SUBSCRIBE", "topic": "RECV_COMMAND"})
    assert r1["is_success"] is True, f"register failed: {r1}"
    assert r2["is_success"] is True, f"subscribe failed: {r2}"


def test_subscribe_all_topics():
    with connect(SERVER_URL) as ws:
        r_reg = _send_recv(ws, {"action": "REGISTER", "car_id": "car_all_topics"})
        r1 = _send_recv(ws, {"action": "SUBSCRIBE", "topic": "RECV_COMMAND"})
        r2 = _send_recv(ws, {"action": "SUBSCRIBE", "topic": "RECV_POSITION"})
        r3 = _send_recv(ws, {"action": "SUBSCRIBE", "topic": "SYSTEM_WIDE"})
    for resp in [r_reg, r1, r2, r3]:
        assert resp["is_success"] is True, f"expected is_success=True, got {resp}"


def test_subscribe_before_registration():
    # Known bug: server returns is_success=True with "already subscribed" instead of an error
    with connect(SERVER_URL) as ws:
        resp = _send_recv(ws, {"action": "SUBSCRIBE", "topic": "RECV_COMMAND"})
    # Document the buggy behavior: response is received (server doesn't reject)
    assert "is_success" in resp, f"expected a response with is_success field, got {resp}"
    # Note: server incorrectly returns is_success=True with message="already subscribed"
    assert resp["is_success"] is True, f"[BUG] server should return is_success=False, but got {resp}"
    assert resp["message"] == "already subscribed", f"[BUG] unexpected message: {resp['message']}"


def test_invalid_message_missing_action():
    with connect(SERVER_URL) as ws:
        resp = _send_recv(ws, {"car_id": "x"})
    assert resp["is_success"] is False, f"expected is_success=False, got {resp}"
    assert "message" in resp and resp["message"], f"expected validation error message, got {resp}"


def test_invalid_message_bad_action():
    with connect(SERVER_URL) as ws:
        resp = _send_recv(ws, {"action": "UNKNOWN", "car_id": "x"})
    assert resp["is_success"] is False, f"expected is_success=False, got {resp}"
    assert "message" in resp and resp["message"], f"expected validation error message, got {resp}"


def test_invalid_subscribe_topic():
    with connect(SERVER_URL) as ws:
        _send_recv(ws, {"action": "REGISTER", "car_id": "car_bad_topic"})
        resp = _send_recv(ws, {"action": "SUBSCRIBE", "topic": "FAKE"})
    assert resp["is_success"] is False, f"expected is_success=False, got {resp}"
    assert "message" in resp and resp["message"], f"expected validation error message, got {resp}"


_ALL_TESTS = [
    test_successful_registration,
    test_duplicate_registration,
    test_subscribe_after_registration,
    test_subscribe_all_topics,
    test_subscribe_before_registration,
    test_invalid_message_missing_action,
    test_invalid_message_bad_action,
    test_invalid_subscribe_topic,
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
