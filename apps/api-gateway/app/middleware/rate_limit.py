"""
Sliding-window rate limiter middleware using Redis.
Falls back to in-process counter if Redis is unavailable.

Limits are per IP address. Configure per-route limits via
the X-Rate-Limit-* headers or the route-specific overrides dict.
"""
import time
import logging
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("rate_limit")

# Default: 200 requests per 60 seconds per IP
DEFAULT_LIMIT  = 200
DEFAULT_WINDOW = 60  # seconds

# Stricter limits for specific prefixes
ROUTE_LIMITS: dict[str, tuple[int, int]] = {
    "/auth/token":    (20, 60),   # 20 login attempts/min
    "/auth/register": (10, 60),   # 10 registrations/min
    "/telemetry/ingest/batch": (30, 60),  # 30 batch ingests/min
}

# In-process fallback store  {ip: [(timestamp, count), ...]}
_store: dict[str, list[float]] = defaultdict(list)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self._redis = redis_client

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _get_limit(self, path: str) -> tuple[int, int]:
        for prefix, (limit, window) in ROUTE_LIMITS.items():
            if path.startswith(prefix):
                return limit, window
        return DEFAULT_LIMIT, DEFAULT_WINDOW

    async def _check_redis(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        """Sliding window in Redis. Returns (allowed, remaining)."""
        try:
            pipe = self._redis._client.pipeline()
            now = time.time()
            window_start = now - window

            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, window + 1)
            results = await pipe.execute()

            count = results[1]
            remaining = max(0, limit - count - 1)
            return count < limit, remaining
        except Exception as e:
            logger.debug(f"Redis rate limit unavailable: {e}, using in-process fallback")
            return self._check_memory(key, limit, window)

    def _check_memory(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        now = time.time()
        window_start = now - window
        calls = [t for t in _store[key] if t > window_start]
        calls.append(now)
        _store[key] = calls
        count = len(calls)
        return count <= limit, max(0, limit - count)

    async def dispatch(self, request: Request, call_next):
        # Health and diagnostics must remain available during an incident, but
        # still expose a consistent header contract to clients and monitors.
        if request.url.path in ("/health", "/metrics", "/docs", "/redoc", "/openapi.json"):
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(DEFAULT_LIMIT)
            response.headers["X-RateLimit-Remaining"] = str(DEFAULT_LIMIT)
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + DEFAULT_WINDOW))
            return response

        ip = self._get_client_ip(request)
        path = request.url.path
        limit, window = self._get_limit(path)
        key = f"rl:{ip}:{path.replace('/', '_')}"

        if self._redis:
            allowed, remaining = await self._check_redis(key, limit, window)
        else:
            allowed, remaining = self._check_memory(key, limit, window)

        if not allowed:
            logger.warning(f"Rate limit exceeded: ip={ip} path={path}")
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded. Try again in {window} seconds."},
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + window)),
                    "Retry-After": str(window),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + window))
        return response
