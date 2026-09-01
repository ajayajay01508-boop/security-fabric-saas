from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.kafka_service import KafkaProducerService
from app.services.redis_service import RedisService
from app.services.stripe_service import StripeService


@pytest.mark.asyncio
async def test_kafka_start_send_and_stop():
    producer = AsyncMock()
    with patch("app.services.kafka_service.AIOKafkaProducer", return_value=producer):
        service = KafkaProducerService()
        await service.start()
        await service.send("events", {"id": 1}, key="tenant-1")
        await service.stop()
    producer.start.assert_awaited_once()
    producer.send_and_wait.assert_awaited_once_with("events", value={"id": 1}, key="tenant-1")
    producer.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_kafka_send_without_start_is_safe():
    service = KafkaProducerService()
    await service.send("events", {"id": 1})


@pytest.mark.asyncio
async def test_kafka_send_failure_is_contained():
    service = KafkaProducerService()
    service._producer = AsyncMock()
    service._producer.send_and_wait.side_effect = RuntimeError("broker unavailable")
    await service.send("events", {"id": 1})


@pytest.mark.asyncio
async def test_redis_adapter_serializes_and_delegates():
    service = RedisService()
    service._client = AsyncMock()
    pubsub = AsyncMock()
    service._client.pubsub = MagicMock(return_value=pubsub)
    await service.publish("alerts", {"id": 7})
    assert service._client.publish.await_args.args == ("alerts", '{"id": 7}')
    assert await service.subscribe("alerts") is pubsub
    pubsub.subscribe.assert_awaited_once_with("alerts")
    await service.set("key", "value", ex=60)
    await service.get("key")
    await service.close()


@pytest.mark.asyncio
async def test_redis_metrics_have_expected_shape():
    metrics = await RedisService().get_metrics()
    assert {"timestamp", "threats_per_minute", "events_processed", "active_connections", "kafka_lag", "inference_latency_ms"} <= metrics.keys()


@pytest.mark.asyncio
async def test_stripe_development_paths(monkeypatch):
    monkeypatch.setattr("app.services.stripe_service.settings.ENVIRONMENT", "development")
    service = StripeService()
    assert (await service.create_customer("a@example.com", "A")).startswith("cus_mock_")
    assert (await service.create_subscription("cus_1", "price_1"))["status"] == "active"
    assert (await service.cancel_subscription("sub_1"))["status"] == "canceled"
    assert (await service.create_portal_session("cus_1", "https://return")) == "https://billing.stripe.com/mock/cus_1"


@pytest.mark.asyncio
async def test_stripe_production_paths(monkeypatch):
    monkeypatch.setattr("app.services.stripe_service.settings.ENVIRONMENT", "production")
    service = StripeService()
    with patch("app.services.stripe_service.stripe.Customer.create", return_value=MagicMock(id="cus_real")), \
         patch("app.services.stripe_service.stripe.Subscription.create", return_value={"id": "sub_real"}), \
         patch("app.services.stripe_service.stripe.Subscription.delete", return_value={"status": "canceled"}), \
         patch("app.services.stripe_service.stripe.billing_portal.Session.create", return_value=MagicMock(url="https://portal")):
        assert await service.create_customer("a@example.com", "A") == "cus_real"
        assert (await service.create_subscription("cus_real", "price"))["id"] == "sub_real"
        assert (await service.cancel_subscription("sub_real"))["status"] == "canceled"
        assert await service.create_portal_session("cus_real", "https://return") == "https://portal"
