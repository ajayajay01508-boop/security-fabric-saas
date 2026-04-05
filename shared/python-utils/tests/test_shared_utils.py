"""
Tests for shared/python-utils/*.py
Pure Python — no external dependencies.
"""
import sys, os, time, random, json, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared', 'python-utils'))


# ══ logging.py ═══════════════════════════════════════════════

class TestJSONFormatter:
    def test_get_logger_returns_logger(self):
        from logging import get_logger as _  # fallback
        import importlib.util, pathlib
        spec = importlib.util.spec_from_file_location(
            "sf_logging",
            pathlib.Path(__file__).parent.parent.parent.parent / "shared/python-utils/logging.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        logger = mod.get_logger("test")
        assert isinstance(logger, logging.Logger)

    def test_json_formatter_output(self):
        import importlib.util, pathlib, io
        spec = importlib.util.spec_from_file_location(
            "sf_logging2",
            pathlib.Path(__file__).parent.parent.parent.parent / "shared/python-utils/logging.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(mod.JSONFormatter())
        logger = logging.getLogger("test_json_fmt")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.info("hello world", extra={"trace_id": "abc123"})

        output = stream.getvalue().strip()
        parsed = json.loads(output)
        assert parsed["msg"] == "hello world"
        assert parsed["level"] == "INFO"
        assert "ts" in parsed

    def test_extra_fields_included(self):
        import importlib.util, pathlib, io
        spec = importlib.util.spec_from_file_location(
            "sf_logging3",
            pathlib.Path(__file__).parent.parent.parent.parent / "shared/python-utils/logging.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(mod.JSONFormatter())
        logger = logging.getLogger("test_extra")
        logger.handlers = [handler]
        logger.setLevel(logging.DEBUG)
        logger.info("msg", extra={"user_id": 42, "action": "login"})

        parsed = json.loads(stream.getvalue().strip())
        assert parsed.get("user_id") == 42
        assert parsed.get("action") == "login"


# ══ security.py ══════════════════════════════════════════════

class TestRateLimitDecorator:
    def test_rate_limit_allows_under_limit(self):
        import importlib.util, pathlib, asyncio
        spec = importlib.util.spec_from_file_location(
            "sf_sec",
            pathlib.Path(__file__).parent.parent.parent.parent / "shared/python-utils/security.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        @mod.rate_limit(max_calls=5, period=60)
        async def dummy():
            return "ok"

        for _ in range(5):
            result = asyncio.get_event_loop().run_until_complete(dummy())
            assert result == "ok"

    def test_rate_limit_blocks_over_limit(self):
        import importlib.util, pathlib, asyncio
        from fastapi import HTTPException
        spec = importlib.util.spec_from_file_location(
            "sf_sec2",
            pathlib.Path(__file__).parent.parent.parent.parent / "shared/python-utils/security.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Fresh function per test to get fresh store entry
        @mod.rate_limit(max_calls=3, period=60)
        async def limited_fn():
            return "ok"

        async def run():
            for _ in range(3):
                await limited_fn()
            # 4th call should raise 429
            with __import__('pytest').raises(HTTPException) as exc_info:
                await limited_fn()
            assert exc_info.value.status_code == 429

        asyncio.get_event_loop().run_until_complete(run())


class TestRequireRoleDecorator:
    def test_require_role_allows_matching(self):
        import importlib.util, pathlib, asyncio
        spec = importlib.util.spec_from_file_location(
            "sf_sec3",
            pathlib.Path(__file__).parent.parent.parent.parent / "shared/python-utils/security.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        class MockUser:
            role = "admin"
            is_superuser = False

        @mod.require_role("admin")
        async def admin_fn(current_user=None):
            return "admin ok"

        result = asyncio.get_event_loop().run_until_complete(
            admin_fn(current_user=MockUser())
        )
        assert result == "admin ok"

    def test_require_role_blocks_wrong_role(self):
        import importlib.util, pathlib, asyncio
        from fastapi import HTTPException
        spec = importlib.util.spec_from_file_location(
            "sf_sec4",
            pathlib.Path(__file__).parent.parent.parent.parent / "shared/python-utils/security.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        class MockUser:
            role = "viewer"
            is_superuser = False

        @mod.require_role("admin")
        async def admin_fn(current_user=None):
            return "admin ok"

        async def run():
            with __import__('pytest').raises(HTTPException) as exc:
                await admin_fn(current_user=MockUser())
            assert exc.value.status_code == 403

        asyncio.get_event_loop().run_until_complete(run())

    def test_superuser_bypasses_role_check(self):
        import importlib.util, pathlib, asyncio
        spec = importlib.util.spec_from_file_location(
            "sf_sec5",
            pathlib.Path(__file__).parent.parent.parent.parent / "shared/python-utils/security.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        class SuperUser:
            role = "viewer"
            is_superuser = True

        @mod.require_role("admin")
        async def admin_fn(current_user=None):
            return "ok"

        result = asyncio.get_event_loop().run_until_complete(
            admin_fn(current_user=SuperUser())
        )
        assert result == "ok"


# ══ metrics.py ═══════════════════════════════════════════════

class TestServiceMetrics:
    def _load(self):
        import importlib.util, pathlib
        spec = importlib.util.spec_from_file_location(
            "sf_metrics",
            pathlib.Path(__file__).parent.parent.parent.parent / "shared/python-utils/metrics.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_make_metrics_factory(self):
        mod = self._load()
        m = mod.make_metrics("test-service")
        assert m.service_name == "test-service"
        assert m._counters == {}

    def test_inc_counter(self):
        mod = self._load()
        m = mod.make_metrics("svc")
        m.inc("requests")
        m.inc("requests")
        assert m._counters["requests"] == 2

    def test_record_latency(self):
        mod = self._load()
        m = mod.make_metrics("svc")
        m.record_latency("inference", 0.05)
        m.record_latency("inference", 0.10)
        assert len(m._latencies["inference"]) == 2

    def test_percentile(self):
        mod = self._load()
        m = mod.make_metrics("svc")
        for v in [0.01, 0.05, 0.10, 0.20, 0.50]:
            m.record_latency("op", v)
        p50 = m.percentile("op", 50)
        p99 = m.percentile("op", 99)
        assert p50 <= p99
        assert 0.0 < p50 < 1.0

    def test_avg_latency(self):
        mod = self._load()
        m = mod.make_metrics("svc")
        m.record_latency("op", 0.1)
        m.record_latency("op", 0.3)
        assert abs(m.avg_latency("op") - 0.2) < 0.001

    def test_record_inference_latency(self):
        mod = self._load()
        m = mod.make_metrics("svc")
        m.record_inference_latency(0.045)
        assert m._counters.get("inference.total") == 1
        assert len(m._latencies.get("inference", [])) == 1

    def test_record_threat_detected(self):
        mod = self._load()
        m = mod.make_metrics("svc")
        m.record_threat_detected("critical")
        m.record_threat_detected("high")
        assert m._counters.get("threats.critical") == 1
        assert m._counters.get("threats.high") == 1
        assert m._counters.get("threats.total") == 2

    def test_summary_structure(self):
        mod = self._load()
        m = mod.make_metrics("svc")
        m.inc("reqs", 10)
        m.record_latency("inference", 0.05)
        s = m.summary()
        assert s["service"] == "svc"
        assert "uptime_seconds" in s
        assert s["counters"]["reqs"] == 10
        assert "inference" in s["latencies"]

    def test_cap_at_1000_latency_samples(self):
        mod = self._load()
        m = mod.make_metrics("svc")
        for _ in range(1500):
            m.record_latency("op", random.uniform(0, 1))
        assert len(m._latencies["op"]) == 1000

    def test_kafka_helpers(self):
        mod = self._load()
        m = mod.make_metrics("svc")
        m.record_kafka_consumed("raw-telemetry", 5)
        m.record_kafka_produced("threat-events", 2)
        m.record_kafka_error("raw-telemetry")
        assert m._counters["kafka.consumed.raw-telemetry"] == 5
        assert m._counters["kafka.produced.threat-events"] == 2
        assert m._counters["kafka.errors.raw-telemetry"] == 1

    def test_notification_helpers(self):
        mod = self._load()
        m = mod.make_metrics("svc")
        m.record_email_sent()
        m.record_voice_call()
        m.record_notification_failed("push")
        assert m._counters["notifications.sent.email"] == 1
        assert m._counters["notifications.sent.voice"] == 1
        assert m._counters["notifications.failed.push"] == 1

    def test_stress_100_records(self):
        mod = self._load()
        m = mod.make_metrics("stress-svc")
        for _ in range(100):
            m.record_inference_latency(random.uniform(0.001, 0.5))
            m.record_threat_detected(random.choice(["critical","high","medium","low"]))
            m.inc("requests")
        assert m._counters["inference.total"] == 100
        assert m._counters["threats.total"] == 100
        assert m._counters["requests"] == 100
        s = m.summary()
        assert s["counters"]["requests"] == 100
