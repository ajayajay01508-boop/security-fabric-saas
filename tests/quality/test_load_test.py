"""Fast, deterministic unit tests for the stdlib load-test harness."""

import importlib.util
import json
import threading
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[2] / "scripts" / "load-test.py"
SPEC = importlib.util.spec_from_file_location("load_test", MODULE_PATH)
load_test = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(load_test)


def test_stats_records_success_and_errors():
    stats = load_test.Stats()
    stats.record(10, 200)
    stats.record(20, 503)
    assert (stats.total, stats.success, stats.errors) == (2, 1, 1)
    assert dict(stats.status_codes) == {200: 1, 503: 1}


def test_percentiles_and_average_are_deterministic():
    stats = load_test.Stats()
    for latency in [10, 20, 30, 40, 50]:
        stats.record(latency, 200)
    assert stats.avg == 30
    assert stats.percentile(50) == 30
    assert stats.percentile(99) == 50


def test_empty_stats_have_zero_latency():
    stats = load_test.Stats()
    assert stats.avg == 0
    assert stats.percentile(95) == 0


def test_http_serializes_json_and_records_status(monkeypatch):
    captured = {}

    class Response:
        status = 202

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return b"{}"

    def fake_urlopen(request, timeout):
        captured["body"] = json.loads(request.data)
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(load_test.urllib.request, "urlopen", fake_urlopen)
    status, latency = load_test.http("POST", "https://example.test/events", {"event": 1})
    assert status == 202
    assert captured == {"body": {"event": 1}, "timeout": 10.0}
    assert latency >= 0


def test_http_converts_transport_failures_to_status_zero(monkeypatch):
    monkeypatch.setattr(
        load_test.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(TimeoutError("offline")),
    )
    status, latency = load_test.http("GET", "https://example.test/health")
    assert status == 0
    assert latency >= 0


def test_get_token_registers_and_authenticates(monkeypatch):
    monkeypatch.setattr(load_test, "http", lambda *_args, **_kwargs: (201, 1.0))

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({"access_token": "verified-token"}).encode()

    monkeypatch.setattr(load_test.urllib.request, "urlopen", lambda *_a, **_k: Response())
    assert load_test.get_token("https://api.test") == "verified-token"


def test_get_token_returns_none_on_transport_error(monkeypatch):
    monkeypatch.setattr(
        load_test.urllib.request,
        "urlopen",
        lambda *_a, **_k: (_ for _ in ()).throw(TimeoutError("offline")),
    )
    assert load_test.get_token("https://api.test") is None


@pytest.mark.parametrize("scenario", ["health", "auth", "alerts", "telemetry", "full"])
def test_each_worker_scenario_records_a_response(monkeypatch, scenario):
    stop = threading.Event()

    class OneRequestStats(load_test.Stats):
        def record(self, latency_ms, status):
            super().record(latency_ms, status)
            stop.set()

    monkeypatch.setattr(load_test, "http", lambda *_a, **_k: (200, 3.0))
    if scenario == "full":
        import random
        monkeypatch.setattr(random, "choice", lambda _choices: "health")

    stats = OneRequestStats()
    load_test.worker_loop("https://api.test", scenario, "token", stats, stop)
    assert stats.total == 1
    assert stats.success == 1


def test_load_test_enforces_error_rate_threshold(monkeypatch):
    def failing_worker(_url, _scenario, _token, stats, stop, _think_time):
        stats.record(5.0, 500)
        stop.set()

    monkeypatch.setattr(load_test, "worker_loop", failing_worker)
    monkeypatch.setattr(load_test, "get_token", lambda _url: "token")
    assert load_test.run_load_test("https://api.test", 1, 0, "auth") == 1


def test_load_test_passes_healthy_results(monkeypatch):
    def passing_worker(_url, _scenario, _token, stats, stop, _think_time):
        stats.record(5.0, 200)
        stop.set()

    monkeypatch.setattr(load_test, "worker_loop", passing_worker)
    assert load_test.run_load_test("https://api.test", 1, 0, "health") == 0
