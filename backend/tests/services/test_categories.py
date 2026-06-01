from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.category import Category
from app.models.position import Position


async def test_category_and_position_link(session_maker) -> None:
    async with session_maker() as session:
        uid = uuid.uuid4()
        pid = uuid.uuid4()
        grp = Category(
            id=uuid.uuid4(),
            user_id=uid,
            portfolio_id=pid,
            parent_id=None,
            name="Brasil",
            weight_pct=25.0,
            display_order=0,
        )
        session.add(grp)
        await session.flush()
        pos = Position(
            id=uuid.uuid4(),
            user_id=uid,
            portfolio_id=pid,
            name="BBAS3",
            asset_type="acoes_nacionais",
            amount=10,
            strength=5,
            category_id=grp.id,
        )
        session.add(pos)
        await session.commit()
        rows = (
            await session.execute(select(Category).where(Category.portfolio_id == pid))
        ).scalars().all()
        assert rows[0].name == "Brasil"
        got = (
            await session.execute(select(Position).where(Position.id == pos.id))
        ).scalar_one()
        assert got.category_id == grp.id
