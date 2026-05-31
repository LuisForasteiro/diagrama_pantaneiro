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
