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
from sqlalchemy.exc import IntegrityError
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

    # No header → fallback to default. Migration 0005 created one Principal per
    # existing user; users registered later get theirs lazily, right here.
    user_id = user.id  # read now: a rollback below expires `user`
    portfolio = await _default_portfolio(session, user_id)
    if portfolio is None:
        portfolio = Portfolio(user_id=user_id, name="Principal", is_default=True)
        session.add(portfolio)
        try:
            await session.commit()
        except IntegrityError:
            # A new user's first page load fires several requests at once, and
            # each one tries to create the default: one wins, the others land
            # here on UNIQUE(user_id, name) — use the winner's instead of a 500.
            await session.rollback()
            portfolio = await _default_portfolio(session, user_id)
            if portfolio is None:
                raise
        else:
            await session.refresh(portfolio)
    return portfolio


async def _default_portfolio(session: AsyncSession, user_id: uuid.UUID) -> Portfolio | None:
    return (
        await session.execute(
            select(Portfolio)
            .where(Portfolio.user_id == user_id, Portfolio.is_default == True)  # noqa: E712
            .order_by(Portfolio.created_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
