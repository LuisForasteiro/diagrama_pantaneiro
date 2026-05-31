from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class TickerCatalog(Base):
    """Reference cache of searchable tickers, refreshed weekly by the
    scheduler. Global (not per-user). `source` ∈ {b3, crypto}. `external_id`
    holds the CoinGecko coin id for crypto (None for b3)."""

    __tablename__ = "ticker_catalog"
    __table_args__ = (
        UniqueConstraint("source", "symbol", name="uq_ticker_source_symbol"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(String(48), index=True)
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source: Mapped[str] = mapped_column(String(16), index=True)
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
