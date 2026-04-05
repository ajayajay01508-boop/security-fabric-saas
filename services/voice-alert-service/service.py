import asyncio
import json
import logging
from aiokafka import AIOKafkaConsumer
from pydantic_settings import BaseSettings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("voice-alert-service")


class Settings(BaseSettings):
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_CONSUMER_GROUP: str = "voice-alert"
    KAFKA_TOPIC_VOICE: str = "voice-alerts"
    TWILIO_ACCOUNT_SID: str = "mock"
    TWILIO_AUTH_TOKEN: str = "mock"
    TWILIO_FROM_NUMBER: str = "+15005550006"
    ALERT_TO_NUMBER: str = "+1000000000"
    AWS_REGION: str = "us-east-1"
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()


def build_twiml_message(threat: dict) -> str:
    severity = threat.get("severity", "unknown").upper()
    classification = threat.get("classification", "unknown threat")
    src = threat.get("source_ip", "unknown")
    dst = threat.get("destination_ip", "unknown")
    confidence = threat.get("confidence_score", 0)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Matthew" language="en-US">
    Security Fabric Alert. {severity} severity threat detected.
    Classification: {classification}.
    Source: {src}. Destination: {dst}.
    Confidence score: {confidence:.0%}.
    Please review your security dashboard immediately.
  </Say>
  <Pause length="1"/>
  <Say voice="Polly.Matthew">Repeating alert. {severity} severity. {classification}. Review dashboard now.</Say>
</Response>"""


class VoiceAlerter:
    def __init__(self):
        self.mock_mode = settings.ENVIRONMENT == "development" or settings.TWILIO_ACCOUNT_SID == "mock"
        if not self.mock_mode:
            from twilio.rest import Client
            self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    def call(self, threat: dict):
        twiml = build_twiml_message(threat)
        if self.mock_mode:
            logger.info(
                f"[MOCK VOICE CALL] Would call {settings.ALERT_TO_NUMBER} | "
                f"severity={threat.get('severity')} | "
                f"classification={threat.get('classification')}"
            )
            logger.debug(f"TwiML: {twiml}")
            return

        try:
            call = self.client.calls.create(
                twiml=twiml,
                to=settings.ALERT_TO_NUMBER,
                from_=settings.TWILIO_FROM_NUMBER,
            )
            logger.info(f"Voice call initiated: SID={call.sid} to {settings.ALERT_TO_NUMBER}")
        except Exception as e:
            logger.error(f"Voice call failed: {e}")


class VoiceAlertService:
    def __init__(self):
        self.consumer: AIOKafkaConsumer | None = None
        self.alerter = VoiceAlerter()
        self.calls_made = 0

    async def start(self):
        self.consumer = AIOKafkaConsumer(
            settings.KAFKA_TOPIC_VOICE,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_CONSUMER_GROUP,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="latest",
        )
        await self.consumer.start()
        logger.info(f"Voice alert service consuming from {settings.KAFKA_TOPIC_VOICE}")

    async def stop(self):
        if self.consumer:
            await self.consumer.stop()

    async def handle(self, threat: dict):
        logger.info(f"CRITICAL ALERT → Voice call | {threat.get('classification')} | {threat.get('source_ip')}")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.alerter.call, threat)
        self.calls_made += 1
        # Rate limit: max 1 call per 60s per tenant
        await asyncio.sleep(60)

    async def run(self):
        await self.start()
        try:
            async for msg in self.consumer:
                await self.handle(msg.value)
        except Exception as e:
            logger.error(f"Voice service error: {e}", exc_info=True)
        finally:
            await self.stop()


if __name__ == "__main__":
    asyncio.run(VoiceAlertService().run())
