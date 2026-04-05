import pytest
import uuid
from app.models.alert import Alert, SeverityLevel, AlertStatus
from sqlalchemy.ext.asyncio import AsyncSession
from tests.conftest import TestSession


async def insert_alert(severity=SeverityLevel.HIGH, status=AlertStatus.OPEN, classification="Test Threat"):
    async with TestSession() as session:
        alert = Alert(
            threat_id=str(uuid.uuid4()),
            severity=severity,
            status=status,
            classification=classification,
            source_ip="1.2.3.4",
            destination_ip="10.0.0.1",
            source_port=54321,
            destination_port=22,
            protocol="TCP",
            confidence_score=0.87,
            description="Test alert",
        )
        session.add(alert)
        await session.commit()
        await session.refresh(alert)
        return alert


@pytest.mark.asyncio
async def test_list_alerts_empty(client, auth_headers):
    r = await client.get("/alerts", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_alerts_with_data(client, auth_headers):
    await insert_alert(SeverityLevel.CRITICAL)
    await insert_alert(SeverityLevel.HIGH)
    r = await client.get("/alerts", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 2


@pytest.mark.asyncio
async def test_list_alerts_filter_by_severity(client, auth_headers):
    await insert_alert(SeverityLevel.CRITICAL)
    await insert_alert(SeverityLevel.LOW)
    r = await client.get("/alerts?severity=critical", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["severity"] == "critical"


@pytest.mark.asyncio
async def test_list_alerts_filter_by_status(client, auth_headers):
    await insert_alert(status=AlertStatus.OPEN)
    await insert_alert(status=AlertStatus.RESOLVED)
    r = await client.get("/alerts?status=resolved", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["status"] == "resolved"


@pytest.mark.asyncio
async def test_list_alerts_pagination(client, auth_headers):
    for _ in range(10):
        await insert_alert()
    r1 = await client.get("/alerts?limit=5&offset=0", headers=auth_headers)
    r2 = await client.get("/alerts?limit=5&offset=5", headers=auth_headers)
    assert len(r1.json()) == 5
    assert len(r2.json()) == 5
    # Ensure different pages
    ids1 = {a["id"] for a in r1.json()}
    ids2 = {a["id"] for a in r2.json()}
    assert ids1.isdisjoint(ids2)


@pytest.mark.asyncio
async def test_get_alert_by_id(client, auth_headers):
    alert = await insert_alert(classification="Port Scan")
    r = await client.get(f"/alerts/{alert.id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["classification"] == "Port Scan"
    assert r.json()["id"] == alert.id


@pytest.mark.asyncio
async def test_get_alert_not_found(client, auth_headers):
    r = await client.get("/alerts/99999", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_acknowledge_alert(client, auth_headers):
    alert = await insert_alert(status=AlertStatus.OPEN)
    r = await client.patch(
        f"/alerts/{alert.id}/acknowledge",
        json={"note": "Investigating"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "acknowledged"
    assert data["acknowledged_at"] is not None


@pytest.mark.asyncio
async def test_resolve_alert(client, auth_headers):
    alert = await insert_alert(status=AlertStatus.OPEN)
    r = await client.patch(f"/alerts/{alert.id}/resolve", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "resolved"
    assert data["resolved_at"] is not None


@pytest.mark.asyncio
async def test_alert_stats_structure(client, auth_headers):
    await insert_alert(SeverityLevel.CRITICAL)
    await insert_alert(SeverityLevel.HIGH)
    await insert_alert(SeverityLevel.MEDIUM)
    await insert_alert(SeverityLevel.LOW, status=AlertStatus.RESOLVED)
    r = await client.get("/alerts/stats", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    for key in ["total", "critical", "high", "medium", "low", "open", "acknowledged", "resolved"]:
        assert key in data, f"Missing key: {key}"
    assert data["total"] == 4
    assert data["critical"] == 1
    assert data["high"] == 1
    assert data["resolved"] == 1


@pytest.mark.asyncio
async def test_alerts_require_auth(client):
    for method, path in [
        ("get",   "/alerts"),
        ("get",   "/alerts/1"),
        ("get",   "/alerts/stats"),
        ("patch", "/alerts/1/acknowledge"),
        ("patch", "/alerts/1/resolve"),
    ]:
        r = await getattr(client, method)(path)
        assert r.status_code == 401, f"{method.upper()} {path} should return 401"


@pytest.mark.asyncio
async def test_list_alerts_limit_max(client, auth_headers):
    """Limit cannot exceed 500."""
    r = await client.get("/alerts?limit=501", headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_alert_fields_present(client, auth_headers):
    await insert_alert(SeverityLevel.HIGH, classification="SQL Injection")
    r = await client.get("/alerts", headers=auth_headers)
    assert r.status_code == 200
    alert = r.json()[0]
    for field in ["id", "threat_id", "severity", "status", "classification",
                  "source_ip", "destination_ip", "confidence_score", "created_at"]:
        assert field in alert, f"Missing field: {field}"
