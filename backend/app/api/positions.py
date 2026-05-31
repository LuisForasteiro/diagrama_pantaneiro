from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_active_user
from app.api.deps import get_active_portfolio
from app.core.db import get_async_session
from app.models.diagram_question import DiagramQuestion
from app.models.portfolio import Portfolio
from app.models.position import Position
from app.models.user import User
from app.schemas.position import PositionCreate, PositionOut, PositionUpdate
from app.services.default_diagram_questions import (
    ETF_DIAGRAM_TYPE,
    ETF_QUESTIONS,
)
from app.services.import_auvp import import_auvp_user_doc
from app.services.strength import DIAGRAM_FOR_CLASS

router = APIRouter(prefix="/api/positions", tags=["positions"])

# Captured AUVP fixture that we auto-seed on first login.
# Path resolves to backend/tests/fixtures/auth_me.json in both dev (bind mount)
# and the prod image (tests/ is COPYed at build time).
_SEED_FIXTURE = (
    Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures" / "auth_me.json"
)


def _to_out(p: Position) -> PositionOut:
    current_value = p.amount * p.current_price if p.current_price is not None else p.amount
    return PositionOut(
        id=p.id,
        name=p.name,
        asset_type=p.asset_type,
        effective_class=p.effective_class,
        amount=p.amount,
        current_price=p.current_price,
        current_value_brl=current_value,
        strength=p.strength,
        diagram_responses=p.diagram_responses,
        source=p.source,
    )


async def _bank_size(
    session: AsyncSession, user_id: uuid.UUID, diagram_type: str
) -> int:
    """Count diagram_questions for this user matching the given diagram type."""
    from sqlalchemy import func as sa_func

    return (
        await session.execute(
            select(sa_func.count(DiagramQuestion.id)).where(
                DiagramQuestion.user_id == user_id,
                DiagramQuestion.diagram_type == diagram_type,
            )
        )
    ).scalar_one()


def _diagram_for(asset_type: str) -> str | None:
    return DIAGRAM_FOR_CLASS.get(asset_type)  # type: ignore[arg-type]


async def _compute_strength_if_diagram(
    session: AsyncSession,
    user_id: uuid.UUID,
    asset_type: str,
    diagram_responses: list[str] | None,
    fallback_strength: int,
) -> int:
    """If the asset type has an associated diagram AND responses were provided,
    compute strength = 2 x yes - N. Otherwise return the caller-supplied strength."""
    diagram = _diagram_for(asset_type)
    if diagram is None or diagram_responses is None:
        return fallback_strength
    n = await _bank_size(session, user_id, diagram)
    # Count only responses that map to a known question (drops stale external_ids
    # from imported AUVP data once the frontend has reconciled them). Cap to [-n, n]
    # as a safety net in case stale IDs still leak through.
    known_ids = {
        str(row[0])
        for row in (
            await session.execute(
                select(DiagramQuestion.id).where(
                    DiagramQuestion.user_id == user_id,
                    DiagramQuestion.diagram_type == diagram,
                )
            )
        ).all()
    }
    yes = sum(1 for r in diagram_responses if r in known_ids)
    return max(-n, min(n, 2 * yes - n))


async def _ensure_etf_questions(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Backfill the default ETF diagram questions for a user (idempotent).

    Mirrors migration 0006. The migration runs once per user at upgrade
    time; this hook covers users created AFTER the migration ran.
    """
    existing_ext_ids = {
        row[0]
        for row in (
            await session.execute(
                select(DiagramQuestion.external_id).where(
                    DiagramQuestion.user_id == user_id,
                    DiagramQuestion.diagram_type == ETF_DIAGRAM_TYPE,
                )
            )
        ).all()
    }
    added = False
    for q in ETF_QUESTIONS:
        if q["external_id"] in existing_ext_ids:
            continue
        session.add(
            DiagramQuestion(
                user_id=user_id,
                diagram_type=ETF_DIAGRAM_TYPE,
                criterias=q["criterias"],
                question_text=q["question_text"],
                display_order=q["display_order"],
                external_id=q["external_id"],
            )
        )
        added = True
    if added:
        await session.commit()


async def _seed_if_empty(
    session: AsyncSession, user_id: uuid.UUID, portfolio_id: uuid.UUID
) -> None:
    # Always ensure default ETF questions exist for this user — cheap, idempotent,
    # covers users created after migration 0006 ran.
    await _ensure_etf_questions(session, user_id)

    # Only auto-import the AUVP fixture for a brand-new user (no positions
    # anywhere yet). Creating a second portfolio must NOT re-seed — the user
    # expects it to start empty.
    existing = (
        await session.execute(
            select(Position).where(Position.user_id == user_id).limit(1)
        )
    ).first()
    if existing is not None:
        return
    if not _SEED_FIXTURE.exists():
        return  # prod image without fixtures: silently skip
    with _SEED_FIXTURE.open("r", encoding="utf-8") as f:
        doc = json.load(f)
    await import_auvp_user_doc(session, user_id, portfolio_id, doc)
    await session.commit()


@router.get("", response_model=list[PositionOut])
async def list_positions(
    user: User = Depends(current_active_user),
    portfolio: Portfolio = Depends(get_active_portfolio),
    session: AsyncSession = Depends(get_async_session),
) -> list[PositionOut]:
    await _seed_if_empty(session, user.id, portfolio.id)
    rows = (
        await session.execute(
            select(Position).where(Position.portfolio_id == portfolio.id)
        )
    ).scalars().all()
    return [_to_out(p) for p in rows]


@router.post("", response_model=PositionOut, status_code=status.HTTP_201_CREATED)
async def create_position(
    body: PositionCreate,
    user: User = Depends(current_active_user),
    portfolio: Portfolio = Depends(get_active_portfolio),
    session: AsyncSession = Depends(get_async_session),
) -> PositionOut:
    strength = await _compute_strength_if_diagram(
        session, user.id, body.asset_type, body.diagram_responses, body.strength
    )
    pos = Position(
        user_id=user.id,
        portfolio_id=portfolio.id,
        name=body.name,
        asset_type=body.asset_type,
        effective_class=body.effective_class,
        amount=body.amount,
        current_price=body.current_price,
        strength=strength,
        diagram_responses=body.diagram_responses,
        source="user",
    )
    session.add(pos)
    await session.commit()
    await session.refresh(pos)
    return _to_out(pos)


@router.patch("/{position_id}", response_model=PositionOut)
async def update_position(
    position_id: uuid.UUID,
    body: PositionUpdate,
    user: User = Depends(current_active_user),
    portfolio: Portfolio = Depends(get_active_portfolio),
    session: AsyncSession = Depends(get_async_session),
) -> PositionOut:
    pos = (
        await session.execute(
            select(Position).where(
                Position.id == position_id, Position.portfolio_id == portfolio.id
            )
        )
    ).scalar_one_or_none()
    if pos is None:
        raise HTTPException(status_code=404, detail="position not found")

    updates = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(pos, k, v)

    # If diagram_responses changed AND this asset has a diagram, re-derive strength.
    # Explicit strength in the same PATCH body still wins (we check exclude_unset).
    if (
        "diagram_responses" in updates
        and "strength" not in updates
        and _diagram_for(pos.asset_type) is not None
    ):
        pos.strength = await _compute_strength_if_diagram(
            session, user.id, pos.asset_type, pos.diagram_responses, pos.strength
        )

    await session.commit()
    await session.refresh(pos)
    return _to_out(pos)


@router.delete("/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_position(
    position_id: uuid.UUID,
    user: User = Depends(current_active_user),
    portfolio: Portfolio = Depends(get_active_portfolio),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    pos = (
        await session.execute(
            select(Position).where(
                Position.id == position_id, Position.portfolio_id == portfolio.id
            )
        )
    ).scalar_one_or_none()
    if pos is None:
        raise HTTPException(status_code=404, detail="position not found")
    await session.delete(pos)
    await session.commit()
