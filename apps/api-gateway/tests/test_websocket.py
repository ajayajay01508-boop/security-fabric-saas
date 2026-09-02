import asyncio

import pytest
from fastapi import WebSocketDisconnect
from jose import jwt

from app.core.config import settings
from app.routers import websocket as websocket_module


class FakeSocket:
    def __init__(self, *, fail_json=False, incoming=None):
        self.accepted = False
        self.closed_code = None
        self.fail_json = fail_json
        self.incoming = list(incoming or [])
        self.json_messages = []
        self.text_messages = []

    async def accept(self):
        self.accepted = True

    async def close(self, code):
        self.closed_code = code

    async def send_json(self, message):
        if self.fail_json:
            raise WebSocketDisconnect()
        self.json_messages.append(message)

    async def send_text(self, message):
        self.text_messages.append(message)

    async def receive_text(self):
        await asyncio.sleep(0)
        if self.incoming:
            value = self.incoming.pop(0)
            if isinstance(value, BaseException):
                raise value
            return value
        raise WebSocketDisconnect()


@pytest.mark.asyncio
async def test_connection_manager_lifecycle_and_dead_connection_cleanup():
    manager = websocket_module.ConnectionManager()
    first = FakeSocket()
    second = FakeSocket(fail_json=True)

    await manager.connect(first, "user-1")
    await manager.connect(second, "user-1")
    await manager.broadcast({"kind": "threat"})

    assert first.json_messages == [{"kind": "threat"}]
    assert manager.active_connections["user-1"] == [first]
    manager.disconnect(first, "user-1")
    manager.disconnect(first, "missing-user")
    assert "user-1" not in manager.active_connections


def test_authenticate_ws_accepts_valid_token_and_rejects_invalid_token():
    token = jwt.encode(
        {"sub": "user-42"}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    assert websocket_module.authenticate_ws(token) == "user-42"
    assert websocket_module.authenticate_ws("not-a-token") is None


@pytest.mark.asyncio
async def test_threat_socket_rejects_invalid_token():
    socket = FakeSocket()
    await websocket_module.threats_websocket(socket, "invalid")
    assert socket.closed_code == 4001


@pytest.mark.asyncio
async def test_threat_socket_streams_message_and_disconnects(monkeypatch):
    token = jwt.encode(
        {"sub": "stream-user"}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    class PubSub:
        def __init__(self):
            self.unsubscribed = False

        async def listen(self):
            yield {"type": "subscribe", "data": "ignored"}
            yield {"type": "message", "data": '{"severity":"high"}'}
            await asyncio.sleep(10)

        async def unsubscribe(self, channel):
            self.unsubscribed = channel == "threat-events"

    pubsub = PubSub()

    class Redis:
        async def subscribe(self, channel):
            assert channel == "threat-events"
            return pubsub

    manager = websocket_module.ConnectionManager()
    monkeypatch.setattr(websocket_module, "manager", manager)
    monkeypatch.setattr(websocket_module, "redis_client", Redis())
    socket = FakeSocket(incoming=["ping", WebSocketDisconnect()])

    await websocket_module.threats_websocket(socket, token)

    assert socket.accepted is True
    assert socket.text_messages == ["pong"]
    assert socket.json_messages == [{"severity": "high"}]
    assert pubsub.unsubscribed is True
    assert "stream-user" not in manager.active_connections


@pytest.mark.asyncio
async def test_metrics_socket_rejects_invalid_token():
    socket = FakeSocket()
    await websocket_module.metrics_websocket(socket, "invalid")
    assert socket.closed_code == 4001


@pytest.mark.asyncio
async def test_metrics_socket_sends_snapshot_until_disconnect(monkeypatch):
    token = jwt.encode(
        {"sub": "metrics-user"}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    class Redis:
        async def get_metrics(self):
            return {"events_processed": 12}

    monkeypatch.setattr(websocket_module, "redis_client", Redis())
    socket = FakeSocket(fail_json=True)
    await websocket_module.metrics_websocket(socket, token)
    assert socket.accepted is True

