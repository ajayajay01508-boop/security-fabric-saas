"""Fast, deterministic unit tests for the stdlib load-test harness."""

import importlib.util
import json
from pathlib import Path

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
