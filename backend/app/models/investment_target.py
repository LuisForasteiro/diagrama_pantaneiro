from __future__ import annotations

import uuid

from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy import Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class InvestmentTarget(Base):
    __tablename__ = "investment_targets"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "asset_type", name="uq_target_portfolio_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("portfolios.id", ondelete="CASCADE"), index=True
    )
    asset_type: Mapped[str] = mapped_column(String(48))
    target_percentage: Mapped[float] = mapped_column(Float)
