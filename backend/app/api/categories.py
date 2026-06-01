"""Hierarchical allocation categories (max 2 levels) per portfolio.

GET returns the tree; PUT replaces it wholesale (mirrors PUT /api/targets).
Validation (sibling sums = 100, depth <= 2, non-empty names) runs both via
the Pydantic schema and the pure validate_tree() before persisting.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_active_user
from app.api.deps import get_active_portfolio
from app.core.db import get_async_session
from app.models.category import Category
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.category import (
    CategoryTreeIn,
    CategoryTreeOut,
    GroupOut,
    SubcategoryOut,
)
from app.services.categories import CatNode, CategoryValidationError, validate_tree

router = APIRouter(prefix="/api/categories", tags=["categories"])


async def _load_tree(
    session: AsyncSession, portfolio_id: uuid.UUID
) -> CategoryTreeOut:
    rows = (
        await session.execute(
            select(Category)
            .where(Category.portfolio_id == portfolio_id)
            .order_by(Category.display_order)
        )
    ).scalars().all()
    by_parent: dict[object, list[Category]] = {}
    for r in rows:
        by_parent.setdefault(r.parent_id, []).append(r)
    groups = []
    for g in by_parent.get(None, []):
        children = [
            SubcategoryOut(id=c.id, name=c.name, weight_pct=c.weight_pct)
            for c in by_parent.get(g.id, [])
        ]
        groups.append(
            GroupOut(id=g.id, name=g.name, weight_pct=g.weight_pct, children=children)
        )
    return CategoryTreeOut(groups=groups)


@router.get("", response_model=CategoryTreeOut)
async def get_categories(
    user: User = Depends(current_active_user),
    portfolio: Portfolio = Depends(get_active_portfolio),
    session: AsyncSession = Depends(get_async_session),
) -> CategoryTreeOut:
    return await _load_tree(session, portfolio.id)


@router.put("", response_model=CategoryTreeOut)
async def replace_categories(
    body: CategoryTreeIn,
    user: User = Depends(current_active_user),
    portfolio: Portfolio = Depends(get_active_portfolio),
    session: AsyncSession = Depends(get_async_session),
) -> CategoryTreeOut:
    # Validate as a flat node list (sibling sums, depth, names) before writing.
    nodes: list[CatNode] = []
    for gi, g in enumerate(body.groups):
        gid = f"g{gi}"
        nodes.append(CatNode(gid, None, g.name, g.weight_pct, gi))
        for ci, c in enumerate(g.children):
            nodes.append(CatNode(f"{gid}_{ci}", gid, c.name, c.weight_pct, ci))
    try:
        validate_tree(nodes)
    except CategoryValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # Replace wholesale: delete existing, then recreate. SET NULL on positions
    # keeps positions alive (they become uncategorized until re-assigned).
    existing = (
        await session.execute(
            select(Category).where(Category.portfolio_id == portfolio.id)
        )
    ).scalars().all()
    for row in existing:
        await session.delete(row)
    await session.flush()

    for gi, g in enumerate(body.groups):
        grp = Category(
            user_id=user.id,
            portfolio_id=portfolio.id,
            parent_id=None,
            name=g.name,
            weight_pct=g.weight_pct,
            display_order=gi,
        )
        session.add(grp)
        await session.flush()
        for ci, c in enumerate(g.children):
            session.add(
                Category(
                    user_id=user.id,
                    portfolio_id=portfolio.id,
                    parent_id=grp.id,
                    name=c.name,
                    weight_pct=c.weight_pct,
                    display_order=ci,
                )
            )
    await session.commit()
    return await _load_tree(session, portfolio.id)
