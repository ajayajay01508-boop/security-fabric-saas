"""Fast, deterministic unit tests for the stdlib load-test harness."""

import importlib.util
import json
import threading
from types import SimpleNamespace
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


def test_http_returns_http_error_status(monkeypatch):
    error = load_test.urllib.error.HTTPError(
        "https://example.test", 429, "limited", {}, None
    )
    monkeypatch.setattr(load_test.urllib.request, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(error))
    status, _latency = load_test.http("GET", "https://example.test", headers={"X-Test": "yes"})
    assert status == 429


def test_get_token_success(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"access_token":"token-123"}'

    monkeypatch.setattr(load_test, "http", lambda *_a, **_k: (201, 1.0))
    monkeypatch.setattr(load_test.urllib.request, "urlopen", lambda *_a, **_k: Response())
    assert load_test.get_token("https://api.test") == "token-123"


def test_get_token_failure_returns_none(monkeypatch, capsys):
    monkeypatch.setattr(load_test, "http", lambda *_a, **_k: (500, 1.0))
    monkeypatch.setattr(
        load_test.urllib.request,
        "urlopen",
        lambda *_a, **_k: (_ for _ in ()).throw(OSError("offline")),
    )
    assert load_test.get_token("https://api.test") is None
    assert "Could not get token" in capsys.readouterr().out


@pytest.mark.parametrize("scenario", ["health", "auth", "alerts", "telemetry"])
def test_worker_loop_routes_named_scenarios(monkeypatch, scenario):
    stop = threading.Event()
    calls = []

    def fake_http(method, url, data=None, headers=None, timeout=10.0):
        calls.append((method, url, data, headers))
        stop.set()
        return 200, 2.0

    monkeypatch.setattr(load_test, "http", fake_http)
    stats = load_test.Stats()
    load_test.worker_loop("https://api.test", scenario, "token", stats, stop)
    assert stats.success == 1
    assert scenario in calls[0][1]


@pytest.mark.parametrize("choice", ["health", "auth", "alerts", "telemetry"])
def test_worker_loop_full_scenario_routes_each_choice(monkeypatch, choice):
    stop = threading.Event()
    calls = []

    def fake_http(method, url, data=None, headers=None, timeout=10.0):
        calls.append((method, url))
        stop.set()
        return 204, 1.0

    monkeypatch.setattr(load_test, "http", fake_http)
    monkeypatch.setattr("random.choice", lambda _values: choice)
    stats = load_test.Stats()
    load_test.worker_loop("https://api.test", "full", None, stats, stop)
    assert stats.success == 1
    assert choice in calls[0][1]


def test_print_progress_handles_zero_elapsed(capsys):
    load_test.print_progress(load_test.Stats(), 0, 10)
    assert "0.0s/10s" in capsys.readouterr().out


class NoopThread:
    def __init__(self, *args, **kwargs):
        self.started = False

    def start(self):
        self.started = True

    def join(self, timeout=None):
        return timeout


def prepare_run(monkeypatch, stats):
    monkeypatch.setattr(load_test, "Stats", lambda: stats)
    monkeypatch.setattr(load_test.threading, "Thread", NoopThread)
    monkeypatch.setattr(load_test.time, "monotonic", lambda: 1.0)
    monkeypatch.setattr(load_test, "print_progress", lambda *_a, **_k: None)


def test_run_load_test_success_and_token_path(monkeypatch):
    stats = load_test.Stats(total=100, success=100, latencies=[20] * 100)
    prepare_run(monkeypatch, stats)
    monkeypatch.setattr(load_test, "get_token", lambda _url: "token")
    assert load_test.run_load_test("https://api.test", 2, 0, "full") == 0


def test_run_load_test_rejects_high_error_rate(monkeypatch):
    stats = load_test.Stats(total=100, success=90, errors=10, latencies=[20] * 100)
    prepare_run(monkeypatch, stats)
    assert load_test.run_load_test("https://api.test", 0, 0, "health") == 1


def test_run_load_test_rejects_high_p99(monkeypatch):
    stats = load_test.Stats(total=10, success=10, latencies=[3000] * 10)
    prepare_run(monkeypatch, stats)
    assert load_test.run_load_test("https://api.test", 0, 0, "health") == 1


def test_main_exits_with_load_test_status(monkeypatch):
    args = SimpleNamespace(url="https://api.test", workers=1, duration=0, scenario="health")
    monkeypatch.setattr(load_test.argparse.ArgumentParser, "parse_args", lambda _self: args)
    monkeypatch.setattr(load_test, "run_load_test", lambda *_a: 7)
    with pytest.raises(SystemExit) as exc:
        load_test.main()
    assert exc.value.code == 7
