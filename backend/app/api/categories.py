from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_active_user
from app.api.deps import get_active_portfolio
from app.core.db import get_async_session
from app.models.category import Category
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.category import CategoryNodeIn, CategoryOut, CategoryTreeUpdate

router = APIRouter(prefix="/api/categories", tags=["categories"])


def _build_tree(rows: list[Category]) -> list[CategoryOut]:
    by_parent: dict[str | None, list[Category]] = {}
    for r in rows:
        by_parent.setdefault(str(r.parent_id) if r.parent_id else None, []).append(r)
    for bucket in by_parent.values():
        bucket.sort(key=lambda c: c.display_order)

    def node(c: Category) -> CategoryOut:
        children = by_parent.get(str(c.id), [])
        return CategoryOut(
            id=c.id,
            parent_id=c.parent_id,
            name=c.name,
            weight_pct=c.weight_pct,
            display_order=c.display_order,
            children=[node(ch) for ch in children],
        )

    return [node(g) for g in by_parent.get(None, [])]


@router.get("", response_model=list[CategoryOut])
async def list_categories(
    user: User = Depends(current_active_user),
    portfolio: Portfolio = Depends(get_active_portfolio),
    session: AsyncSession = Depends(get_async_session),
) -> list[CategoryOut]:
    rows = (
        await session.execute(
            select(Category).where(Category.portfolio_id == portfolio.id)
        )
    ).scalars().all()
    return _build_tree(list(rows))


@router.put("", response_model=list[CategoryOut])
async def replace_categories(
    body: CategoryTreeUpdate,
    user: User = Depends(current_active_user),
    portfolio: Portfolio = Depends(get_active_portfolio),
    session: AsyncSession = Depends(get_async_session),
) -> list[CategoryOut]:
    # Full replace: delete the old tree, insert the new one. positions.category_id
    # is ON DELETE SET NULL, so reassignment survives as "sem categoria" until
    # the user re-picks (acceptable for a full re-author).
    existing = (
        await session.execute(
            select(Category).where(Category.portfolio_id == portfolio.id)
        )
    ).scalars().all()
    for row in existing:
        await session.delete(row)
    await session.flush()

    async def add(node: CategoryNodeIn, parent_id: object, order: int) -> None:
        cat = Category(
            user_id=user.id,
            portfolio_id=portfolio.id,
            parent_id=parent_id,
            name=node.name,
            weight_pct=float(node.weight_pct),
            display_order=node.display_order if node.display_order is not None else order,
        )
        session.add(cat)
        await session.flush()  # assigns cat.id
        for j, child in enumerate(node.children):
            await add(child, cat.id, j)

    for i, group in enumerate(body.groups):
        await add(group, None, i)

    await session.commit()
    rows = (
        await session.execute(
            select(Category).where(Category.portfolio_id == portfolio.id)
        )
    ).scalars().all()
    return _build_tree(list(rows))
