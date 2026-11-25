"""Seeds service categories (implicit, see schemas/token.py), counters and an
admin user. Idempotent -- safe to run multiple times."""
import asyncio

from sqlalchemy import select

from app.config import get_settings
from app.db import AsyncSessionLocal
from app.models.counter import Counter
from app.models.user import User, UserRole
from app.security import hash_password

settings = get_settings()

COUNTERS = [
    {"counter_name": "Counter 01", "assigned_service": None},
    {"counter_name": "Counter 02", "assigned_service": "Payment"},
    {"counter_name": "Counter 03", "assigned_service": "Document Verification"},
]


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == settings.seed_admin_username))
        if result.scalar_one_or_none() is None:
            db.add(
                User(
                    username=settings.seed_admin_username,
                    password_hash=hash_password(settings.seed_admin_password),
                    role=UserRole.admin,
                )
            )
            print(f"Seeded admin user '{settings.seed_admin_username}'")

        result = await db.execute(select(User).where(User.username == "staff1"))
        if result.scalar_one_or_none() is None:
            db.add(User(username="staff1", password_hash=hash_password("staff123"), role=UserRole.staff))
            print("Seeded staff user 'staff1'")

        existing = await db.execute(select(Counter.counter_name))
        existing_names = set(existing.scalars().all())
        for c in COUNTERS:
            if c["counter_name"] not in existing_names:
                db.add(Counter(**c))
                print(f"Seeded {c['counter_name']}")

        await db.commit()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
