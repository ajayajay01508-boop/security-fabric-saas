import asyncio
import json
import logging
import uuid
import time
import random
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
import redis.asyncio as aioredis
from detector import ThreatDetector
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ai-detection-engine")


class DetectionProcessor:
    def __init__(self):
        self.detector = ThreatDetector(model_path=settings.MODEL_PATH)
        self.consumer: AIOKafkaConsumer | None = None
        self.producer: AIOKafkaProducer | None = None
        self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        self.processed_count = 0
        self.threat_count = 0

    async def start(self):
        self.consumer = AIOKafkaConsumer(
            settings.KAFKA_TOPIC_TELEMETRY,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_CONSUMER_GROUP,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="latest",
            enable_auto_commit=True,
            max_poll_records=100,
        )
        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await self.consumer.start()
        await self.producer.start()
        logger.info("Detection processor started")

    async def stop(self):
        if self.consumer:
            await self.consumer.stop()
        if self.producer:
            await self.producer.stop()
        await self.redis.close()
        logger.info("Detection processor stopped")

    async def process_event(self, event: dict) -> dict | None:
        """Run ML inference on a telemetry event."""
        start_ts = time.time()
        result = self.detector.predict(event)
        latency_ms = (time.time() - start_ts) * 1000

        # Update metrics in Redis
        await self.redis.incr("metrics:events_processed")
        await self.redis.set("metrics:last_inference_ms", round(latency_ms, 2))

        if result["is_threat"]:
            threat_event = {
                "threat_id": str(uuid.uuid4()),
                "timestamp": time.time(),
                "severity": result["severity"],
                "classification": result["classification"],
                "confidence_score": result["confidence"],
                "source_ip": event.get("source_ip"),
                "destination_ip": event.get("destination_ip"),
                "source_port": event.get("source_port"),
                "destination_port": event.get("destination_port"),
                "protocol": event.get("protocol"),
                "description": result["description"],
                "tenant_id": event.get("tenant_id"),
                "raw_event_id": event.get("event_id"),
                "inference_latency_ms": round(latency_ms, 2),
            }

            self.threat_count += 1
            await self.redis.incr("metrics:threats_detected")
            await self.redis.publish("threat-events", json.dumps(threat_event))
            logger.info(
                f"THREAT DETECTED | {result['severity'].upper()} | "
                f"{result['classification']} | "
                f"{event.get('source_ip')} → {event.get('destination_ip')} | "
                f"confidence={result['confidence']:.2f}"
            )
            return threat_event
        return None

    async def run(self):
        await self.start()
        logger.info(f"Consuming from topic: {settings.KAFKA_TOPIC_TELEMETRY}")
        try:
            async for msg in self.consumer:
                event = msg.value
                self.processed_count += 1

                threat = await self.process_event(event)

                if threat:
                    # Publish to threat-events topic
                    await self.producer.send_and_wait(
                        settings.KAFKA_TOPIC_THREATS, value=threat
                    )
                    # High severity → also queue for voice + notification
                    if threat["severity"] in ("critical", "high"):
                        await self.producer.send_and_wait(
                            "alert-notifications", value=threat
                        )
                    if threat["severity"] == "critical":
                        await self.producer.send_and_wait(
                            "voice-alerts", value=threat
                        )

                if self.processed_count % 500 == 0:
                    logger.info(
                        f"Stats: processed={self.processed_count} "
                        f"threats={self.threat_count}"
                    )
        except Exception as e:
            logger.error(f"Consumer error: {e}", exc_info=True)
        finally:
            await self.stop()


async def main():
    processor = DetectionProcessor()
    await processor.run()


if __name__ == "__main__":
    asyncio.run(main())
