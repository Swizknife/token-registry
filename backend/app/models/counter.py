import enum

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class CounterStatus(str, enum.Enum):
    open = "open"
    busy = "busy"
    paused = "paused"
    closed = "closed"


class Counter(Base):
    __tablename__ = "counters"

    counter_id: Mapped[int] = mapped_column(primary_key=True)
    counter_name: Mapped[str] = mapped_column(String(64), unique=True)
    assigned_service: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_token_id: Mapped[int | None] = mapped_column(
        ForeignKey("tokens.token_id", use_alter=True, name="fk_counters_current_token_id"), nullable=True
    )
    counter_status: Mapped[CounterStatus] = mapped_column(
        Enum(CounterStatus, name="counter_status"), default=CounterStatus.open
    )
    staff_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)

    current_token: Mapped["Token | None"] = relationship(  # noqa: F821
        foreign_keys=[current_token_id], post_update=True
    )
