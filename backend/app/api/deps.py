"""Shared FastAPI dependencies for portfolio-scoped routes.

`get_active_portfolio` is the single authorization choke point for any
endpoint that works on portfolio-scoped data (positions, targets, aportes,
prices). It reads the X-Portfolio-Id header (set by the frontend API
client from the active-portfolio store) and validates user ownership.

When the header is absent it falls back to the user's default portfolio —
this lets Phase 1 ship backend-only with zero frontend changes.
"""

from __future__ import annotations

import uuid

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_active_user
from app.core.db import get_async_session
from app.models.portfolio import Portfolio
from app.models.user import User


async def get_active_portfolio(
    x_portfolio_id: str | None = Header(default=None, alias="X-Portfolio-Id"),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> Portfolio:
    if x_portfolio_id:
        try:
            pid = uuid.UUID(x_portfolio_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid X-Portfolio-Id",
            )
        portfolio = (
            await session.execute(
                select(Portfolio).where(
                    Portfolio.id == pid, Portfolio.user_id == user.id
                )
            )
        ).scalar_one_or_none()
        if portfolio is None:
            # 404 (not 403) so we don't leak existence of other users' portfolios.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="portfolio not found"
            )
        return portfolio

    # No header → fallback to default. Guaranteed to exist for every user
    # after migration 0005 (one Principal is created per user).
    portfolio = (
        await session.execute(
            select(Portfolio)
            .where(Portfolio.user_id == user.id, Portfolio.is_default == True)  # noqa: E712
            .order_by(Portfolio.created_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if portfolio is None:
        # Defensive: a brand-new user with no default yet (shouldn't happen
        # after Phase 1, but keeps the system self-healing).
        portfolio = Portfolio(user_id=user.id, name="Principal", is_default=True)
        session.add(portfolio)
        await session.commit()
        await session.refresh(portfolio)
    return portfolio
