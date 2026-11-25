"""Phase 3 analytics + the Phase 4 TimesFM training export."""
import datetime as dt

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.counter import Counter
from app.models.token import Token, TokenStatus
from app.models.user import User
from app.schemas.analytics import CounterEfficiencyRow, SummaryResponse, TimeseriesBucket
from app.security import require_admin

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary", response_model=SummaryResponse)
async def summary(
    date_from: dt.date = Query(default=None, alias="from"),
    date_to: dt.date = Query(default=None, alias="to"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> SummaryResponse:
    date_from = date_from or dt.date.today()
    date_to = date_to or dt.date.today()

    base = select(Token).where(Token.service_date.between(date_from, date_to))
    total = await db.scalar(select(func.count()).select_from(base.subquery()))

    completed_query = base.where(Token.status == TokenStatus.completed)
    completed = await db.scalar(select(func.count()).select_from(completed_query.subquery()))

    wait_seconds = await db.scalar(
        select(func.avg(func.extract("epoch", Token.called_time - Token.registration_time))).where(
            Token.service_date.between(date_from, date_to), Token.called_time.is_not(None)
        )
    )
    service_seconds = await db.scalar(
        select(func.avg(func.extract("epoch", Token.completion_time - Token.service_start_time))).where(
            Token.service_date.between(date_from, date_to),
            Token.completion_time.is_not(None),
            Token.service_start_time.is_not(None),
        )
    )

    span_hours = max((date_to - date_from).days * 24 + 24, 1)
    throughput = (completed or 0) / span_hours if completed else None

    return SummaryResponse(
        total_tokens=total or 0,
        completed=completed or 0,
        avg_wait_seconds=float(wait_seconds) if wait_seconds is not None else None,
        avg_service_seconds=float(service_seconds) if service_seconds is not None else None,
        throughput_per_hour=throughput,
    )


@router.get("/counters", response_model=list[CounterEfficiencyRow])
async def counter_efficiency(
    db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)
) -> list[CounterEfficiencyRow]:
    today = dt.date.today()
    counters_result = await db.execute(select(Counter))
    counters = counters_result.scalars().all()

    rows = []
    for c in counters:
        completed = await db.scalar(
            select(func.count()).where(
                Token.counter_id == c.counter_id,
                Token.status == TokenStatus.completed,
                Token.service_date == today,
            )
        )
        avg_service = await db.scalar(
            select(func.avg(func.extract("epoch", Token.completion_time - Token.service_start_time))).where(
                Token.counter_id == c.counter_id,
                Token.status == TokenStatus.completed,
                Token.service_date == today,
                Token.service_start_time.is_not(None),
            )
        )
        rows.append(
            CounterEfficiencyRow(
                counter_id=c.counter_id,
                counter_name=c.counter_name,
                completed=completed or 0,
                avg_service_seconds=float(avg_service) if avg_service is not None else None,
            )
        )
    return rows


@router.get("/timeseries", response_model=list[TimeseriesBucket])
async def timeseries(
    granularity_minutes: int = Query(15, ge=5, le=120),
    date_from: dt.date = Query(default=None, alias="from"),
    date_to: dt.date = Query(default=None, alias="to"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[TimeseriesBucket]:
    """Arrivals/completions/service-duration per bucket per service category --
    the historical dataset a future TimesFM inference service trains/predicts from."""
    date_from = date_from or dt.date.today()
    date_to = date_to or dt.date.today()

    bucket_expr = func.to_timestamp(
        func.floor(func.extract("epoch", Token.registration_time) / (granularity_minutes * 60))
        * (granularity_minutes * 60)
    )

    arrivals_result = await db.execute(
        select(bucket_expr.label("bucket"), Token.service_category, func.count().label("arrivals"))
        .where(Token.service_date.between(date_from, date_to))
        .group_by("bucket", Token.service_category)
    )
    arrivals_map = {(row.bucket, row.service_category): row.arrivals for row in arrivals_result.all()}

    completion_bucket_expr = func.to_timestamp(
        func.floor(func.extract("epoch", Token.completion_time) / (granularity_minutes * 60))
        * (granularity_minutes * 60)
    )
    completions_result = await db.execute(
        select(
            completion_bucket_expr.label("bucket"),
            Token.service_category,
            func.count().label("completions"),
            func.avg(func.extract("epoch", Token.completion_time - Token.service_start_time)).label("avg_service"),
        )
        .where(
            Token.service_date.between(date_from, date_to),
            Token.completion_time.is_not(None),
        )
        .group_by("bucket", Token.service_category)
    )
    completions_map = {
        (row.bucket, row.service_category): (row.completions, row.avg_service) for row in completions_result.all()
    }

    buckets = set(arrivals_map.keys()) | set(completions_map.keys())
    results = []
    for bucket, category in sorted(buckets, key=lambda b: (b[0], b[1])):
        completions, avg_service = completions_map.get((bucket, category), (0, None))
        results.append(
            TimeseriesBucket(
                bucket_start=bucket,
                service_category=category,
                arrivals=arrivals_map.get((bucket, category), 0),
                completions=completions,
                avg_service_seconds=float(avg_service) if avg_service is not None else None,
            )
        )
    return results
