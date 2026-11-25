"""Builds sms_notifications rows and hands them to the background worker.

Call sites only need to commit their own transaction; the row is written in
the same session/transaction so it either persists with the queue change or
not at all, but actual sending happens out-of-band afterwards.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.sms_notification import MessageType, SmsNotification
from app.services.sms.worker import enqueue_notification

settings = get_settings()


def _build_message(message_type: MessageType, *, token_number: str, service_category: str | None = None,
                    counter_name: str | None = None) -> str:
    if message_type == MessageType.registration:
        return (
            f"Your token is {token_number}. You have successfully registered for "
            f"{service_category}. Please wait for your turn. "
            f"Track the live queue at {settings.public_queue_url}."
        )
    if message_type == MessageType.token_called:
        return f"Your token {token_number} has been called. Please proceed to {counter_name}."
    if message_type == MessageType.estimated_turn:
        return "Your estimated turn is coming up soon. Please remain nearby."
    raise ValueError(f"Unknown message type: {message_type}")


async def create_notification_row(
    db: AsyncSession,
    *,
    token_id: int,
    phone_number: str,
    message_type: MessageType,
    token_number: str,
    service_category: str | None = None,
    counter_name: str | None = None,
) -> SmsNotification:
    """Writes the pending row within the caller's transaction.

    Does NOT enqueue for sending yet -- the worker runs in a separate
    session, so enqueueing must happen only after the caller commits, or the
    worker may try to read a row that isn't visible yet. Call
    `enqueue_after_commit` once the transaction has committed.
    """
    body = _build_message(
        message_type, token_number=token_number, service_category=service_category, counter_name=counter_name
    )
    notification = SmsNotification(
        token_id=token_id,
        phone_number=phone_number,
        message_type=message_type,
        message_content=body,
    )
    db.add(notification)
    await db.flush()
    return notification


async def enqueue_after_commit(notification_id: int) -> None:
    await enqueue_notification(notification_id)
