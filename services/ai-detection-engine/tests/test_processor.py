from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from processor import DetectionProcessor


def processor_with(result):
    processor = DetectionProcessor.__new__(DetectionProcessor)
    processor.detector = MagicMock()
    processor.detector.predict.return_value = result
    processor.redis = AsyncMock()
    processor.consumer = None
    processor.producer = None
    processor.processed_count = 0
    processor.threat_count = 0
    return processor


@pytest.mark.asyncio
async def test_process_non_threat_updates_metrics():
    processor = processor_with({"is_threat": False})
    assert await processor.process_event({"event_id": "safe"}) is None
    processor.redis.incr.assert_awaited_once_with("metrics:events_processed")
    processor.redis.set.assert_awaited_once()
    assert processor.threat_count == 0


@pytest.mark.asyncio
async def test_process_threat_builds_and_publishes_event():
    processor = processor_with({
        "is_threat": True,
        "severity": "critical",
        "classification": "Command & Control",
        "confidence": 0.97,
        "description": "C2 traffic",
    })
    event = {
        "event_id": "evt-1", "tenant_id": 4, "source_ip": "10.0.0.1",
        "destination_ip": "10.0.0.2", "source_port": 5000,
        "destination_port": 4444, "protocol": "TCP",
    }
    threat = await processor.process_event(event)
    assert threat["raw_event_id"] == "evt-1"
    assert threat["severity"] == "critical"
    assert threat["confidence_score"] == 0.97
    assert processor.threat_count == 1
    processor.redis.publish.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_and_stop_external_clients():
    processor = DetectionProcessor.__new__(DetectionProcessor)
    processor.detector = MagicMock()
    processor.redis = AsyncMock()
    processor.consumer = None
    processor.producer = None
    processor.processed_count = 0
    processor.threat_count = 0
    consumer, producer = AsyncMock(), AsyncMock()
    with patch("processor.AIOKafkaConsumer", return_value=consumer), patch("processor.AIOKafkaProducer", return_value=producer):
        await processor.start()
        assert processor.consumer is consumer
        assert processor.producer is producer
        consumer.start.assert_awaited_once()
        producer.start.assert_awaited_once()
        await processor.stop()
    consumer.stop.assert_awaited_once()
    producer.stop.assert_awaited_once()
    processor.redis.close.assert_awaited_once()
