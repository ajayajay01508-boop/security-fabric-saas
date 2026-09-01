from unittest.mock import AsyncMock

import pytest

from app.core.security import create_access_token
from app.routers.websocket import ConnectionManager, authenticate_ws


@pytest.mark.asyncio
async def test_connection_lifecycle_removes_empty_user_bucket():
    manager = ConnectionManager()
    socket = AsyncMock()
    await manager.connect(socket, "42")
    socket.accept.assert_awaited_once()
    assert manager.active_connections["42"] == [socket]

    manager.disconnect(socket, "42")
    assert "42" not in manager.active_connections


@pytest.mark.asyncio
async def test_broadcast_sends_to_every_live_connection():
    manager = ConnectionManager()
    first, second = AsyncMock(), AsyncMock()
    manager.active_connections = {"1": [first], "2": [second]}
    payload = {"severity": "critical"}

    await manager.broadcast(payload)

    first.send_json.assert_awaited_once_with(payload)
    second.send_json.assert_awaited_once_with(payload)


@pytest.mark.asyncio
async def test_broadcast_removes_failed_connections_without_crashing():
    manager = ConnectionManager()
    failed, healthy = AsyncMock(), AsyncMock()
    failed.send_json.side_effect = RuntimeError("socket closed")
    manager.active_connections = {"1": [failed, healthy]}

    await manager.broadcast({"event": "threat"})

    assert manager.active_connections["1"] == [healthy]


def test_websocket_authentication_accepts_valid_token_and_rejects_invalid():
    token = create_access_token({"sub": "99"})
    assert authenticate_ws(token) == "99"
    assert authenticate_ws("not-a-token") is None
