import pytest
from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models.sms_notification import DeliveryStatus, SmsNotification
from app.services.sms.base import ProviderResult
from app.services.sms.worker import _process_one
from app.services.tokens import register_token


class _AlwaysFailsProvider:
    name = "fake-failing"

    async def send(self, to, body):
        return ProviderResult(success=False, error="simulated provider outage")


class _AlwaysSucceedsProvider:
    name = "fake-ok"

    async def send(self, to, body):
        return ProviderResult(success=True, provider_message_id="abc123")


@pytest.mark.asyncio
async def test_registration_creates_pending_notification(db):
    token = await register_token(db, phone_number="+10000000001", service_category="Payment")
    notification = (
        await db.execute(select(SmsNotification).where(SmsNotification.token_id == token.token_id))
    ).scalar_one()
    assert notification.delivery_status == DeliveryStatus.pending
    assert notification.phone_number == "+10000000001"


@pytest.mark.asyncio
async def test_failed_provider_marks_notification_failed_without_raising(db):
    token = await register_token(db, phone_number="+10000000002", service_category="Payment")
    notification = (
        await db.execute(select(SmsNotification).where(SmsNotification.token_id == token.token_id))
    ).scalar_one()

    await _process_one(_AlwaysFailsProvider(), notification.notification_id)

    async with AsyncSessionLocal() as session:
        refreshed = (
            await session.execute(select(SmsNotification).where(SmsNotification.notification_id == notification.notification_id))
        ).scalar_one()
        assert refreshed.delivery_status == DeliveryStatus.failed
        assert refreshed.attempt_count >= 1
        assert refreshed.last_error == "simulated provider outage"


@pytest.mark.asyncio
async def test_successful_provider_marks_notification_sent(db):
    token = await register_token(db, phone_number="+10000000003", service_category="Payment")
    notification = (
        await db.execute(select(SmsNotification).where(SmsNotification.token_id == token.token_id))
    ).scalar_one()

    await _process_one(_AlwaysSucceedsProvider(), notification.notification_id)

    async with AsyncSessionLocal() as session:
        refreshed = (
            await session.execute(select(SmsNotification).where(SmsNotification.notification_id == notification.notification_id))
        ).scalar_one()
        assert refreshed.delivery_status == DeliveryStatus.sent
        assert refreshed.provider_message_id == "abc123"
        assert refreshed.sent_at is not None
