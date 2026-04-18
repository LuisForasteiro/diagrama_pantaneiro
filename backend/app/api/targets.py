from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_active_user
from app.api.deps import get_active_portfolio
from app.core.db import get_async_session
from app.models.investment_target import InvestmentTarget
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.target import TargetOut, TargetsUpdateBody

router = APIRouter(prefix="/api/targets", tags=["targets"])


@router.get("", response_model=list[TargetOut])
async def list_targets(
    user: User = Depends(current_active_user),
    portfolio: Portfolio = Depends(get_active_portfolio),
    session: AsyncSession = Depends(get_async_session),
) -> list[TargetOut]:
    rows = (
        await session.execute(
            select(InvestmentTarget).where(
                InvestmentTarget.portfolio_id == portfolio.id
            )
        )
    ).scalars().all()
    return [TargetOut.model_validate(r) for r in rows]


@router.put("", response_model=list[TargetOut])
async def replace_targets(
    body: TargetsUpdateBody,
    user: User = Depends(current_active_user),
    portfolio: Portfolio = Depends(get_active_portfolio),
    session: AsyncSession = Depends(get_async_session),
) -> list[TargetOut]:
    existing = (
        await session.execute(
            select(InvestmentTarget).where(
                InvestmentTarget.portfolio_id == portfolio.id
            )
        )
    ).scalars().all()
    by_type = {row.asset_type: row for row in existing}

    for entry in body.targets:
        row = by_type.get(entry.asset_type)
        if row is None:
            session.add(
                InvestmentTarget(
                    user_id=user.id,
                    portfolio_id=portfolio.id,
                    asset_type=entry.asset_type,
                    target_percentage=float(entry.target_percentage),
                )
            )
        else:
            row.target_percentage = float(entry.target_percentage)

    await session.commit()

    rows = (
        await session.execute(
            select(InvestmentTarget).where(
                InvestmentTarget.portfolio_id == portfolio.id
            )
        )
    ).scalars().all()
    return [TargetOut.model_validate(r) for r in rows]
