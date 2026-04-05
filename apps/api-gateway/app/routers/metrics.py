"""
Prometheus metrics endpoint for the API Gateway.
Exposes /metrics in the standard Prometheus text format.
"""
from fastapi import APIRouter, Response
from prometheus_client import (
    Counter, Histogram, Gauge, generate_latest,
    CONTENT_TYPE_LATEST, CollectorRegistry, multiprocess
)
import time

router = APIRouter()

# ─── Metrics definitions ──────────────────────────────────────
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

THREAT_EVENTS = Counter(
    "threat_events_total",
    "Total threat events detected",
    ["severity"],
)

ALERTS_GAUGE = Gauge(
    "alerts_open_total",
    "Current open alerts",
)

KAFKA_PRODUCE_COUNT = Counter(
    "kafka_messages_produced_total",
    "Kafka messages produced",
    ["topic"],
)

KAFKA_PRODUCE_ERRORS = Counter(
    "kafka_produce_errors_total",
    "Kafka produce failures",
    ["topic"],
)

WS_CONNECTIONS = Gauge(
    "websocket_connections_active",
    "Active WebSocket connections",
)

AUTH_FAILURES = Counter(
    "auth_failures_total",
    "Authentication failures",
    ["reason"],
)

DB_QUERY_LATENCY = Histogram(
    "db_query_duration_seconds",
    "Database query latency",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)


# ─── Helper functions used by other modules ───────────────────
def record_request(method: str, endpoint: str, status_code: int, duration: float):
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)


def record_threat(severity: str):
    THREAT_EVENTS.labels(severity=severity).inc()


def record_kafka_produce(topic: str, success: bool = True):
    if success:
        KAFKA_PRODUCE_COUNT.labels(topic=topic).inc()
    else:
        KAFKA_PRODUCE_ERRORS.labels(topic=topic).inc()


def set_open_alerts(count: int):
    ALERTS_GAUGE.set(count)


def record_auth_failure(reason: str = "invalid_credentials"):
    AUTH_FAILURES.labels(reason=reason).inc()


def ws_connect():
    WS_CONNECTIONS.inc()


def ws_disconnect():
    WS_CONNECTIONS.dec()


# ─── Endpoint ─────────────────────────────────────────────────
@router.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@router.get("/metrics/summary")
async def metrics_summary():
    """Human-readable metrics summary for ops dashboards."""
    return {
        "service": "api-gateway",
        "version": "1.0.0",
        "metrics": {
            "requests_total": "Use /metrics for Prometheus format",
            "threats_detected": "Streamed via /ws/threats",
            "alerts_open": ALERTS_GAUGE._value.get(),
            "ws_connections": WS_CONNECTIONS._value.get(),
        },
    }
