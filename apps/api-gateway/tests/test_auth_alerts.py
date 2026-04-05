import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import Base, get_db

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
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
        from app.models import user, alert, subscription  # noqa
        await conn.run_sync(Base.metadata.create_all)
    app.dependency_overrides[get_db] = override_get_db
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def auth_headers(client):
    await client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "password123",
        "full_name": "Test User",
        "organization": "Test Org",
    })
    resp = await client.post(
        "/auth/token",
        data={"username": "test@example.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ─── Tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_register(client):
    r = await client.post("/auth/register", json={
        "email": "new@example.com",
        "password": "securepass",
        "full_name": "New User",
        "organization": "Org",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "new@example.com"
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": "pass", "full_name": "A", "organization": ""}
    await client.post("/auth/register", json=payload)
    r = await client.post("/auth/register", json=payload)
    assert r.status_code == 400
    assert "already registered" in r.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/auth/register", json={
        "email": "login@example.com", "password": "mypassword",
        "full_name": "Login User", "organization": "",
    })
    r = await client.post(
        "/auth/token",
        data={"username": "login@example.com", "password": "mypassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200
    assert "access_token" in r.json()
    assert "refresh_token" in r.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/auth/register", json={
        "email": "wrong@example.com", "password": "correct",
        "full_name": "X", "organization": "",
    })
    r = await client.post(
        "/auth/token",
        data={"username": "wrong@example.com", "password": "incorrect"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client, auth_headers):
    r = await client.get("/auth/me", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_get_me_unauthorized(client):
    r = await client.get("/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_alerts_empty(client, auth_headers):
    r = await client.get("/alerts", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_alerts_stats(client, auth_headers):
    r = await client.get("/alerts/stats", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "critical" in data


@pytest.mark.asyncio
async def test_alert_not_found(client, auth_headers):
    r = await client.get("/alerts/99999", headers=auth_headers)
    assert r.status_code == 404
