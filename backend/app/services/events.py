"""Append-only queue_events writer. Never call UPDATE/DELETE on this table."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.queue_event import QueueEvent


async def record_event(
    db: AsyncSession,
    *,
    token_id: int,
    event_type: str,
    counter_id: int | None = None,
    actor_user_id: int | None = None,
    payload: dict | None = None,
) -> QueueEvent:
    event = QueueEvent(
        token_id=token_id,
        event_type=event_type,
        counter_id=counter_id,
        actor_user_id=actor_user_id,
        payload=payload,
    )
    db.add(event)
    await db.flush()
    return event
