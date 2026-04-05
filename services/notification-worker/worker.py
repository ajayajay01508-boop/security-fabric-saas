import asyncio
import json
import logging
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from aiokafka import AIOKafkaConsumer
from pydantic_settings import BaseSettings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("notification-worker")


class Settings(BaseSettings):
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_CONSUMER_GROUP: str = "notification-worker"
    KAFKA_TOPIC_ALERTS: str = "alert-notifications"
    REDIS_URL: str = "redis://localhost:6379"
    DATABASE_URL: str = "postgresql+asyncpg://fabric:fabric_secret@postgres:5432/security_fabric"
    SMTP_HOST: str = "mailhog"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_FROM: str = "alerts@security-fabric.io"
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()

SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
    "info": "⚪",
}

ALERT_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <style>
    body {{ font-family: 'Courier New', monospace; background: #0a0a0a; color: #e0e0e0; }}
    .container {{ max-width: 600px; margin: 0 auto; padding: 24px; }}
    .header {{ background: #1a1a1a; border-left: 4px solid {color}; padding: 16px 20px; margin-bottom: 20px; }}
    .severity {{ font-size: 24px; font-weight: bold; color: {color}; }}
    .field {{ margin: 8px 0; }}
    .label {{ color: #888; font-size: 12px; text-transform: uppercase; }}
    .value {{ color: #fff; font-size: 14px; margin-top: 2px; }}
    .footer {{ margin-top: 24px; padding-top: 16px; border-top: 1px solid #333; color: #555; font-size: 12px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="severity">{emoji} {severity_upper} THREAT DETECTED</div>
      <div style="color:#888; margin-top:4px;">{classification}</div>
    </div>

    <div class="field">
      <div class="label">Threat ID</div>
      <div class="value">{threat_id}</div>
    </div>
    <div class="field">
      <div class="label">Source</div>
      <div class="value">{source_ip}:{source_port}</div>
    </div>
    <div class="field">
      <div class="label">Destination</div>
      <div class="value">{destination_ip}:{destination_port}</div>
    </div>
    <div class="field">
      <div class="label">Confidence Score</div>
      <div class="value">{confidence_score}</div>
    </div>
    <div class="field">
      <div class="label">Description</div>
      <div class="value">{description}</div>
    </div>

    <div class="footer">
      Security Fabric — Automated Alert System<br/>
      To manage alert preferences, visit your dashboard.
    </div>
  </div>
</body>
</html>
"""

SEVERITY_COLORS = {
    "critical": "#ff3b30",
    "high": "#ff9500",
    "medium": "#ffcc00",
    "low": "#34c759",
    "info": "#636366",
}


class EmailNotifier:
    def send_alert(self, threat: dict, recipient: str = "admin@security-fabric.io"):
        severity = threat.get("severity", "info")
        color = SEVERITY_COLORS.get(severity, "#636366")
        emoji = SEVERITY_EMOJI.get(severity, "⚪")

        html_body = ALERT_EMAIL_TEMPLATE.format(
            color=color,
            emoji=emoji,
            severity_upper=severity.upper(),
            classification=threat.get("classification", "Unknown"),
            threat_id=threat.get("threat_id", "N/A"),
            source_ip=threat.get("source_ip", "N/A"),
            source_port=threat.get("source_port", "N/A"),
            destination_ip=threat.get("destination_ip", "N/A"),
            destination_port=threat.get("destination_port", "N/A"),
            confidence_score=f"{threat.get('confidence_score', 0):.2%}",
            description=threat.get("description", "N/A"),
        )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[{severity.upper()}] Security Alert: {threat.get('classification', 'Threat Detected')}"
        msg["From"] = settings.SMTP_FROM
        msg["To"] = recipient
        msg.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
                if settings.SMTP_USER:
                    smtp.login(settings.SMTP_USER, settings.SMTP_PASS)
                smtp.sendmail(settings.SMTP_FROM, [recipient], msg.as_string())
            logger.info(f"Email sent for threat {threat.get('threat_id')} to {recipient}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")


class NotificationWorker:
    def __init__(self):
        self.consumer: AIOKafkaConsumer | None = None
        self.email_notifier = EmailNotifier()
        self.processed = 0

    async def start(self):
        self.consumer = AIOKafkaConsumer(
            settings.KAFKA_TOPIC_ALERTS,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_CONSUMER_GROUP,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="latest",
        )
        await self.consumer.start()
        logger.info(f"Notification worker consuming from {settings.KAFKA_TOPIC_ALERTS}")

    async def stop(self):
        if self.consumer:
            await self.consumer.stop()

    async def handle_alert(self, threat: dict):
        severity = threat.get("severity", "info")
        logger.info(
            f"Processing alert | {severity.upper()} | "
            f"{threat.get('classification')} | "
            f"{threat.get('source_ip')} → {threat.get('destination_ip')}"
        )

        # Send email notification
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self.email_notifier.send_alert,
            threat,
            "admin@security-fabric.io",
        )
        self.processed += 1

    async def run(self):
        await self.start()
        try:
            async for msg in self.consumer:
                await self.handle_alert(msg.value)
                if self.processed % 100 == 0:
                    logger.info(f"Notification worker processed {self.processed} alerts")
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
        finally:
            await self.stop()


if __name__ == "__main__":
    asyncio.run(NotificationWorker().run())


def build_twiml_equivalent(threat: dict) -> str:
    """
    Builds a human-readable alert string equivalent to TwiML voice content.
    Used by tests and for non-Twilio alert channels.
    """
    severity = threat.get("severity", "unknown").upper()
    classification = threat.get("classification", "unknown threat")
    src = threat.get("source_ip", "unknown")
    dst = threat.get("destination_ip", "unknown")
    confidence = threat.get("confidence_score", 0)
    return (
        f"Security Fabric Alert. {severity} severity threat detected. "
        f"Classification: {classification}. "
        f"Source: {src}. Destination: {dst}. "
        f"Confidence score: {confidence:.0%}. "
        f"Please review your security dashboard immediately."
    )
