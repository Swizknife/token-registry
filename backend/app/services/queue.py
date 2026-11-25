"""Queue state transitions: Call Next, Recall, Serving, Complete, Skip, Absent, Requeue.

Call Next is the operation that must never double-assign a token when two
counters press the button at the same moment. It uses `FOR UPDATE SKIP
LOCKED` so a concurrent caller steps over a row another transaction is
already holding instead of blocking on it or racing it.
"""
import datetime as dt

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.counter import Counter, CounterStatus
from app.models.customer import Customer
from app.models.sms_notification import MessageType
from app.models.token import Token, TokenStatus
from app.services.events import record_event
from app.services.notifications import create_notification_row, enqueue_after_commit
from app.services.realtime import broadcaster


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


async def _lock_next_waiting_token(db: AsyncSession, service_category: str | None) -> Token | None:
    query = (
        select(Token)
        .where(Token.status == TokenStatus.waiting)
        .order_by(Token.priority.desc(), Token.registration_time)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if service_category is not None:
        query = query.where(Token.service_category == service_category)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def call_next(db: AsyncSession, *, counter_id: int, actor_user_id: int | None) -> Token:
    counter_result = await db.execute(select(Counter).where(Counter.counter_id == counter_id).with_for_update())
    counter = counter_result.scalar_one_or_none()
    if counter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Counter not found")

    token = None
    if counter.assigned_service is not None:
        token = await _lock_next_waiting_token(db, counter.assigned_service)
    if token is None:
        token = await _lock_next_waiting_token(db, None)
    if token is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No tokens waiting")

    token.status = TokenStatus.called
    token.called_time = _now()
    token.counter_id = counter.counter_id
    counter.current_token_id = token.token_id
    counter.counter_status = CounterStatus.busy

    await record_event(
        db,
        token_id=token.token_id,
        event_type="called",
        counter_id=counter.counter_id,
        actor_user_id=actor_user_id,
        payload={"to": "called"},
    )

    customer_result = await db.execute(select(Customer).where(Customer.customer_id == token.customer_id))
    customer = customer_result.scalar_one()
    notification = await create_notification_row(
        db,
        token_id=token.token_id,
        phone_number=customer.phone_number,
        message_type=MessageType.token_called,
        token_number=token.token_number,
        counter_name=counter.counter_name,
    )

    await db.commit()
    await enqueue_after_commit(notification.notification_id)
    await broadcaster.broadcast(
        "token.called",
        {"token_id": token.token_id, "token_number": token.token_number, "counter_name": counter.counter_name},
    )
    await broadcaster.broadcast("display.refresh", {})
    return token


async def _get_token_or_404(db: AsyncSession, token_id: int) -> Token:
    result = await db.execute(select(Token).where(Token.token_id == token_id).with_for_update())
    token = result.scalar_one_or_none()
    if token is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
    return token


async def recall(db: AsyncSession, *, token_id: int, actor_user_id: int | None) -> Token:
    token = await _get_token_or_404(db, token_id)
    if token.status not in (TokenStatus.called, TokenStatus.serving):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token is not currently called")
    token.recall_count += 1
    await record_event(
        db, token_id=token.token_id, event_type="recalled", counter_id=token.counter_id, actor_user_id=actor_user_id
    )
    await db.commit()
    await broadcaster.broadcast(
        "token.updated", {"token_id": token.token_id, "status": token.status.value}
    )
    await broadcaster.broadcast("display.refresh", {})
    return token


async def mark_serving(db: AsyncSession, *, token_id: int, actor_user_id: int | None) -> Token:
    token = await _get_token_or_404(db, token_id)
    if token.status != TokenStatus.called:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token must be in 'called' state")
    token.status = TokenStatus.serving
    token.service_start_time = _now()
    await record_event(
        db,
        token_id=token.token_id,
        event_type="serving",
        counter_id=token.counter_id,
        actor_user_id=actor_user_id,
        payload={"to": "serving"},
    )
    await db.commit()
    await broadcaster.broadcast("token.updated", {"token_id": token.token_id, "status": "serving"})
    await broadcaster.broadcast("display.refresh", {})
    return token


async def complete(db: AsyncSession, *, token_id: int, actor_user_id: int | None) -> Token:
    token = await _get_token_or_404(db, token_id)
    if token.status not in (TokenStatus.called, TokenStatus.serving):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token is not being served")
    token.status = TokenStatus.completed
    token.completion_time = _now()
    counter_id = token.counter_id

    if counter_id is not None:
        counter_result = await db.execute(select(Counter).where(Counter.counter_id == counter_id).with_for_update())
        counter = counter_result.scalar_one_or_none()
        if counter is not None and counter.current_token_id == token.token_id:
            counter.current_token_id = None
            counter.counter_status = CounterStatus.open

    await record_event(
        db,
        token_id=token.token_id,
        event_type="completed",
        counter_id=counter_id,
        actor_user_id=actor_user_id,
        payload={"to": "completed"},
    )
    await db.commit()
    await broadcaster.broadcast("token.updated", {"token_id": token.token_id, "status": "completed"})
    await broadcaster.broadcast("counter.updated", {"counter_id": counter_id})
    await broadcaster.broadcast("display.refresh", {})
    return token


async def skip(db: AsyncSession, *, token_id: int, actor_user_id: int | None) -> Token:
    token = await _get_token_or_404(db, token_id)
    if token.status not in (TokenStatus.waiting, TokenStatus.called):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token cannot be skipped")
    counter_id = token.counter_id
    token.status = TokenStatus.skipped

    if counter_id is not None:
        counter_result = await db.execute(select(Counter).where(Counter.counter_id == counter_id).with_for_update())
        counter = counter_result.scalar_one_or_none()
        if counter is not None and counter.current_token_id == token.token_id:
            counter.current_token_id = None
            counter.counter_status = CounterStatus.open

    await record_event(
        db, token_id=token.token_id, event_type="skipped", counter_id=counter_id, actor_user_id=actor_user_id
    )
    await db.commit()
    await broadcaster.broadcast("token.updated", {"token_id": token.token_id, "status": "skipped"})
    await broadcaster.broadcast("display.refresh", {})
    return token


async def mark_absent(db: AsyncSession, *, token_id: int, actor_user_id: int | None) -> Token:
    token = await _get_token_or_404(db, token_id)
    if token.status not in (TokenStatus.called, TokenStatus.serving):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token is not currently called")
    counter_id = token.counter_id
    token.status = TokenStatus.absent

    if counter_id is not None:
        counter_result = await db.execute(select(Counter).where(Counter.counter_id == counter_id).with_for_update())
        counter = counter_result.scalar_one_or_none()
        if counter is not None and counter.current_token_id == token.token_id:
            counter.current_token_id = None
            counter.counter_status = CounterStatus.open

    await record_event(
        db, token_id=token.token_id, event_type="absent", counter_id=counter_id, actor_user_id=actor_user_id
    )
    await db.commit()
    await broadcaster.broadcast("token.updated", {"token_id": token.token_id, "status": "absent"})
    await broadcaster.broadcast("display.refresh", {})
    return token


async def requeue(db: AsyncSession, *, token_id: int, actor_user_id: int | None) -> Token:
    token = await _get_token_or_404(db, token_id)
    if token.status not in (TokenStatus.skipped, TokenStatus.absent):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token cannot be re-queued")
    token.status = TokenStatus.waiting
    token.counter_id = None
    token.called_time = None
    token.service_start_time = None

    await record_event(db, token_id=token.token_id, event_type="requeued", actor_user_id=actor_user_id)
    await db.commit()
    await broadcaster.broadcast("token.updated", {"token_id": token.token_id, "status": "waiting"})
    await broadcaster.broadcast("display.refresh", {})
    return token
