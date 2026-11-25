import datetime as dt

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class QueueEvent(Base):
    """Append-only audit / analytics log. Never updated or deleted."""

    __tablename__ = "queue_events"

    event_id: Mapped[int] = mapped_column(primary_key=True)
    token_id: Mapped[int] = mapped_column(ForeignKey("tokens.token_id"), index=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    counter_id: Mapped[int | None] = mapped_column(ForeignKey("counters.counter_id"), nullable=True)
    event_timestamp: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
