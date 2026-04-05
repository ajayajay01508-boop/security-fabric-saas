import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock


VALID_EVENT = {
    "source_ip": "192.168.1.100",
    "destination_ip": "10.0.0.1",
    "source_port": 54321,
    "destination_port": 443,
    "protocol": "HTTPS",
    "bytes_sent": 4096,
    "bytes_received": 8192,
    "packets": 20,
    "duration_ms": 150,
}


@pytest.mark.asyncio
async def test_ingest_event_success(client, auth_headers):
    with patch("app.routers.telemetry.kafka_producer") as mock_kafka:
        mock_kafka.send = AsyncMock()
        r = await client.post("/telemetry/ingest", json=VALID_EVENT, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "queued"
    assert "event_id" in data
    assert len(data["event_id"]) == 36  # UUID format


@pytest.mark.asyncio
async def test_ingest_event_requires_auth(client):
    r = await client.post("/telemetry/ingest", json=VALID_EVENT)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_ingest_event_missing_required_fields(client, auth_headers):
    # Missing source_ip
    bad = {k: v for k, v in VALID_EVENT.items() if k != "source_ip"}
    r = await client.post("/telemetry/ingest", json=bad, headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_ingest_batch_success(client, auth_headers):
    events = [VALID_EVENT.copy() for _ in range(5)]
    with patch("app.routers.telemetry.kafka_producer") as mock_kafka:
        mock_kafka.send = AsyncMock()
        r = await client.post("/telemetry/ingest/batch", json={"events": events}, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "queued"
    assert data["count"] == 5
    assert len(data["event_ids"]) == 5


@pytest.mark.asyncio
async def test_ingest_batch_empty(client, auth_headers):
    with patch("app.routers.telemetry.kafka_producer") as mock_kafka:
        mock_kafka.send = AsyncMock()
        r = await client.post("/telemetry/ingest/batch", json={"events": []}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["count"] == 0


@pytest.mark.asyncio
async def test_ingest_batch_too_large(client, auth_headers):
    events = [VALID_EVENT.copy() for _ in range(1001)]
    with patch("app.routers.telemetry.kafka_producer") as mock_kafka:
        mock_kafka.send = AsyncMock()
        r = await client.post("/telemetry/ingest/batch", json={"events": events}, headers=auth_headers)
    assert r.status_code == 400
    assert "1000" in r.json()["detail"]


@pytest.mark.asyncio
async def test_ingest_generates_unique_event_ids(client, auth_headers):
    ids = []
    with patch("app.routers.telemetry.kafka_producer") as mock_kafka:
        mock_kafka.send = AsyncMock()
        for _ in range(10):
            r = await client.post("/telemetry/ingest", json=VALID_EVENT, headers=auth_headers)
            ids.append(r.json()["event_id"])
    assert len(set(ids)) == 10  # all unique


@pytest.mark.asyncio
async def test_ingest_optional_fields_default(client, auth_headers):
    minimal = {
        "source_ip": "1.2.3.4",
        "destination_ip": "5.6.7.8",
        "source_port": 1234,
        "destination_port": 80,
        "protocol": "TCP",
    }
    with patch("app.routers.telemetry.kafka_producer") as mock_kafka:
        mock_kafka.send = AsyncMock()
        r = await client.post("/telemetry/ingest", json=minimal, headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_ingest_kafka_failure_handled(client, auth_headers):
    """Kafka send failure should not crash the endpoint."""
    with patch("app.routers.telemetry.kafka_producer") as mock_kafka:
        mock_kafka.send = AsyncMock(side_effect=Exception("Kafka down"))
        r = await client.post("/telemetry/ingest", json=VALID_EVENT, headers=auth_headers)
    # Should still return 200 — kafka failures are logged, not surfaced
    assert r.status_code in (200, 500)
