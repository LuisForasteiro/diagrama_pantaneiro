from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import Portfolio as PortfolioModel
from app.services.import_auvp import import_auvp_user_doc
from app.services.portfolio_loader import load_portfolio

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "auth_me.json"


@pytest.fixture
async def session(session_maker) -> AsyncSession:
    async with session_maker() as s:
        yield s


async def _seed(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    user_id = uuid.uuid4()
    portfolio_row = PortfolioModel(
        id=uuid.uuid4(), user_id=user_id, name="Principal", is_default=True
    )
    session.add(portfolio_row)
    await session.flush()
    with FIXTURE.open("r", encoding="utf-8") as f:
        doc = json.load(f)
    await import_auvp_user_doc(session, user_id, portfolio_row.id, doc)
    await session.commit()
    return user_id, portfolio_row.id


async def test_loader_returns_portfolio_matching_captured_fixture(
    session: AsyncSession,
) -> None:
    user_id, portfolio_id = await _seed(session)
    portfolio = await load_portfolio(session, user_id, portfolio_id)

    assert len(portfolio.assets) == 19
    assert len(portfolio.questions) == 17
    assert sum(portfolio.targets.values()) == 100.0
    assert portfolio.targets["acoes_nacionais"] == 55.0

    vale3 = next(a for a in portfolio.assets if a.name == "VALE3")
    assert vale3.type == "acoes_nacionais"
    assert vale3.amount == 50
    assert vale3.current_price is not None
    assert vale3.strength == 7

    lci = next(a for a in portfolio.assets if a.name == "LCI INTER 90,00")
    assert lci.type == "rendafixa"
    assert lci.amount == 1074.0
    assert lci.current_price is None


async def test_loader_produces_suggestions_matching_backend_at_r500(
    session: AsyncSession,
) -> None:
    """End-to-end parity: DB-loaded portfolio + algorithm should match
    the captured R$500 backend response."""
    from app.services.algorithm import compute_suggestions

    user_id, portfolio_id = await _seed(session)
    portfolio = await load_portfolio(session, user_id, portfolio_id)
    suggestions = compute_suggestions(portfolio, 500)

    assert len(suggestions) == 3  # R$500 fixture has 3 rows
    total = sum(s.suggestion_value for s in suggestions)
    assert abs(total - 500) < 0.01


async def test_loader_emits_effective_class_when_set(
    session: AsyncSession,
) -> None:
    """An OBTC3 stored as asset_type='acoes_nacionais' but with
    effective_class='criptomoedas' should appear to the algorithm as crypto."""
    from app.models.position import Position

    user_id = uuid.uuid4()
    portfolio_row = PortfolioModel(
        id=uuid.uuid4(), user_id=user_id, name="Principal", is_default=True
    )
    session.add(portfolio_row)
    await session.flush()
    session.add(
        Position(
            user_id=user_id,
            portfolio_id=portfolio_row.id,
            name="OBTC3",
            asset_type="acoes_nacionais",
            effective_class="criptomoedas",
            amount=10,
            current_price=5,
            strength=4,
            source="user",
        )
    )
    await session.commit()

    portfolio = await load_portfolio(session, user_id, portfolio_row.id)
    obtc3 = next(a for a in portfolio.assets if a.name == "OBTC3")
    assert obtc3.type == "criptomoedas"


async def test_loader_category_mode_sets_group_keys_and_effective_targets(
    session_maker,
) -> None:
    from app.models.category import Category
    from app.models.position import Position

    async with session_maker() as session:
        uid = uuid.uuid4()
        pf = PortfolioModel(id=uuid.uuid4(), user_id=uid, name="P", is_default=True)
        session.add(pf)
        await session.flush()
        # Brasil 100% -> Ações 60 / RF 40
        g = Category(
            user_id=uid, portfolio_id=pf.id, parent_id=None,
            name="Brasil", weight_pct=100.0, display_order=0,
        )
        session.add(g)
        await session.flush()
        acoes = Category(
            user_id=uid, portfolio_id=pf.id, parent_id=g.id,
            name="Ações", weight_pct=60.0, display_order=0,
        )
        rf = Category(
            user_id=uid, portfolio_id=pf.id, parent_id=g.id,
            name="RF", weight_pct=40.0, display_order=1,
        )
        session.add_all([acoes, rf])
        await session.flush()
        session.add(
            Position(
                user_id=uid, portfolio_id=pf.id, name="BBAS3",
                asset_type="acoes_nacionais", amount=10, strength=5,
                current_price=10.0, category_id=acoes.id,
            )
        )
        await session.commit()
        acoes_id = str(acoes.id)
        rf_id = str(rf.id)
        pf_id = pf.id
        uid2 = uid

    async with session_maker() as session:
        portfolio = await load_portfolio(session, uid2, pf_id)

    # meta efetiva por folha: Ações = 100% x 60% = 60; RF = 40
    assert portfolio.targets[acoes_id] == 60.0
    assert portfolio.targets[rf_id] == 40.0
    # group_key do asset = categoria folha
    assert portfolio.assets[0].group_key == acoes_id


async def test_loader_flat_mode_unchanged_when_no_categories(session_maker) -> None:
    from app.models.investment_target import InvestmentTarget
    from app.models.position import Position

    async with session_maker() as session:
        uid = uuid.uuid4()
        pf = PortfolioModel(id=uuid.uuid4(), user_id=uid, name="P2", is_default=True)
        session.add(pf)
        await session.flush()
        session.add(
            InvestmentTarget(
                user_id=uid, portfolio_id=pf.id,
                asset_type="acoes_nacionais", target_percentage=100.0,
            )
        )
        session.add(
            Position(
                user_id=uid, portfolio_id=pf.id, name="BBAS3",
                asset_type="acoes_nacionais", amount=10, strength=5,
                current_price=10.0,
            )
        )
        await session.commit()
        pf_id = pf.id
        uid2 = uid

    async with session_maker() as session:
        portfolio = await load_portfolio(session, uid2, pf_id)

    assert portfolio.targets == {"acoes_nacionais": 100.0}
    assert portfolio.assets[0].group_key is None  # modo plano
