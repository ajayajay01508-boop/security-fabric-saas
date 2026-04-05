import json
from aiokafka import AIOKafkaProducer
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class KafkaProducerService:
    def __init__(self):
        self._producer: AIOKafkaProducer | None = None

    async def start(self):
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
            retry_backoff_ms=200,
            request_timeout_ms=10000,
        )
        await self._producer.start()
        logger.info("Kafka producer started")

    async def stop(self):
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped")

    async def send(self, topic: str, value: dict, key: str | None = None):
        if not self._producer:
            logger.warning("Kafka producer not started, skipping message")
            return
        try:
            await self._producer.send_and_wait(topic, value=value, key=key)
        except Exception as e:
            logger.error(f"Failed to send Kafka message: {e}")


kafka_producer = KafkaProducerService()
