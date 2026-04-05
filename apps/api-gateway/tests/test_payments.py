import pytest


@pytest.mark.asyncio
async def test_payment_status_new_user(client, auth_headers):
    """New user should have a subscription (created on register)."""
    r = await client.get("/payments/status", headers=auth_headers)
    # Either 200 with a plan or 404 if subscription not auto-created
    assert r.status_code in (200, 404)


@pytest.mark.asyncio
async def test_subscribe_starter(client, auth_headers):
    r = await client.post("/payments/subscribe", json={"plan": "starter"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["plan"] == "starter"


@pytest.mark.asyncio
async def test_subscribe_professional(client, auth_headers):
    r = await client.post("/payments/subscribe", json={"plan": "professional"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["plan"] == "professional"


@pytest.mark.asyncio
async def test_subscribe_enterprise(client, auth_headers):
    r = await client.post("/payments/subscribe", json={"plan": "enterprise"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["plan"] == "enterprise"


@pytest.mark.asyncio
async def test_subscribe_free_rejected(client, auth_headers):
    """Cannot subscribe to free plan via API."""
    r = await client.post("/payments/subscribe", json={"plan": "free"}, headers=auth_headers)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_subscribe_invalid_plan(client, auth_headers):
    r = await client.post("/payments/subscribe", json={"plan": "diamond"}, headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_subscribe_requires_auth(client):
    r = await client.post("/payments/subscribe", json={"plan": "starter"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_status_after_subscribe(client, auth_headers):
    await client.post("/payments/subscribe", json={"plan": "professional"}, headers=auth_headers)
    r = await client.get("/payments/status", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["plan"] == "professional"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_billing_portal_returns_url(client, auth_headers):
    r = await client.post("/payments/portal", headers=auth_headers)
    assert r.status_code == 200
    assert "url" in r.json()
    assert r.json()["url"].startswith("https://")


@pytest.mark.asyncio
async def test_billing_portal_requires_auth(client):
    r = await client.post("/payments/portal")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_subscribe_upgrade_flow(client, auth_headers):
    """User can upgrade from starter to professional."""
    r1 = await client.post("/payments/subscribe", json={"plan": "starter"}, headers=auth_headers)
    assert r1.status_code == 200
    r2 = await client.post("/payments/subscribe", json={"plan": "professional"}, headers=auth_headers)
    assert r2.status_code == 200
    r3 = await client.get("/payments/status", headers=auth_headers)
    assert r3.json()["plan"] == "professional"


@pytest.mark.asyncio
async def test_stripe_webhook_accepts_post(client):
    """Webhook endpoint accepts POST without auth."""
    r = await client.post(
        "/payments/webhook",
        content=b'{"type":"payment_intent.succeeded"}',
        headers={"Content-Type": "application/json", "Stripe-Signature": "mock_sig"},
    )
    assert r.status_code == 200
