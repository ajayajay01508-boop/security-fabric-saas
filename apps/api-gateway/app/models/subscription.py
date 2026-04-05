from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func, Enum
from app.database import Base
import enum


class PlanType(str, enum.Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan = Column(Enum(PlanType), default=PlanType.FREE)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    stripe_subscription_id = Column(String, nullable=True)
    stripe_price_id = Column(String, nullable=True)
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
