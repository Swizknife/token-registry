"""Background SMS dispatch worker.

Registration and Call Next write a `pending` sms_notifications row and return
immediately; this worker drains an in-process asyncio.Queue and performs the
actual send with retry, so a slow/unreachable provider never blocks a kiosk
or counter action.
"""
import asyncio
import logging

from sqlalchemy import select

from app.config import get_settings
from app.db import AsyncSessionLocal
from app.models.sms_notification import DeliveryStatus, SmsNotification
from app.services.sms.base import SmsProvider
from app.services.sms.console import ConsoleSmsProvider
from app.services.sms.twilio import TwilioSmsProvider

logger = logging.getLogger("sms.worker")

_queue: asyncio.Queue[int] = asyncio.Queue()
_worker_task: asyncio.Task | None = None


def get_provider() -> SmsProvider:
    settings = get_settings()
    if settings.sms_provider == "twilio":
        return TwilioSmsProvider()
    return ConsoleSmsProvider()


async def enqueue_notification(notification_id: int) -> None:
    await _queue.put(notification_id)


async def _process_one(provider: SmsProvider, notification_id: int) -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SmsNotification).where(SmsNotification.notification_id == notification_id)
        )
        notification = result.scalar_one_or_none()
        if notification is None:
            return

        backoff = 0.5
        while notification.attempt_count < settings.sms_max_attempts:
            notification.attempt_count += 1
            send_result = await provider.send(notification.phone_number, notification.message_content)
            if send_result.success:
                notification.delivery_status = DeliveryStatus.sent
                notification.provider = provider.name
                notification.provider_message_id = send_result.provider_message_id
                notification.sent_at = _now()
                await db.commit()
                return
            notification.last_error = send_result.error
            if notification.attempt_count >= settings.sms_max_attempts:
                break
            await asyncio.sleep(backoff)
            backoff *= 2

        notification.delivery_status = DeliveryStatus.failed
        notification.provider = provider.name
        await db.commit()


def _now():
    import datetime as dt

    return dt.datetime.now(dt.timezone.utc)


async def run_worker() -> None:
    provider = get_provider()
    logger.info("SMS worker started with provider=%s", provider.name)
    while True:
        notification_id = await _queue.get()
        try:
            await _process_one(provider, notification_id)
        except Exception:  # noqa: BLE001
            logger.exception("Unhandled error processing SMS notification %s", notification_id)


def start_worker() -> None:
    global _worker_task
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.create_task(run_worker())


def stop_worker() -> None:
    global _worker_task
    if _worker_task is not None:
        _worker_task.cancel()
        _worker_task = None
