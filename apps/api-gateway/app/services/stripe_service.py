import stripe
from app.core.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    async def create_customer(self, email: str, name: str) -> str:
        if settings.ENVIRONMENT == "development":
            return f"cus_mock_{email.replace('@', '_')}"
        customer = stripe.Customer.create(email=email, name=name)
        return customer.id

    async def create_subscription(self, customer_id: str, price_id: str) -> dict:
        if settings.ENVIRONMENT == "development":
            return {"id": f"sub_mock_{customer_id}", "status": "active"}
        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": price_id}],
            payment_behavior="default_incomplete",
            expand=["latest_invoice.payment_intent"],
        )
        return subscription

    async def cancel_subscription(self, subscription_id: str):
        if settings.ENVIRONMENT == "development":
            return {"id": subscription_id, "status": "canceled"}
        return stripe.Subscription.delete(subscription_id)

    async def create_portal_session(self, customer_id: str, return_url: str) -> str:
        if settings.ENVIRONMENT == "development":
            return f"https://billing.stripe.com/mock/{customer_id}"
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return session.url


stripe_svc = StripeService()
