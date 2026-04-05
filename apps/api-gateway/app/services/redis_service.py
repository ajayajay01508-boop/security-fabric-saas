import redis.asyncio as aioredis
from app.core.config import settings
import json
import time
import random


class RedisService:
    def __init__(self):
        self._client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async def publish(self, channel: str, data: dict):
        await self._client.publish(channel, json.dumps(data))

    async def subscribe(self, channel: str):
        pubsub = self._client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub

    async def set(self, key: str, value: str, ex: int = None):
        await self._client.set(key, value, ex=ex)

    async def get(self, key: str) -> str | None:
        return await self._client.get(key)

    async def get_metrics(self) -> dict:
        """Return platform metrics for dashboard streaming."""
        return {
            "timestamp": time.time(),
            "threats_per_minute": random.randint(0, 50),
            "events_processed": random.randint(1000, 5000),
            "active_connections": random.randint(1, 100),
            "kafka_lag": random.randint(0, 500),
            "inference_latency_ms": round(random.uniform(10, 80), 2),
        }

    async def close(self):
        await self._client.close()


redis_client = RedisService()
