"""The test that validates FOR UPDATE SKIP LOCKED actually prevents two
counters from being assigned the same waiting token. Runs against the real
Postgres container -- this is exactly the behavior that would be
unobservable against SQLite.
"""
import asyncio

import pytest
from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models.counter import Counter
from app.models.customer import Customer
from app.models.token import Token, TokenStatus
from app.services.queue import call_next


async def _seed_tokens(n: int, service="General Enquiry") -> list[int]:
    async with AsyncSessionLocal() as db:
        customer = Customer(phone_number="+10000000000")
        db.add(customer)
        await db.flush()
        token_ids = []
        for i in range(n):
            t = Token(
                token_number=f"A{i:03d}",
                customer_id=customer.customer_id,
                service_category=service,
                status=TokenStatus.waiting,
                service_date=__import__("datetime").date.today(),
            )
            db.add(t)
            await db.flush()
            token_ids.append(t.token_id)
        await db.commit()
        return token_ids


async def _seed_counters(n: int) -> list[int]:
    async with AsyncSessionLocal() as db:
        counters = [Counter(counter_name=f"C{i}") for i in range(n)]
        db.add_all(counters)
        await db.commit()
        return [c.counter_id for c in counters]


@pytest.mark.asyncio
async def test_two_counters_never_get_the_same_single_token(db):
    await _seed_tokens(1)
    counter_ids = await _seed_counters(2)

    async def attempt(counter_id: int):
        async with AsyncSessionLocal() as session:
            try:
                token = await call_next(session, counter_id=counter_id, actor_user_id=None)
                return token.token_id
            except Exception:
                return None

    results = await asyncio.gather(*(attempt(cid) for cid in counter_ids))
    successes = [r for r in results if r is not None]
    assert len(successes) == 1, f"expected exactly one counter to win the token, got {results}"


@pytest.mark.asyncio
async def test_n_tokens_m_counters_no_duplicate_assignment(db):
    token_ids = await _seed_tokens(12)
    counter_ids = await _seed_counters(5)

    async def attempt(counter_id: int):
        async with AsyncSessionLocal() as session:
            try:
                token = await call_next(session, counter_id=counter_id, actor_user_id=None)
                return token.token_id
            except Exception:
                return None

    # Fire more call-next attempts than tokens, across all counters, concurrently.
    attempts = []
    for _ in range(3):
        attempts.extend(attempt(cid) for cid in counter_ids)

    results = await asyncio.gather(*attempts)
    successes = [r for r in results if r is not None]

    assert len(successes) == len(set(successes)), "a token was assigned to more than one counter"
    assert len(successes) <= len(token_ids)

    # Each counter in this test is hit by 3 concurrent attempts, so a counter may
    # legitimately end up having called multiple tokens one after another (each
    # overwriting its current_token_id) -- that's sequential reuse, not a
    # duplicate assignment. The invariant that matters is already checked above:
    # no single token was ever handed to more than one counter.
    async with AsyncSessionLocal() as session:
        called = (
            await session.execute(select(Token).where(Token.status == TokenStatus.called))
        ).scalars().all()
        assert len(called) == len(successes)
