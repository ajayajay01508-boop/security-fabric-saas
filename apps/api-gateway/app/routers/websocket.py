from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError, jwt
from app.core.config import settings
from app.services.redis_service import redis_client
import asyncio
import json

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            connections = self.active_connections[user_id]
            if websocket in connections:
                connections.remove(websocket)
            if not connections:
                del self.active_connections[user_id]

    async def broadcast(self, message: dict):
        dead = []
        for user_id, connections in self.active_connections.items():
            for ws in connections:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append((user_id, ws))
        for user_id, ws in dead:
            self.disconnect(ws, user_id)


manager = ConnectionManager()


def authenticate_ws(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


@router.websocket("/threats")
async def threats_websocket(websocket: WebSocket, token: str = Query(...)):
    user_id = authenticate_ws(token)
    if not user_id:
        await websocket.close(code=4001)
        return

    await manager.connect(websocket, user_id)
    pubsub = await redis_client.subscribe("threat-events")

    try:
        async def listen():
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    await websocket.send_json(data)

        listener_task = asyncio.create_task(listen())

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                await websocket.send_text("ping")

    except WebSocketDisconnect:
        listener_task.cancel()
        manager.disconnect(websocket, user_id)
        await pubsub.unsubscribe("threat-events")


@router.websocket("/metrics")
async def metrics_websocket(websocket: WebSocket, token: str = Query(...)):
    user_id = authenticate_ws(token)
    if not user_id:
        await websocket.close(code=4001)
        return

    await websocket.accept()

    try:
        while True:
            metrics = await redis_client.get_metrics()
            await websocket.send_json(metrics)
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
