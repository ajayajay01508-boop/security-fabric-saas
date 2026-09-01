import uuid

import pytest


@pytest.mark.asyncio
async def test_generates_correlation_id_and_security_headers(client):
    response = await client.get("/health")
    assert response.status_code == 200
    uuid.UUID(response.headers["x-request-id"])
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


@pytest.mark.asyncio
async def test_preserves_caller_correlation_id(client):
    response = await client.get("/health", headers={"X-Request-ID": "trace-test-123"})
    assert response.headers["x-request-id"] == "trace-test-123"


@pytest.mark.asyncio
async def test_protected_endpoint_rejects_missing_bearer_token(client):
    response = await client.get("/auth/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_rejects_malformed_bearer_token(client):
    response = await client.get("/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"
