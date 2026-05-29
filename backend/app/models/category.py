from __future__ import annotations

import uuid

from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Category(Base):
    """User-defined 2-level grouping for targets/visualization.

    `parent_id IS NULL` = grupo (nível 1); preenchido = subgrupo (nível 2).
    Pesos são relativos aos irmãos (somam 100 por nível). Independente de
    `asset_type` (que segue cuidando de preço/diagrama/força).
    """

    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("portfolios.id", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("categories.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(64))
    weight_pct: Mapped[float] = mapped_column(Float)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
