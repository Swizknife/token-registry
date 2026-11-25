import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.counter import Counter, CounterStatus
from app.models.customer import Customer
from app.models.token import Token, TokenStatus
from app.models.user import User, UserRole
from app.schemas.staff import OverviewResponse
from app.schemas.token import TokenDetail, TokenStaffRow
from app.security import require_admin, require_staff
from app.services import queue as queue_service

router = APIRouter(prefix="/api/staff", tags=["staff"])


def _mask_phone(phone: str) -> str:
    if len(phone) <= 4:
        return "*" * len(phone)
    return "*" * (len(phone) - 4) + phone[-4:]


@router.get("/overview", response_model=OverviewResponse)
async def overview(db: AsyncSession = Depends(get_db), _: User = Depends(require_staff)) -> OverviewResponse:
    today = dt.date.today()
    base = select(func.count()).where(Token.service_date == today)

    total = await db.scalar(base)
    waiting = await db.scalar(base.where(Token.status == TokenStatus.waiting))
    serving = await db.scalar(
        base.where(Token.status.in_([TokenStatus.called, TokenStatus.serving]))
    )
    completed = await db.scalar(base.where(Token.status == TokenStatus.completed))

    counters_result = await db.execute(select(Counter))
    counters = counters_result.scalars().all()
    active_counters = sum(1 for c in counters if c.counter_status != CounterStatus.closed)

    counters_now_serving: dict[str, str | None] = {}
    for c in counters:
        token_number = None
        if c.current_token_id is not None:
            tok = await db.scalar(select(Token.token_number).where(Token.token_id == c.current_token_id))
            token_number = tok
        counters_now_serving[c.counter_name] = token_number

    return OverviewResponse(
        total_registered_today=total or 0,
        currently_waiting=waiting or 0,
        being_served=serving or 0,
        completed_today=completed or 0,
        active_counters=active_counters,
        counters_now_serving=counters_now_serving,
    )


@router.get("/tokens", response_model=list[TokenStaffRow])
async def list_tokens(
    status_filter: str | None = Query(None, alias="status"),
    service: str | None = Query(None),
    q: str | None = Query(None, description="search by token number"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
) -> list[TokenStaffRow]:
    today = dt.date.today()
    query = select(Token, Customer.phone_number).join(Customer, Token.customer_id == Customer.customer_id)
    query = query.where(Token.service_date == today)
    if status_filter:
        query = query.where(Token.status == status_filter)
    if service:
        query = query.where(Token.service_category == service)
    if q:
        query = query.where(Token.token_number.ilike(f"%{q}%"))
    query = query.order_by(Token.registration_time.desc()).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    return [
        TokenStaffRow(
            token_id=token.token_id,
            token_number=token.token_number,
            phone_masked=_mask_phone(phone),
            service_category=token.service_category,
            status=token.status.value,
            registration_time=token.registration_time,
            called_time=token.called_time,
            counter_id=token.counter_id,
            estimated_wait_time=token.estimated_wait_time,
        )
        for token, phone in result.all()
    ]


async def _build_token_detail(db: AsyncSession, token_id: int) -> TokenDetail:
    query = select(Token, Customer.phone_number).join(Customer, Token.customer_id == Customer.customer_id)
    query = query.where(Token.token_id == token_id)
    result = await db.execute(query)
    row = result.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
    token, phone = row
    return TokenDetail(
        token_id=token.token_id,
        token_number=token.token_number,
        phone_number=phone,
        service_category=token.service_category,
        status=token.status.value,
        registration_time=token.registration_time,
        called_time=token.called_time,
        service_start_time=token.service_start_time,
        completion_time=token.completion_time,
        counter_id=token.counter_id,
        recall_count=token.recall_count,
        estimated_wait_time=token.estimated_wait_time,
    )


async def _build_masked_row(db: AsyncSession, token_id: int) -> TokenStaffRow:
    query = select(Token, Customer.phone_number).join(Customer, Token.customer_id == Customer.customer_id)
    query = query.where(Token.token_id == token_id)
    result = await db.execute(query)
    row = result.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
    token, phone = row
    return TokenStaffRow(
        token_id=token.token_id,
        token_number=token.token_number,
        phone_masked=_mask_phone(phone),
        service_category=token.service_category,
        status=token.status.value,
        registration_time=token.registration_time,
        called_time=token.called_time,
        counter_id=token.counter_id,
        estimated_wait_time=token.estimated_wait_time,
    )


@router.get("/tokens/{token_id}", response_model=TokenDetail)
async def get_token_detail(
    token_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)
) -> TokenDetail:
    """Full detail including the unmasked phone number -- admin only."""
    return await _build_token_detail(db, token_id)


@router.post("/tokens/{token_id}/absent", response_model=TokenStaffRow)
async def mark_absent(
    token_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(require_staff)
) -> TokenStaffRow:
    await queue_service.mark_absent(db, token_id=token_id, actor_user_id=user.user_id)
    return await _build_masked_row(db, token_id)


@router.post("/tokens/{token_id}/requeue", response_model=TokenStaffRow)
async def requeue(
    token_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(require_staff)
) -> TokenStaffRow:
    await queue_service.requeue(db, token_id=token_id, actor_user_id=user.user_id)
    return await _build_masked_row(db, token_id)
