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
from app.models.category import Category
from app.models.diagram_question import DiagramQuestion
from app.models.portfolio import Portfolio
from app.models.position import Position
from app.models.user import User
from app.schemas.position import PositionCreate, PositionOut, PositionUpdate
from app.services.default_diagram_questions import DEFAULT_QUESTION_BANKS
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
        price_updated_at=p.price_updated_at,
        category_id=p.category_id,
        strength=p.strength,
        diagram_responses=p.diagram_responses,
        tradable=p.tradable,
        source=p.source,
    )


async def _validate_leaf_category(
    session: AsyncSession, portfolio_id: uuid.UUID, category_id: uuid.UUID | None
) -> None:
    """Ensure category_id (if given) is a leaf category of the active portfolio.
    A leaf is a category with no children. Groups with children are rejected."""
    if category_id is None:
        return
    cat = (
        await session.execute(
            select(Category).where(
                Category.id == category_id,
                Category.portfolio_id == portfolio_id,
            )
        )
    ).scalar_one_or_none()
    if cat is None:
        raise HTTPException(status_code=422, detail="category not found in portfolio")
    has_children = (
        await session.execute(
            select(Category.id).where(Category.parent_id == category_id).limit(1)
        )
    ).first()
    if has_children is not None:
        raise HTTPException(
            status_code=422, detail="category must be a leaf (no children)"
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


async def _ensure_default_questions(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Backfill the default diagram questions for all three banks (idempotent).

    Covers cerrado (ações), imobiliários (FIIs/REITs) and ETFs. Previously only
    the ETF bank was backfilled here; the other two relied on the AUVP fixture,
    which the prod image does not ship, leaving self-host users without an
    ações/imobiliários checklist. Dedup is by `external_id`, so re-runs and the
    AUVP fixture import never produce duplicates.
    """
    added = False
    for diagram_type, questions in DEFAULT_QUESTION_BANKS:
        existing_ext_ids = {
            row[0]
            for row in (
                await session.execute(
                    select(DiagramQuestion.external_id).where(
                        DiagramQuestion.user_id == user_id,
                        DiagramQuestion.diagram_type == diagram_type,
                    )
                )
            ).all()
        }
        for q in questions:
            if q["external_id"] in existing_ext_ids:
                continue
            session.add(
                DiagramQuestion(
                    user_id=user_id,
                    diagram_type=diagram_type,
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
    # Always ensure the default question banks exist for this user — cheap,
    # idempotent, and (unlike the AUVP fixture) present in the prod image.
    await _ensure_default_questions(session, user_id)

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
    # Strength derives from the *effective* class's diagram, not the raw
    # asset_type. An asset overridden to a manual-strength class (e.g. a
    # Bitcoin ETF wrapper reclassified as criptomoedas) has no diagram, so its
    # strength stays manual instead of being computed to a negative value.
    # Mirrors portfolio_loader's `effective_class or asset_type` rule.
    effective_type = body.effective_class or body.asset_type
    strength = await _compute_strength_if_diagram(
        session, user.id, effective_type, body.diagram_responses, body.strength
    )
    await _validate_leaf_category(session, portfolio.id, body.category_id)
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
        tradable=body.tradable,
        source="user",
        category_id=body.category_id,
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
    if "category_id" in updates:
        await _validate_leaf_category(session, portfolio.id, updates["category_id"])
    for k, v in updates.items():
        setattr(pos, k, v)

    # If diagram_responses changed AND this asset's *effective* class has a
    # diagram, re-derive strength. Using effective_class (not asset_type) means
    # an override to a manual-strength class (crypto/RF) keeps its manual
    # strength instead of being recomputed negative from the underlying
    # asset_type's diagram. Explicit strength in the same PATCH body still wins
    # (we check exclude_unset).
    effective_type = pos.effective_class or pos.asset_type
    if (
        "diagram_responses" in updates
        and "strength" not in updates
        and _diagram_for(effective_type) is not None
    ):
        pos.strength = await _compute_strength_if_diagram(
            session, user.id, effective_type, pos.diagram_responses, pos.strength
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
