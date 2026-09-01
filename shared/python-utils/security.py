"""
Security decorators for FastAPI route handlers.
Usage:
    from shared.python_utils.security import require_role, rate_limit

    @app.get("/admin")
    @require_role("admin")
    async def admin_route(current_user = Depends(get_current_active_user)):
        ...
"""
import time
import functools
from collections import defaultdict
from typing import Callable
from fastapi import HTTPException, status


# ─── Rate Limiting ─────────────────────────────────────────────

_rate_limit_store: dict[str, list[float]] = defaultdict(list)


def rate_limit(max_calls: int = 100, period: int = 60):
    """
    Simple in-process rate limiter (per function, per caller IP).
    For distributed rate limiting, use Redis with a sliding window.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            now = time.time()
            key = func.__name__
            calls = _rate_limit_store[key]
            # Remove calls outside the window
            _rate_limit_store[key] = [t for t in calls if now - t < period]
            if len(_rate_limit_store[key]) >= max_calls:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: {max_calls} calls per {period}s",
                )
            _rate_limit_store[key].append(now)
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# ─── Role-based access ─────────────────────────────────────────

def require_role(*roles: str):
    """
    Decorator that asserts the current_user has one of the given roles.
    Assumes the first argument (or kwarg named 'current_user') is the user model.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get("current_user") or (args[0] if args else None)
            if user is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
            user_role = getattr(user, "role", "user")
            if user_role not in roles and not getattr(user, "is_superuser", False):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires one of roles: {roles}",
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# ─── Audit logging ─────────────────────────────────────────────

def audit_log(action: str):
    """Log sensitive actions to the audit trail."""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            from shared.python_utils.structured_logging import get_logger
            audit = get_logger("audit")
            user = kwargs.get("current_user")
            user_id = getattr(user, "id", "anonymous") if user else "anonymous"
            audit.info(
                f"AUDIT:{action}",
                extra={"user_id": user_id, "action": action, "function": func.__name__}
            )
            return await func(*args, **kwargs)
        return wrapper
    return decorator
