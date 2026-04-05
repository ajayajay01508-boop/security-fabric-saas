"""
Tests for the /admin router.
Verifies superuser-only access enforcement and all admin operations.
"""
import pytest
import pytest_asyncio
from app.models.user import User
from app.models.alert import Alert, SeverityLevel, AlertStatus
from tests.conftest import TestSession
import uuid


async def make_superuser(client, email="super@example.com"):
    """Register a user and promote to superuser directly in DB."""
    await client.post("/auth/register", json={
        "email": email, "password": "superpass123",
        "full_name": "Super User", "organization": "Ops",
    })
    async with TestSession() as session:
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        user.is_superuser = True
        await session.commit()
    resp = await client.post(
        "/auth/token",
        data={"username": email, "password": "superpass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ── Access control ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_requires_superuser(client, auth_headers):
    """Regular user gets 403 on all admin endpoints."""
    for method, path in [
        ("get",   "/admin/users"),
        ("get",   "/admin/stats"),
    ]:
        r = await getattr(client, method)(path, headers=auth_headers)
        assert r.status_code == 403, f"{method.upper()} {path} should be 403"


@pytest.mark.asyncio
async def test_admin_requires_auth(client):
    """Unauthenticated requests get 401."""
    for path in ["/admin/users", "/admin/stats"]:
        r = await client.get(path)
        assert r.status_code == 401


# ── /admin/users ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_users_as_superuser(client):
    super_headers = await make_superuser(client, "list_super@example.com")

    # Create a few regular users
    for i in range(3):
        await client.post("/auth/register", json={
            "email": f"user{i}@example.com",
            "password": "pass123",
            "full_name": f"User {i}",
            "organization": "",
        })

    r = await client.get("/admin/users", headers=super_headers)
    assert r.status_code == 200
    users = r.json()
    assert isinstance(users, list)
    assert len(users) >= 4  # superuser + 3 regular users
    # Check fields
    for u in users:
        for field in ["id", "email", "full_name", "is_active", "is_superuser", "created_at"]:
            assert field in u


@pytest.mark.asyncio
async def test_deactivate_user(client):
    super_headers = await make_superuser(client, "deact_super@example.com")

    # Register target user
    r = await client.post("/auth/register", json={
        "email": "target@example.com", "password": "pass",
        "full_name": "Target", "organization": "",
    })
    target_id = r.json()["id"]

    # Deactivate
    r = await client.patch(f"/admin/users/{target_id}/deactivate", headers=super_headers)
    assert r.status_code == 200
    assert "deactivated" in r.json()["message"].lower()

    # Verify user is inactive
    r = await client.get("/admin/users", headers=super_headers)
    target = next((u for u in r.json() if u["id"] == target_id), None)
    assert target is not None
    assert target["is_active"] is False


@pytest.mark.asyncio
async def test_activate_user(client):
    super_headers = await make_superuser(client, "act_super@example.com")

    r = await client.post("/auth/register", json={
        "email": "inactive@example.com", "password": "pass",
        "full_name": "Inactive", "organization": "",
    })
    user_id = r.json()["id"]

    # Deactivate then reactivate
    await client.patch(f"/admin/users/{user_id}/deactivate", headers=super_headers)
    r = await client.patch(f"/admin/users/{user_id}/activate", headers=super_headers)
    assert r.status_code == 200

    r = await client.get("/admin/users", headers=super_headers)
    user = next((u for u in r.json() if u["id"] == user_id), None)
    assert user["is_active"] is True


@pytest.mark.asyncio
async def test_cannot_deactivate_self(client):
    """Superuser cannot deactivate their own account."""
    super_headers = await make_superuser(client, "selfdeact@example.com")

    # Get own user ID
    me = await client.get("/auth/me", headers=super_headers)
    my_id = me.json()["id"]

    r = await client.patch(f"/admin/users/{my_id}/deactivate", headers=super_headers)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_deactivate_nonexistent_user(client):
    super_headers = await make_superuser(client, "noent_super@example.com")
    r = await client.patch("/admin/users/99999/deactivate", headers=super_headers)
    assert r.status_code == 404


# ── /admin/stats ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_system_stats_structure(client):
    super_headers = await make_superuser(client, "stats_super@example.com")
    r = await client.get("/admin/stats", headers=super_headers)
    assert r.status_code == 200
    data = r.json()
    for field in ["total_users", "active_users", "total_alerts",
                  "open_alerts", "resolved_alerts", "db_status"]:
        assert field in data
    assert data["db_status"] == "healthy"
    assert data["total_users"] >= 1


@pytest.mark.asyncio
async def test_system_stats_counts_alerts(client):
    super_headers = await make_superuser(client, "statsalerts@example.com")

    # Insert alerts
    async with TestSession() as session:
        for i in range(3):
            session.add(Alert(
                threat_id=str(uuid.uuid4()),
                severity=SeverityLevel.HIGH,
                status=AlertStatus.OPEN,
                classification="Test",
                source_ip="1.2.3.4",
                destination_ip="5.6.7.8",
                source_port=1234,
                destination_port=80,
                protocol="TCP",
                confidence_score=0.9,
                description="Admin test alert",
            ))
        await session.commit()

    r = await client.get("/admin/stats", headers=super_headers)
    assert r.json()["open_alerts"] >= 3
    assert r.json()["total_alerts"] >= 3


# ── /admin/alerts/bulk-resolve ────────────────────────────────

@pytest.mark.asyncio
async def test_bulk_resolve_old_alerts(client):
    super_headers = await make_superuser(client, "bulkres@example.com")

    # Insert old alert (backdated)
    from datetime import datetime, timedelta, timezone
    async with TestSession() as session:
        old_alert = Alert(
            threat_id=str(uuid.uuid4()),
            severity=SeverityLevel.LOW,
            status=AlertStatus.OPEN,
            classification="Old Threat",
            source_ip="1.1.1.1",
            destination_ip="2.2.2.2",
            source_port=1234,
            destination_port=80,
            protocol="TCP",
            confidence_score=0.5,
            description="Old alert",
            created_at=datetime.now(timezone.utc) - timedelta(days=35),
        )
        session.add(old_alert)
        await session.commit()

    r = await client.delete("/admin/alerts/bulk-resolve?older_than_days=30",
                            headers=super_headers)
    assert r.status_code == 200
    data = r.json()
    assert "resolved" in data
    assert data["resolved"] >= 1
