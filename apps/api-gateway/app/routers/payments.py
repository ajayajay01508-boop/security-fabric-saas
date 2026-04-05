from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.subscription import Subscription, PlanType, SubscriptionStatus
from app.core.security import get_current_active_user
from app.services.stripe_service import stripe_svc

router = APIRouter()

PLAN_PRICES = {
    PlanType.STARTER: {"price": 4900, "name": "Starter"},
    PlanType.PROFESSIONAL: {"price": 14900, "name": "Professional"},
    PlanType.ENTERPRISE: {"price": 49900, "name": "Enterprise"},
}


class SubscribeRequest(BaseModel):
    plan: PlanType
    payment_method_id: Optional[str] = None


class SubscriptionResponse(BaseModel):
    plan: PlanType
    status: SubscriptionStatus
    stripe_subscription_id: Optional[str]

    class Config:
        from_attributes = True


@router.post("/subscribe")
async def subscribe(
    req: SubscribeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if req.plan == PlanType.FREE:
        raise HTTPException(status_code=400, detail="Cannot subscribe to free plan via this endpoint")

    result = await db.execute(select(Subscription).where(Subscription.user_id == current_user.id))
    sub = result.scalar_one_or_none()

    # Mock subscription for development
    if sub:
        sub.plan = req.plan
        sub.status = SubscriptionStatus.ACTIVE
    else:
        sub = Subscription(user_id=current_user.id, plan=req.plan, status=SubscriptionStatus.ACTIVE)
        db.add(sub)

    await db.commit()
    return {"status": "subscribed", "plan": req.plan}


@router.get("/status", response_model=SubscriptionResponse)
async def get_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Subscription).where(Subscription.user_id == current_user.id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="No subscription found")
    return sub


@router.post("/portal")
async def billing_portal(current_user: User = Depends(get_current_active_user)):
    return {
        "url": f"https://billing.stripe.com/p/session/mock_{current_user.id}",
        "message": "Redirect user to this URL for billing management",
    }


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    body = await request.body()
    # In production: verify stripe_signature
    return {"received": True}
