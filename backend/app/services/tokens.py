"""Token registration: atomic daily sequence allocation + customer upsert."""
import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.counter import Counter, CounterStatus
from app.models.customer import Customer
from app.models.sms_notification import MessageType
from app.models.token import Token, TokenSequence, TokenStatus
from app.services.events import record_event
from app.services.notifications import create_notification_row
from app.services.prediction import predict_wait_seconds

settings = get_settings()


async def _allocate_token_number(db: AsyncSession, service_date: dt.date, prefix: str) -> str:
    """Atomic upsert-increment. Works under Postgres (ON CONFLICT) and
    SQLite (same syntax supported by SQLAlchemy's generic insert..on_conflict
    for sqlite dialect) used in tests."""
    stmt = (
        pg_insert(TokenSequence)
        .values(service_date=service_date, prefix=prefix, last_number=1)
        .on_conflict_do_update(
            index_elements=["service_date", "prefix"],
            set_={"last_number": TokenSequence.last_number + 1},
        )
        .returning(TokenSequence.last_number)
    )
    result = await db.execute(stmt)
    number = result.scalar_one()
    if number > 999:
        # Roll to next letter prefix, restart numbering. Rare in practice.
        next_prefix = chr(ord(prefix) + 1)
        return await _allocate_token_number(db, service_date, next_prefix)
    return f"{prefix}{number:03d}"


async def _get_or_create_customer(db: AsyncSession, phone_number: str) -> Customer:
    result = await db.execute(select(Customer).where(Customer.phone_number == phone_number))
    customer = result.scalar_one_or_none()
    if customer is None:
        customer = Customer(phone_number=phone_number)
        db.add(customer)
        await db.flush()
    return customer


async def _estimate_wait(db: AsyncSession, service_category: str) -> int | None:
    waiting_count = await db.scalar(
        select(func.count()).where(
            Token.status.in_([TokenStatus.waiting]), Token.service_category == service_category
        )
    )
    active_counters = await db.scalar(
        select(func.count()).where(Counter.counter_status != CounterStatus.closed)
    )
    recent = await db.execute(
        select(Token.service_start_time, Token.completion_time)
        .where(Token.completion_time.is_not(None), Token.service_start_time.is_not(None))
        .order_by(Token.completion_time.desc())
        .limit(20)
    )
    recent_service_times = [
        int((completed - started).total_seconds())
        for started, completed in recent.all()
        if completed and started and (completed - started).total_seconds() > 0
    ]
    return await predict_wait_seconds(
        service_category=service_category,
        queue_depth=waiting_count or 0,
        active_counters=active_counters or 1,
        recent_service_times=recent_service_times,
    )


async def register_token(db: AsyncSession, *, phone_number: str, service_category: str) -> Token:
    today = dt.date.today()
    customer = await _get_or_create_customer(db, phone_number)
    token_number = await _allocate_token_number(db, today, settings.token_prefix)

    estimated_wait = await _estimate_wait(db, service_category)

    token = Token(
        token_number=token_number,
        customer_id=customer.customer_id,
        service_category=service_category,
        status=TokenStatus.waiting,
        service_date=today,
        estimated_wait_time=estimated_wait,
    )
    db.add(token)
    await db.flush()

    await record_event(db, token_id=token.token_id, event_type="registered", payload={"to": "waiting"})

    notification = await create_notification_row(
        db,
        token_id=token.token_id,
        phone_number=phone_number,
        message_type=MessageType.registration,
        token_number=token_number,
        service_category=service_category,
    )

    await db.commit()

    # Enqueue only after commit, so the worker's separate session can see the row.
    from app.services.notifications import enqueue_after_commit

    await enqueue_after_commit(notification.notification_id)

    return token
