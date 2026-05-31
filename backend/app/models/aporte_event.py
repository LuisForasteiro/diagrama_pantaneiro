from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy import DateTime, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.aporte_allocation import AporteAllocation


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AporteEvent(Base):
    __tablename__ = "aporte_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("portfolios.id", ondelete="CASCADE"), index=True
    )
    aporte_value_brl: Mapped[float] = mapped_column(Float)
    # Python-side default for microsecond precision; SQLite's CURRENT_TIMESTAMP
    # is second-resolution, which makes ORDER BY non-deterministic for rapid inserts.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now()
    )

    allocations: Mapped[list["AporteAllocation"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
