from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.counter import Counter
from app.models.token import Token
from app.models.user import User
from app.schemas.counter import CallNextResponse, CounterCreateRequest, CounterResponse
from app.security import require_admin, require_staff
from app.services import queue as queue_service
from app.services.queue import call_next as call_next_service

router = APIRouter(prefix="/api/counters", tags=["counters"])


async def _to_response(db: AsyncSession, counter: Counter) -> CounterResponse:
    token_number = None
    if counter.current_token_id is not None:
        token_number = await db.scalar(select(Token.token_number).where(Token.token_id == counter.current_token_id))
    return CounterResponse(
        counter_id=counter.counter_id,
        counter_name=counter.counter_name,
        assigned_service=counter.assigned_service,
        current_token_id=counter.current_token_id,
        current_token_number=token_number,
        counter_status=counter.counter_status.value,
    )


@router.get("", response_model=list[CounterResponse])
async def list_counters(db: AsyncSession = Depends(get_db), _: User = Depends(require_staff)) -> list[CounterResponse]:
    result = await db.execute(select(Counter).order_by(Counter.counter_id))
    return [await _to_response(db, c) for c in result.scalars().all()]


@router.post("", response_model=CounterResponse)
async def create_counter(
    payload: CounterCreateRequest, db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)
) -> CounterResponse:
    counter = Counter(counter_name=payload.counter_name, assigned_service=payload.assigned_service)
    db.add(counter)
    await db.commit()
    await db.refresh(counter)
    return await _to_response(db, counter)


@router.post("/{counter_id}/call-next", response_model=CallNextResponse)
async def call_next(
    counter_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(require_staff)
) -> CallNextResponse:
    token = await call_next_service(db, counter_id=counter_id, actor_user_id=user.user_id)
    counter = await db.get(Counter, counter_id)
    return CallNextResponse(
        token_id=token.token_id,
        token_number=token.token_number,
        service_category=token.service_category,
        counter_id=counter_id,
        counter_name=counter.counter_name,
    )


@router.post("/{counter_id}/recall/{token_id}")
async def recall(
    counter_id: int, token_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(require_staff)
):
    token = await queue_service.recall(db, token_id=token_id, actor_user_id=user.user_id)
    return {"token_id": token.token_id, "status": token.status.value}


@router.post("/{counter_id}/serving/{token_id}")
async def mark_serving(
    counter_id: int, token_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(require_staff)
):
    token = await queue_service.mark_serving(db, token_id=token_id, actor_user_id=user.user_id)
    return {"token_id": token.token_id, "status": token.status.value}


@router.post("/{counter_id}/complete/{token_id}")
async def complete(
    counter_id: int, token_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(require_staff)
):
    token = await queue_service.complete(db, token_id=token_id, actor_user_id=user.user_id)
    return {"token_id": token.token_id, "status": token.status.value}


@router.post("/{counter_id}/skip/{token_id}")
async def skip(
    counter_id: int, token_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(require_staff)
):
    token = await queue_service.skip(db, token_id=token_id, actor_user_id=user.user_id)
    return {"token_id": token.token_id, "status": token.status.value}
