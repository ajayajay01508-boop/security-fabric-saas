"""
Lightweight metrics helpers shared across all Python services.
Services that want Prometheus metrics import from here rather than
duplicating Counter/Histogram definitions.

Usage:
    from shared.python_utils.metrics import service_metrics
    service_metrics.record_kafka_consumed("raw-telemetry")
    service_metrics.record_inference_latency(0.045)
"""
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List

logger = logging.getLogger("metrics")


@dataclass
class ServiceMetrics:
    """
    Simple in-process metrics accumulator.
    Flushed to Prometheus via /metrics endpoint if prometheus_client is available,
    otherwise readable directly for logging and health checks.
    """
    service_name: str
    _counters: Dict[str, int] = field(default_factory=dict)
    _latencies: Dict[str, List[float]] = field(default_factory=dict)
    _start_time: float = field(default_factory=time.time)

    def inc(self, name: str, value: int = 1) -> None:
        self._counters[name] = self._counters.get(name, 0) + value

    def record_latency(self, name: str, seconds: float) -> None:
        if name not in self._latencies:
            self._latencies[name] = []
        self._latencies[name].append(seconds)
        # Keep last 1000 samples
        if len(self._latencies[name]) > 1000:
            self._latencies[name] = self._latencies[name][-1000:]

    def percentile(self, name: str, p: float) -> float:
        samples = self._latencies.get(name, [])
        if not samples:
            return 0.0
        s = sorted(samples)
        idx = int(len(s) * p / 100)
        return s[min(idx, len(s) - 1)]

    def avg_latency(self, name: str) -> float:
        samples = self._latencies.get(name, [])
        return sum(samples) / len(samples) if samples else 0.0

    # ── Semantic helpers ─────────────────────────────────────

    def record_kafka_consumed(self, topic: str, count: int = 1) -> None:
        self.inc(f"kafka.consumed.{topic}", count)

    def record_kafka_produced(self, topic: str, count: int = 1) -> None:
        self.inc(f"kafka.produced.{topic}", count)

    def record_kafka_error(self, topic: str) -> None:
        self.inc(f"kafka.errors.{topic}")

    def record_inference_latency(self, seconds: float) -> None:
        self.record_latency("inference", seconds)
        self.inc("inference.total")

    def record_threat_detected(self, severity: str) -> None:
        self.inc(f"threats.{severity}")
        self.inc("threats.total")

    def record_notification_sent(self, channel: str) -> None:
        self.inc(f"notifications.sent.{channel}")

    def record_notification_failed(self, channel: str) -> None:
        self.inc(f"notifications.failed.{channel}")

    def record_email_sent(self) -> None:
        self.record_notification_sent("email")

    def record_voice_call(self) -> None:
        self.record_notification_sent("voice")

    # ── Reporting ────────────────────────────────────────────

    def summary(self) -> dict:
        uptime = time.time() - self._start_time
        return {
            "service": self.service_name,
            "uptime_seconds": round(uptime, 1),
            "counters": dict(self._counters),
            "latencies": {
                name: {
                    "avg_ms":  round(self.avg_latency(name) * 1000, 2),
                    "p50_ms":  round(self.percentile(name, 50) * 1000, 2),
                    "p95_ms":  round(self.percentile(name, 95) * 1000, 2),
                    "p99_ms":  round(self.percentile(name, 99) * 1000, 2),
                    "samples": len(self._latencies[name]),
                }
                for name in self._latencies
            },
        }

    def log_summary(self) -> None:
        s = self.summary()
        logger.info(
            f"[{self.service_name}] uptime={s['uptime_seconds']}s "
            f"counters={s['counters']} "
            f"inference_p99={s['latencies'].get('inference', {}).get('p99_ms', 0)}ms"
        )


# Global singletons — each service gets its own name
def make_metrics(service_name: str) -> ServiceMetrics:
    return ServiceMetrics(service_name=service_name)
