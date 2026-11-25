"""Public queue display endpoint. Must never expose phone numbers or customer_id."""
import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.counter import Counter
from app.models.token import Token, TokenStatus
from app.schemas.public import NowServingRow, PublicDisplayResponse

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/display", response_model=PublicDisplayResponse)
async def public_display(db: AsyncSession = Depends(get_db)) -> PublicDisplayResponse:
    counters_result = await db.execute(select(Counter).order_by(Counter.counter_id))
    counters = counters_result.scalars().all()

    now_serving: list[NowServingRow] = []
    for c in counters:
        token_number = None
        if c.current_token_id is not None:
            token_number = await db.scalar(select(Token.token_number).where(Token.token_id == c.current_token_id))
        now_serving.append(NowServingRow(counter_id=c.counter_id, counter_name=c.counter_name, token_number=token_number))

    today = dt.date.today()
    upcoming_result = await db.execute(
        select(Token.token_number)
        .where(Token.service_date == today, Token.status == TokenStatus.waiting)
        .order_by(Token.priority.desc(), Token.registration_time)
        .limit(8)
    )
    upcoming = list(upcoming_result.scalars().all())

    completed_result = await db.execute(
        select(Token.token_number)
        .where(Token.service_date == today, Token.status == TokenStatus.completed)
        .order_by(Token.completion_time.desc())
        .limit(6)
    )
    recently_completed = list(completed_result.scalars().all())

    return PublicDisplayResponse(now_serving=now_serving, upcoming=upcoming, recently_completed=recently_completed)
