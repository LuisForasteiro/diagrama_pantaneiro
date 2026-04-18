"""Aporte business logic: create events + apply allocations.

Does NOT handle HTTP or auth - that's the API layer's job. These functions
take an AsyncSession and caller-verified IDs, then do the domain work.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aporte_allocation import AporteAllocation
from app.models.aporte_event import AporteEvent
from app.models.position import Position
from app.services.algorithm import compute_suggestions
from app.services.portfolio_loader import load_portfolio

RF_TYPES = {"rendafixa", "rendafixa_internacional"}


async def create_aporte_event(
    session: AsyncSession,
    user_id: uuid.UUID,
    portfolio_id: uuid.UUID,
    aporte_value_brl: float,
) -> AporteEvent:
    """Compute suggestions for the given portfolio + persist them as a new
    AporteEvent with unapplied AporteAllocations."""
    portfolio = await load_portfolio(session, user_id, portfolio_id)
    suggestions = compute_suggestions(portfolio, aporte_value_brl)

    event = AporteEvent(
        user_id=user_id,
        portfolio_id=portfolio_id,
        aporte_value_brl=aporte_value_brl,
    )
    session.add(event)
    await session.flush()  # assigns event.id

    for s in suggestions:
        session.add(
            AporteAllocation(
                aporte_event_id=event.id,
                position_id=uuid.UUID(s.asset_id),
                position_name_snapshot=s.asset_name,
                asset_type_snapshot=s.asset_type,
                price_at_aporte_brl=s.current_price,
                suggested_value_brl=s.suggestion_value,
                suggested_quantity=s.suggestion_quantity,
            )
        )
    await session.flush()
    await session.refresh(event, ["allocations"])
    return event


async def apply_allocation(
    session: AsyncSession,
    allocation_id: uuid.UUID,
    applied_value_brl: float | None = None,
    applied_quantity: float | None = None,
) -> AporteAllocation:
    """Mark an allocation applied and mutate the referenced Position's amount.

    If applied_value_brl/applied_quantity are omitted, the suggested values
    are used as-is. For RF positions (amount stores BRL), amount is
    incremented by applied_value_brl; for crypto and stocks (amount stores
    shares), amount is incremented by applied_quantity.
    """
    alloc = (
        await session.execute(
            select(AporteAllocation).where(AporteAllocation.id == allocation_id)
        )
    ).scalar_one()

    if alloc.applied:
        return alloc

    value = (
        applied_value_brl if applied_value_brl is not None else alloc.suggested_value_brl
    )
    quantity = (
        applied_quantity if applied_quantity is not None else alloc.suggested_quantity
    )

    if alloc.position_id is not None:
        position = (
            await session.execute(
                select(Position).where(Position.id == alloc.position_id)
            )
        ).scalar_one_or_none()
        if position is not None:
            # Unpriced RF (private LCI/CDB): amount stores BRL, add value.
            # Priced positions (stocks, crypto, Tesouro): amount stores units,
            # add the applied quantity.
            if position.asset_type in RF_TYPES and position.current_price is None:
                position.amount = position.amount + value
            else:
                position.amount = position.amount + quantity

    alloc.applied = True
    alloc.applied_at = datetime.now(timezone.utc)
    alloc.applied_value_brl = value
    alloc.applied_quantity = quantity
    return alloc
