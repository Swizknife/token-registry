import datetime as dt
import enum

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, SmallInteger, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class TokenStatus(str, enum.Enum):
    waiting = "waiting"
    called = "called"
    serving = "serving"
    completed = "completed"
    skipped = "skipped"
    absent = "absent"


class Token(Base):
    __tablename__ = "tokens"
    __table_args__ = (UniqueConstraint("service_date", "token_number", name="uq_token_per_day"),)

    token_id: Mapped[int] = mapped_column(primary_key=True)
    token_number: Mapped[str] = mapped_column(String(16), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.customer_id"))
    service_category: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[TokenStatus] = mapped_column(
        Enum(TokenStatus, name="token_status"), default=TokenStatus.waiting, index=True
    )

    registration_time: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    called_time: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    service_start_time: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completion_time: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    counter_id: Mapped[int | None] = mapped_column(ForeignKey("counters.counter_id"), nullable=True)
    estimated_wait_time: Mapped[int | None] = mapped_column(Integer, nullable=True)

    service_date: Mapped[dt.date] = mapped_column(Date, index=True)
    recall_count: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[int] = mapped_column(SmallInteger, default=0)

    customer: Mapped["Customer"] = relationship(back_populates="tokens")  # noqa: F821


class TokenSequence(Base):
    """Backing store for atomic, gap-free daily token number allocation."""

    __tablename__ = "token_sequences"

    service_date: Mapped[dt.date] = mapped_column(Date, primary_key=True)
    prefix: Mapped[str] = mapped_column(String(4), primary_key=True)
    last_number: Mapped[int] = mapped_column(Integer, default=0)
