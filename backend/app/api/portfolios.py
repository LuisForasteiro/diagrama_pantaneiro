from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func as sa_func
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_active_user
from app.core.db import get_async_session
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.portfolio import PortfolioCreate, PortfolioOut, PortfolioRename

router = APIRouter(prefix="/api/portfolios", tags=["portfolios"])


@router.get("", response_model=list[PortfolioOut])
async def list_portfolios(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[PortfolioOut]:
    rows = (
        await session.execute(
            select(Portfolio)
            .where(Portfolio.user_id == user.id)
            .order_by(Portfolio.created_at.asc())
        )
    ).scalars().all()
    return [PortfolioOut.model_validate(r) for r in rows]


@router.post("", response_model=PortfolioOut, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    body: PortfolioCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> PortfolioOut:
    portfolio = Portfolio(user_id=user.id, name=body.name, is_default=False)
    session.add(portfolio)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="portfolio name already exists",
        )
    await session.refresh(portfolio)
    return PortfolioOut.model_validate(portfolio)


@router.patch("/{portfolio_id}", response_model=PortfolioOut)
async def rename_portfolio(
    portfolio_id: uuid.UUID,
    body: PortfolioRename,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> PortfolioOut:
    portfolio = (
        await session.execute(
            select(Portfolio).where(
                Portfolio.id == portfolio_id, Portfolio.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="portfolio not found"
        )
    portfolio.name = body.name
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="portfolio name already exists",
        )
    await session.refresh(portfolio)
    return PortfolioOut.model_validate(portfolio)


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    total = (
        await session.execute(
            select(sa_func.count(Portfolio.id)).where(Portfolio.user_id == user.id)
        )
    ).scalar_one()
    if total <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="cannot delete last portfolio",
        )

    portfolio = (
        await session.execute(
            select(Portfolio).where(
                Portfolio.id == portfolio_id, Portfolio.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="portfolio not found"
        )

    was_default = portfolio.is_default
    await session.delete(portfolio)
    await session.flush()

    if was_default:
        # Promote the oldest remaining portfolio to default.
        replacement = (
            await session.execute(
                select(Portfolio)
                .where(Portfolio.user_id == user.id)
                .order_by(Portfolio.created_at.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if replacement is not None:
            replacement.is_default = True

    await session.commit()
