"""
Admin router — superuser-only operations.
Requires is_superuser=True on the requesting user.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from pydantic import BaseModel
from typing import List
from datetime import datetime, timezone

from app.database import get_db
from app.models.user import User
from app.models.alert import Alert, AlertStatus
from app.models.subscription import Subscription
from app.core.security import get_current_active_user

router = APIRouter()


def require_superuser(current_user: User = Depends(get_current_active_user)) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser access required")
    return current_user


class UserSummary(BaseModel):
    id: int
    email: str
    full_name: str
    organization: str
    is_active: bool
    is_superuser: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SystemStats(BaseModel):
    total_users: int
    active_users: int
    total_alerts: int
    open_alerts: int
    resolved_alerts: int
    db_status: str


# ── Endpoints ─────────────────────────────────────────────────

@router.get("/users", response_model=List[UserSummary])
async def list_users(
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superuser),
):
    """List all registered users."""
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
    )
    return result.scalars().all()


@router.patch("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superuser),
):
    """Deactivate a user account."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    await db.commit()
    return {"message": f"User {user.email} deactivated"}


@router.patch("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superuser),
):
    """Reactivate a user account."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    await db.commit()
    return {"message": f"User {user.email} activated"}


@router.get("/stats", response_model=SystemStats)
async def system_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superuser),
):
    """System-wide statistics for ops dashboard."""
    total_users  = (await db.execute(select(func.count(User.id)))).scalar()
    active_users = (await db.execute(select(func.count(User.id)).where(User.is_active == True))).scalar()  # noqa: E712
    total_alerts = (await db.execute(select(func.count(Alert.id)))).scalar()
    open_alerts  = (await db.execute(
        select(func.count(Alert.id)).where(Alert.status == AlertStatus.OPEN)
    )).scalar()
    resolved     = (await db.execute(
        select(func.count(Alert.id)).where(Alert.status == AlertStatus.RESOLVED)
    )).scalar()

    # Quick DB health check
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "degraded"

    return SystemStats(
        total_users=total_users or 0,
        active_users=active_users or 0,
        total_alerts=total_alerts or 0,
        open_alerts=open_alerts or 0,
        resolved_alerts=resolved or 0,
        db_status=db_status,
    )


@router.delete("/alerts/bulk-resolve")
async def bulk_resolve_alerts(
    older_than_days: int = 30,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superuser),
):
    """Bulk resolve all open alerts older than N days."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    result = await db.execute(
        select(Alert).where(
            Alert.status == AlertStatus.OPEN,
            Alert.created_at < cutoff,
        )
    )
    alerts = result.scalars().all()
    count = len(alerts)
    for alert in alerts:
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    return {"resolved": count, "older_than_days": older_than_days}
