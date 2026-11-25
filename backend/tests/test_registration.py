import datetime as dt

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.queue_event import QueueEvent
from app.models.sms_notification import SmsNotification
from app.models.token import Token, TokenSequence


@pytest.mark.asyncio
async def test_register_token_persists_everything(client: AsyncClient, db: AsyncSession):
    resp = await client.post(
        "/api/kiosk/tokens", json={"phone_number": "9876543210", "service_category": "Payment"}
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["token_number"] == "A001"
    assert body["status"] == "waiting"

    customers = (await db.execute(select(Customer))).scalars().all()
    assert len(customers) == 1

    tokens = (await db.execute(select(Token))).scalars().all()
    assert len(tokens) == 1
    assert tokens[0].service_category == "Payment"

    events = (await db.execute(select(QueueEvent).where(QueueEvent.event_type == "registered"))).scalars().all()
    assert len(events) == 1

    notifications = (await db.execute(select(SmsNotification))).scalars().all()
    assert len(notifications) == 1
    assert notifications[0].message_type.value == "registration"


@pytest.mark.asyncio
async def test_invalid_phone_number_rejected(client: AsyncClient):
    resp = await client.post("/api/kiosk/tokens", json={"phone_number": "123", "service_category": "Payment"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_service_category_rejected(client: AsyncClient):
    resp = await client.post(
        "/api/kiosk/tokens", json={"phone_number": "9876543210", "service_category": "Not A Real Service"}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_token_numbers_sequential_and_unique(client: AsyncClient):
    numbers = []
    for _ in range(5):
        resp = await client.post(
            "/api/kiosk/tokens", json={"phone_number": "9876543210", "service_category": "Payment"}
        )
        numbers.append(resp.json()["token_number"])
    assert numbers == ["A001", "A002", "A003", "A004", "A005"]
    assert len(set(numbers)) == len(numbers)


@pytest.mark.asyncio
async def test_token_numbering_restarts_each_day(monkeypatch, client: AsyncClient):
    import app.services.tokens as tokens_module

    yesterday = dt.date.today() - dt.timedelta(days=1)

    class _FixedDate(dt.date):
        @classmethod
        def today(cls):
            return yesterday

    monkeypatch.setattr(tokens_module.dt, "date", _FixedDate)
    resp = await client.post("/api/kiosk/tokens", json={"phone_number": "9876543210", "service_category": "Payment"})
    assert resp.json()["token_number"] == "A001"
    monkeypatch.undo()

    # Back to the real "today" -- a fresh day's sequence, so numbering restarts.
    resp = await client.post("/api/kiosk/tokens", json={"phone_number": "9876543210", "service_category": "Payment"})
    assert resp.json()["token_number"] == "A001"


@pytest.mark.asyncio
async def test_repeat_customer_reuses_record(client: AsyncClient, db: AsyncSession):
    await client.post("/api/kiosk/tokens", json={"phone_number": "9876543210", "service_category": "Payment"})
    await client.post(
        "/api/kiosk/tokens", json={"phone_number": "9876543210", "service_category": "General Enquiry"}
    )
    customers = (await db.execute(select(Customer))).scalars().all()
    assert len(customers) == 1
    tokens = (await db.execute(select(Token))).scalars().all()
    assert len(tokens) == 2


@pytest.mark.asyncio
async def test_prediction_service_unreachable_still_returns_201(client: AsyncClient, monkeypatch):
    from app.services import tokens as tokens_module

    async def _boom(**kwargs):
        return None

    monkeypatch.setattr(tokens_module, "predict_wait_seconds", _boom)

    resp = await client.post("/api/kiosk/tokens", json={"phone_number": "9876543210", "service_category": "Payment"})
    assert resp.status_code == 201
    assert resp.json()["estimated_wait_time"] is None
