import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import processor as processor_module


class FakeRedis:
    def __init__(self):
        self.increments = []
        self.values = {}
        self.published = []
        self.closed = False

    async def incr(self, key):
        self.increments.append(key)

    async def set(self, key, value):
        self.values[key] = value

    async def publish(self, channel, value):
        self.published.append((channel, json.loads(value)))

    async def close(self):
        self.closed = True


def build_processor(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(processor_module.aioredis, "from_url", lambda *_args, **_kwargs: redis)
    return processor_module.DetectionProcessor(), redis


@pytest.mark.asyncio
async def test_process_event_records_non_threat_metrics(monkeypatch):
    processor, redis = build_processor(monkeypatch)
    processor.detector.predict = lambda _event: {
        "is_threat": False,
        "severity": "info",
        "classification": "Unknown",
        "confidence": 0.1,
        "description": "normal",
    }
    result = await processor.process_event({"event_id": "safe"})
    assert result is None
    assert redis.increments == ["metrics:events_processed"]
    assert "metrics:last_inference_ms" in redis.values


@pytest.mark.asyncio
async def test_process_event_builds_and_publishes_threat(monkeypatch):
    processor, redis = build_processor(monkeypatch)
    processor.detector.predict = lambda _event: {
        "is_threat": True,
        "severity": "critical",
        "classification": "Command & Control",
        "confidence": 0.93,
        "description": "known C2 port",
    }
    event = {
        "event_id": "event-1",
        "source_ip": "10.0.0.1",
        "destination_ip": "10.0.0.2",
        "source_port": 50000,
        "destination_port": 4444,
        "protocol": "tcp",
        "tenant_id": "tenant-1",
    }
    threat = await processor.process_event(event)
    assert threat["raw_event_id"] == "event-1"
    assert threat["classification"] == "Command & Control"
    assert processor.threat_count == 1
    assert redis.increments == ["metrics:events_processed", "metrics:threats_detected"]
    assert redis.published[0][0] == "threat-events"


@pytest.mark.asyncio
async def test_start_and_stop_manage_dependencies(monkeypatch):
    processor, redis = build_processor(monkeypatch)

    class Resource:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.started = False
            self.stopped = False

        async def start(self):
            self.started = True

        async def stop(self):
            self.stopped = True

    consumer = Resource()
    producer = Resource()
    monkeypatch.setattr(processor_module, "AIOKafkaConsumer", lambda *_args, **_kwargs: consumer)
    monkeypatch.setattr(processor_module, "AIOKafkaProducer", lambda **_kwargs: producer)

    await processor.start()
    assert consumer.started and producer.started
    await processor.stop()
    assert consumer.stopped and producer.stopped and redis.closed


class FakeConsumer:
    def __init__(self, events):
        self.events = iter(events)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return SimpleNamespace(value=next(self.events))
        except StopIteration:
            raise StopAsyncIteration


@pytest.mark.asyncio
async def test_run_routes_events_by_severity_and_stops(monkeypatch):
    processor, _redis = build_processor(monkeypatch)
    processor.consumer = FakeConsumer([{"id": 1}, {"id": 2}, {"id": 3}])
    processor.producer = SimpleNamespace(send_and_wait=AsyncMock())
    processor.processed_count = 497
    processor.start = AsyncMock()
    processor.stop = AsyncMock()
    outputs = iter([
        {"severity": "critical"},
        {"severity": "high"},
        None,
    ])
    processor.process_event = AsyncMock(side_effect=lambda _event: next(outputs))

    await processor.run()

    topics = [call.args[0] for call in processor.producer.send_and_wait.await_args_list]
    assert topics == [
        processor_module.settings.KAFKA_TOPIC_THREATS,
        "alert-notifications",
        "voice-alerts",
        processor_module.settings.KAFKA_TOPIC_THREATS,
        "alert-notifications",
    ]
    processor.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_handles_consumer_error_and_stops(monkeypatch):
    processor, _redis = build_processor(monkeypatch)

    class BrokenConsumer:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise RuntimeError("consumer failed")

    processor.consumer = BrokenConsumer()
    processor.start = AsyncMock()
    processor.stop = AsyncMock()
    await processor.run()
    processor.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop_without_kafka_resources_still_closes_redis(monkeypatch):
    processor, redis = build_processor(monkeypatch)
    await processor.stop()
    assert redis.closed is True

