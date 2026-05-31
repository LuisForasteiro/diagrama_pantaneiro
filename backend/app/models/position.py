from __future__ import annotations

import uuid
from datetime import datetime

from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("portfolios.id", ondelete="CASCADE"), index=True
    )

    name: Mapped[str] = mapped_column(String(128))
    asset_type: Mapped[str] = mapped_column(String(48), index=True)
    # Semantic override: when set, algorithm/metas/donut treat the position as
    # this class. asset_type stays for price-routing (market_data/registry.py).
    effective_class: Mapped[str | None] = mapped_column(String(48), nullable=True)
    amount: Mapped[float] = mapped_column(Float)
    current_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    strength: Mapped[int] = mapped_column(Integer)
    diagram_responses: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="auvp_import")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
