from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.models.category import Category
from app.models.position import Position
from app.services.categories import (
    CatNode,
    CategoryValidationError,
    leaf_effective_targets,
    validate_tree,
)


def _tree() -> list[CatNode]:
    # Bitcoin 40 (group-leaf) | Brasil 25 (Ações 50 / RF 50) | Internacional 35
    return [
        CatNode("g_btc", None, "Bitcoin", 40.0, 0),
        CatNode("g_br", None, "Brasil", 25.0, 1),
        CatNode("s_br_acoes", "g_br", "Ações", 50.0, 0),
        CatNode("s_br_rf", "g_br", "Renda Fixa", 50.0, 1),
        CatNode("g_int", None, "Internacional", 35.0, 2),
        CatNode("s_int_acoes", "g_int", "Ações americanas", 100.0, 0),
    ]


def test_leaf_effective_targets_computes_products() -> None:
    eff = leaf_effective_targets(_tree())
    assert eff["g_btc"] == pytest.approx(40.0)  # group-leaf
    assert eff["s_br_acoes"] == pytest.approx(12.5)  # 25% x 50%
    assert eff["s_br_rf"] == pytest.approx(12.5)
    assert eff["s_int_acoes"] == pytest.approx(35.0)  # 35% x 100%
    assert "g_br" not in eff
    assert "g_int" not in eff
    assert sum(eff.values()) == pytest.approx(100.0)


def test_validate_tree_accepts_valid() -> None:
    validate_tree(_tree())  # no raise


def test_validate_tree_rejects_group_sum_not_100() -> None:
    nodes = [
        CatNode("a", None, "A", 40.0, 0),
        CatNode("b", None, "B", 40.0, 1),
    ]
    with pytest.raises(CategoryValidationError):
        validate_tree(nodes)


def test_validate_tree_rejects_children_sum_not_100() -> None:
    nodes = [
        CatNode("g", None, "G", 100.0, 0),
        CatNode("c1", "g", "C1", 30.0, 0),
        CatNode("c2", "g", "C2", 30.0, 1),
    ]
    with pytest.raises(CategoryValidationError):
        validate_tree(nodes)


def test_validate_tree_rejects_depth_3() -> None:
    nodes = [
        CatNode("g", None, "G", 100.0, 0),
        CatNode("c", "g", "C", 100.0, 0),
        CatNode("gc", "c", "GC", 100.0, 0),  # neto: proibido
    ]
    with pytest.raises(CategoryValidationError):
        validate_tree(nodes)


def test_validate_tree_rejects_blank_name() -> None:
    with pytest.raises(CategoryValidationError):
        validate_tree([CatNode("g", None, "  ", 100.0, 0)])


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
