"""
Shared pytest fixtures for all API Gateway tests.
Uses in-memory SQLite so no external services are needed.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import Base, get_db

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        from app.models import user, alert, subscription  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
    app.dependency_overrides[get_db] = override_get_db
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as c:
        yield c


@pytest_asyncio.fixture
async def registered_user(client):
    """Create and return a registered user payload."""
    payload = {
        "email": "fixture@example.com",
        "password": "testpass123",
        "full_name": "Fixture User",
        "organization": "Test Org",
    }
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 201
    return payload


@pytest_asyncio.fixture
async def auth_headers(client, registered_user):
    """Return Authorization headers for the fixture user."""
    resp = await client.post(
        "/auth/token",
        data={
            "username": registered_user["email"],
            "password": registered_user["password"],
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def seeded_alert(client, auth_headers):
    """Insert a real alert row for tests that need existing data."""
    from sqlalchemy import insert
    from app.models.alert import Alert, SeverityLevel, AlertStatus
    import uuid
    async with TestSession() as session:
        alert = Alert(
            threat_id=str(uuid.uuid4()),
            severity=SeverityLevel.HIGH,
            status=AlertStatus.OPEN,
            classification="Brute Force SSH",
            source_ip="1.2.3.4",
            destination_ip="10.0.0.1",
            source_port=54321,
            destination_port=22,
            protocol="TCP",
            confidence_score=0.87,
            description="Test alert fixture",
        )
        session.add(alert)
        await session.commit()
        await session.refresh(alert)
        return alert
