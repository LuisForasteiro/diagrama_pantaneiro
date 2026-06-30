"""DB -> domain Portfolio converter.

Bridges the SQLAlchemy models (positions, investment_targets, diagram_questions)
to the in-memory `Portfolio` domain type that the rebalancing algorithm
expects.

Positions and targets are scoped to a single portfolio. Diagram questions
are user-scoped (shared library across all of a user's portfolios), so the
loader takes both user_id and portfolio_id.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.diagram_question import DiagramQuestion
from app.models.investment_target import InvestmentTarget
from app.models.position import Position
from app.services.categories import CatNode, leaf_effective_targets
from app.services.types import Asset, Portfolio, Question


async def load_portfolio(
    session: AsyncSession,
    user_id: uuid.UUID,
    portfolio_id: uuid.UUID,
    exclude_position_ids: set[uuid.UUID] | None = None,
) -> Portfolio:
    """Load a portfolio snapshot for the algorithm.

    `exclude_position_ids` (optional) is used by the aporte-recompute flow
    to drop positions the user opted out of within a specific event (e.g.,
    a Tesouro title that no longer exists). The positions themselves are
    NOT touched in the DB — they're just filtered from the algorithm's view.
    """
    excluded = exclude_position_ids or set()
    pos_rows = (
        await session.execute(
            select(Position).where(Position.portfolio_id == portfolio_id)
        )
    ).scalars().all()
    pos_rows = [p for p in pos_rows if p.id not in excluded]
    tgt_rows = (
        await session.execute(
            select(InvestmentTarget).where(
                InvestmentTarget.portfolio_id == portfolio_id
            )
        )
    ).scalars().all()
    q_rows = (
        await session.execute(
            select(DiagramQuestion).where(DiagramQuestion.user_id == user_id)
        )
    ).scalars().all()

    # Detect mode: any category for this portfolio -> hierarchical category mode.
    cat_rows = (
        await session.execute(
            select(Category).where(Category.portfolio_id == portfolio_id)
        )
    ).scalars().all()

    # Semantic override: when effective_class is set, the algorithm and any
    # downstream aggregator treat the position as that class. The original
    # asset_type stays in the DB row (used only for price-routing in
    # market_data/registry.py and for the UI to show the override badge).
    if cat_rows:
        nodes = [
            CatNode(
                id=str(c.id),
                parent_id=(str(c.parent_id) if c.parent_id is not None else None),
                name=c.name,
                weight_pct=c.weight_pct,
                display_order=c.display_order,
            )
            for c in cat_rows
        ]
        targets = leaf_effective_targets(nodes)
        # Asset.group_key = the position's leaf category id (None if uncategorized;
        # uncategorized assets then fall back to their class, which has no target
        # in category mode, so they receive no aporte — exactly the desired rule).
        assets = [
            Asset(
                id=str(p.id),
                type=(p.effective_class or p.asset_type),  # type: ignore[arg-type]
                name=p.name,
                amount=p.amount,
                strength=p.strength,
                current_price=p.current_price,
                diagram_responses=p.diagram_responses,
                tradable=p.tradable,
                group_key=(str(p.category_id) if p.category_id is not None else None),
            )
            for p in pos_rows
        ]
    else:
        assets = [
            Asset(
                id=str(p.id),
                type=(p.effective_class or p.asset_type),  # type: ignore[arg-type]
                name=p.name,
                amount=p.amount,
                strength=p.strength,
                current_price=p.current_price,
                diagram_responses=p.diagram_responses,
                tradable=p.tradable,
            )
            for p in pos_rows
        ]
        targets = {t.asset_type: t.target_percentage for t in tgt_rows}
    questions = [
        Question(
            id=q.external_id or str(q.id),
            criteria=q.criterias,
            text=q.question_text,
            diagram=q.diagram_type,  # type: ignore[arg-type]
        )
        for q in q_rows
    ]
    return Portfolio(assets=assets, targets=targets, questions=questions)
