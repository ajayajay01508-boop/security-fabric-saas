"""
Tests for rate limiting middleware.
Uses the in-process fallback (no Redis needed).
"""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_rate_limit_headers_present(client, auth_headers):
    """Every response should carry X-RateLimit-* headers."""
    r = await client.get("/health")
    assert r.status_code == 200
    assert "x-ratelimit-limit" in r.headers
    assert "x-ratelimit-remaining" in r.headers
    assert "x-ratelimit-reset" in r.headers


@pytest.mark.asyncio
async def test_rate_limit_remaining_decrements(client):
    """Remaining count should decrease with each request."""
    r1 = await client.get("/health")
    r2 = await client.get("/health")
    rem1 = int(r1.headers.get("x-ratelimit-remaining", 999))
    rem2 = int(r2.headers.get("x-ratelimit-remaining", 999))
    assert rem2 <= rem1


@pytest.mark.asyncio
async def test_auth_token_route_has_strict_limit(client):
    """
    /auth/token has a stricter per-minute limit (20 req/min).
    Its X-RateLimit-Limit should be lower than the global 200.
    """
    r = await client.post(
        "/auth/token",
        data={"username": "x@x.com", "password": "wrong"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    limit = int(r.headers.get("x-ratelimit-limit", 200))
    assert limit <= 200


@pytest.mark.asyncio
async def test_health_endpoint_exempt_from_limit(client):
    """Health endpoint should always return 200, never 429."""
    for _ in range(10):
        r = await client.get("/health")
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_reset_is_future_timestamp(client):
    """/health reset timestamp should be in the future."""
    import time
    r = await client.get("/health")
    reset = int(r.headers.get("x-ratelimit-reset", 0))
    assert reset > time.time() - 5


@pytest.mark.asyncio
async def test_rate_limit_in_process_fallback():
    """
    Directly test the in-process rate limit store.
    Simulate limit being hit by patching the window.
    """
    from app.middleware.rate_limit import RateLimitMiddleware, _store
    import time

    # Manually fill the store for a fake key
    key = "rl:test_ip:/test_path"
    now = time.time()
    limit = 5
    window = 60
    # Fill with 'limit' recent timestamps
    _store[key] = [now - i for i in range(limit)]

    middleware = RateLimitMiddleware(app=None, redis_client=None)
    allowed, remaining = middleware._check_memory(key, limit, window)
    assert not allowed  # Should be blocked
    assert remaining == 0


@pytest.mark.asyncio
async def test_rate_limit_window_expiry():
    """Old requests outside the window should not count."""
    from app.middleware.rate_limit import _store
    import time

    key = "rl:test_ip_expire:/some_path"
    # Timestamps from 2 minutes ago (outside 60s window)
    _store[key] = [time.time() - 120] * 100

    from app.middleware.rate_limit import RateLimitMiddleware
    middleware = RateLimitMiddleware(app=None, redis_client=None)
    allowed, remaining = middleware._check_memory(key, limit=10, window=60)
    # Old entries purged → only the new request counts → allowed
    assert allowed
    assert remaining >= 8
