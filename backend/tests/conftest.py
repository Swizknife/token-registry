"""Test fixtures.

Tests run against the real Postgres container (SKIP LOCKED is Postgres-only,
so SQLite cannot stand in for the concurrency test). Each test function gets
a clean schema via a transaction-wrapped drop/create of all tables.
"""
import asyncio
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://queue:queue@localhost:5432/queue_test")
os.environ.setdefault("SMS_PROVIDER", "console")
os.environ.setdefault("JWT_SECRET", "test-secret-at-least-32-bytes-long-xx")

from app.config import get_settings  # noqa: E402
from app.db import AsyncSessionLocal, Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.counter import Counter  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from app.security import hash_password  # noqa: E402

get_settings.cache_clear()


@pytest_asyncio.fixture(autouse=True)
async def _clean_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def seeded_counters(db: AsyncSession) -> list[Counter]:
    counters = [
        Counter(counter_name="Counter 01", assigned_service=None),
        Counter(counter_name="Counter 02", assigned_service="Payment"),
    ]
    db.add_all(counters)
    await db.commit()
    for c in counters:
        await db.refresh(c)
    return counters


@pytest_asyncio.fixture
async def staff_token(db: AsyncSession, client: AsyncClient) -> str:
    db.add(User(username="teststaff", password_hash=hash_password("pass1234"), role=UserRole.staff))
    await db.commit()
    resp = await client.post("/api/auth/login", json={"username": "teststaff", "password": "pass1234"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def admin_token(db: AsyncSession, client: AsyncClient) -> str:
    db.add(User(username="testadmin", password_hash=hash_password("pass1234"), role=UserRole.admin))
    await db.commit()
    resp = await client.post("/api/auth/login", json={"username": "testadmin", "password": "pass1234"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]
