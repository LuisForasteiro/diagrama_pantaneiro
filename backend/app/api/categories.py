"""Hierarchical allocation categories (max 2 levels) per portfolio.

GET returns the tree; PUT replaces it wholesale (mirrors PUT /api/targets).
Validation (sibling sums = 100, depth <= 2, non-empty names) runs both via
the Pydantic schema and the pure validate_tree() before persisting.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_active_user
from app.api.deps import get_active_portfolio
from app.core.db import get_async_session
from app.models.category import Category
from app.models.portfolio import Portfolio
from app.models.position import Position
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

    # Reconcile by id (mirrors PUT /api/targets' update-in-place pattern):
    # nodes that arrive with an id matching an existing row are UPDATED in
    # place — keeping the id so positions stay linked. New nodes (no id, or an
    # id not in this portfolio) are inserted. Removed nodes are deleted, and
    # their positions' category_id is explicitly NULLed (we can't rely on the
    # ON DELETE SET NULL FK because SQLite ships with FK enforcement off).
    existing = {
        c.id: c
        for c in (
            await session.execute(
                select(Category).where(Category.portfolio_id == portfolio.id)
            )
        ).scalars().all()
    }
    seen: set[uuid.UUID] = set()

    async def _upsert(
        node_id: uuid.UUID | None,
        parent_id: uuid.UUID | None,
        name: str,
        weight: float,
        order: int,
    ) -> Category:
        cat = existing.get(node_id) if node_id is not None else None
        if cat is None:
            cat = Category(
                user_id=user.id,
                portfolio_id=portfolio.id,
                parent_id=parent_id,
                name=name,
                weight_pct=weight,
                display_order=order,
            )
            session.add(cat)
            await session.flush()
        else:
            cat.parent_id = parent_id
            cat.name = name
            cat.weight_pct = weight
            cat.display_order = order
        seen.add(cat.id)
        return cat

    for gi, g in enumerate(body.groups):
        grp = await _upsert(g.id, None, g.name, g.weight_pct, gi)
        for ci, c in enumerate(g.children):
            await _upsert(c.id, grp.id, c.name, c.weight_pct, ci)

    removed_ids = [cid for cid in existing if cid not in seen]
    if removed_ids:
        await session.execute(
            update(Position)
            .where(Position.category_id.in_(removed_ids))
            .values(category_id=None)
        )
        for cid in removed_ids:
            await session.delete(existing[cid])

    await session.commit()
    return await _load_tree(session, portfolio.id)
