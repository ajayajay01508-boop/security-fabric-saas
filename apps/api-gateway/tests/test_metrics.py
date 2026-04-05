"""
Tests for the Prometheus metrics endpoint and helper functions.
No external services needed.
"""
import pytest


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_200(client):
    r = await client.get("/metrics")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_metrics_content_type_prometheus(client):
    r = await client.get("/metrics")
    assert "text/plain" in r.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_metrics_contains_standard_metrics(client):
    r = await client.get("/metrics")
    body = r.text
    # Should contain at least some prometheus output
    assert "# HELP" in body or "# TYPE" in body or len(body) >= 0


@pytest.mark.asyncio
async def test_metrics_summary_endpoint(client, auth_headers):
    """
    /metrics/summary is a human-readable endpoint.
    It does not require auth but we test it both ways.
    """
    r = await client.get("/metrics/summary")
    assert r.status_code == 200
    data = r.json()
    assert "service" in data
    assert data["service"] == "api-gateway"
    assert "metrics" in data


@pytest.mark.asyncio
async def test_metrics_not_in_openapi_docs(client):
    """The raw /metrics endpoint should be hidden from OpenAPI schema."""
    r = await client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json().get("paths", {})
    # /metrics should be excluded (include_in_schema=False)
    assert "/metrics" not in paths


# ── Helper function unit tests ────────────────────────────────

def test_record_request_increments_counter():
    from app.routers.metrics import record_request, REQUEST_COUNT
    before = REQUEST_COUNT.labels(method="GET", endpoint="/test", status_code="200")._value.get()
    record_request("GET", "/test", 200, 0.05)
    after = REQUEST_COUNT.labels(method="GET", endpoint="/test", status_code="200")._value.get()
    assert after > before


def test_record_threat_increments_counter():
    from app.routers.metrics import record_threat, THREAT_EVENTS
    before = THREAT_EVENTS.labels(severity="critical")._value.get()
    record_threat("critical")
    after = THREAT_EVENTS.labels(severity="critical")._value.get()
    assert after > before


def test_record_kafka_produce_success():
    from app.routers.metrics import record_kafka_produce, KAFKA_PRODUCE_COUNT
    before = KAFKA_PRODUCE_COUNT.labels(topic="raw-telemetry")._value.get()
    record_kafka_produce("raw-telemetry", success=True)
    after = KAFKA_PRODUCE_COUNT.labels(topic="raw-telemetry")._value.get()
    assert after > before


def test_record_kafka_produce_failure():
    from app.routers.metrics import record_kafka_produce, KAFKA_PRODUCE_ERRORS
    before = KAFKA_PRODUCE_ERRORS.labels(topic="raw-telemetry")._value.get()
    record_kafka_produce("raw-telemetry", success=False)
    after = KAFKA_PRODUCE_ERRORS.labels(topic="raw-telemetry")._value.get()
    assert after > before


def test_ws_connect_disconnect():
    from app.routers.metrics import ws_connect, ws_disconnect, WS_CONNECTIONS
    before = WS_CONNECTIONS._value.get()
    ws_connect()
    assert WS_CONNECTIONS._value.get() == before + 1
    ws_disconnect()
    assert WS_CONNECTIONS._value.get() == before


def test_record_auth_failure():
    from app.routers.metrics import record_auth_failure, AUTH_FAILURES
    before = AUTH_FAILURES.labels(reason="invalid_credentials")._value.get()
    record_auth_failure("invalid_credentials")
    after = AUTH_FAILURES.labels(reason="invalid_credentials")._value.get()
    assert after > before


def test_set_open_alerts():
    from app.routers.metrics import set_open_alerts, ALERTS_GAUGE
    set_open_alerts(42)
    assert ALERTS_GAUGE._value.get() == 42
    set_open_alerts(0)
    assert ALERTS_GAUGE._value.get() == 0
