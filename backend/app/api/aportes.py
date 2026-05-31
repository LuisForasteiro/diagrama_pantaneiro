from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_active_user
from app.api.deps import get_active_portfolio
from app.core.db import get_async_session
from app.models.aporte_allocation import AporteAllocation
from app.models.aporte_event import AporteEvent
from app.models.portfolio import Portfolio
from app.models.position import Position
from app.models.user import User
from app.schemas.aporte import (
    AporteAllocationOut,
    AporteCreate,
    AporteEventOut,
    ApplyRequest,
)
from app.services.aporte_service import (
    AporteHasAppliedError,
    apply_allocation,
    create_aporte_event,
    recompute_event_excluding,
)

router = APIRouter(prefix="/api/aportes", tags=["aportes"])


async def _get_portfolio_event(
    session: AsyncSession, event_id: uuid.UUID, portfolio_id: uuid.UUID
) -> AporteEvent:
    event = (
        await session.execute(
            select(AporteEvent).where(
                AporteEvent.id == event_id,
                AporteEvent.portfolio_id == portfolio_id,
            )
        )
    ).scalar_one_or_none()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="aporte not found"
        )
    return event


@router.post("", response_model=AporteEventOut, status_code=status.HTTP_201_CREATED)
async def create_aporte(
    body: AporteCreate,
    user: User = Depends(current_active_user),
    portfolio: Portfolio = Depends(get_active_portfolio),
    session: AsyncSession = Depends(get_async_session),
) -> AporteEventOut:
    event = await create_aporte_event(session, user.id, portfolio.id, body.value)
    await session.commit()
    fresh = await _get_portfolio_event(session, event.id, portfolio.id)
    return AporteEventOut.model_validate(fresh)


@router.get("", response_model=list[AporteEventOut])
async def list_aportes(
    user: User = Depends(current_active_user),
    portfolio: Portfolio = Depends(get_active_portfolio),
    session: AsyncSession = Depends(get_async_session),
) -> list[AporteEventOut]:
    events = (
        await session.execute(
            select(AporteEvent)
            .where(AporteEvent.portfolio_id == portfolio.id)
            .order_by(AporteEvent.created_at.desc())
        )
    ).scalars().all()
    return [AporteEventOut.model_validate(e) for e in events]


@router.get("/{event_id}", response_model=AporteEventOut)
async def get_aporte(
    event_id: uuid.UUID,
    user: User = Depends(current_active_user),
    portfolio: Portfolio = Depends(get_active_portfolio),
    session: AsyncSession = Depends(get_async_session),
) -> AporteEventOut:
    event = await _get_portfolio_event(session, event_id, portfolio.id)
    return AporteEventOut.model_validate(event)


@router.post(
    "/{event_id}/allocations/{allocation_id}/apply",
    response_model=AporteAllocationOut,
)
async def apply(
    event_id: uuid.UUID,
    allocation_id: uuid.UUID,
    body: ApplyRequest,
    user: User = Depends(current_active_user),
    portfolio: Portfolio = Depends(get_active_portfolio),
    session: AsyncSession = Depends(get_async_session),
) -> AporteAllocationOut:
    event = await _get_portfolio_event(session, event_id, portfolio.id)
    alloc = (
        await session.execute(
            select(AporteAllocation).where(
                AporteAllocation.id == allocation_id,
                AporteAllocation.aporte_event_id == event.id,
            )
        )
    ).scalar_one_or_none()
    if alloc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="allocation not found"
        )
    updated = await apply_allocation(
        session, alloc.id, body.applied_value_brl, body.applied_quantity
    )
    await session.commit()
    await session.refresh(updated)
    return AporteAllocationOut.model_validate(updated)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_aporte(
    event_id: uuid.UUID,
    user: User = Depends(current_active_user),
    portfolio: Portfolio = Depends(get_active_portfolio),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    event = await _get_portfolio_event(session, event_id, portfolio.id)
    if any(a.applied for a in event.allocations):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="cannot delete aporte with applied allocations",
        )
    await session.delete(event)
    await session.commit()


@router.delete(
    "/{event_id}/allocations/{allocation_id}",
    response_model=AporteEventOut,
)
async def delete_allocation(
    event_id: uuid.UUID,
    allocation_id: uuid.UUID,
    user: User = Depends(current_active_user),
    portfolio: Portfolio = Depends(get_active_portfolio),
    session: AsyncSession = Depends(get_async_session),
) -> AporteEventOut:
    event = await _get_portfolio_event(session, event_id, portfolio.id)
    alloc = next((a for a in event.allocations if a.id == allocation_id), None)
    if alloc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="allocation not found"
        )

    # Sticky exclusion: keep previously-deleted positions out across
    # consecutive deletes. We don't store a separate ledger — instead we
    # derive the set as `(all portfolio positions) − (currently allocated)`,
    # then add the position the user is deleting now. Positions that were
    # never allocatable (negative strength, no target) are also in this
    # gap, but excluding them is a no-op for the algorithm.
    portfolio_position_ids = {
        row[0]
        for row in (
            await session.execute(
                select(Position.id).where(Position.portfolio_id == portfolio.id)
            )
        ).all()
    }
    currently_allocated = {
        a.position_id for a in event.allocations if a.position_id is not None
    }
    excluded = portfolio_position_ids - currently_allocated
    if alloc.position_id is not None:
        excluded.add(alloc.position_id)

    try:
        updated = await recompute_event_excluding(
            session, event, user.id, excluded
        )
    except AporteHasAppliedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="cannot edit aporte after applying",
        )
    await session.commit()
    await session.refresh(updated, ["allocations"])
    return AporteEventOut.model_validate(updated)
