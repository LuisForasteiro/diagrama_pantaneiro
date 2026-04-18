from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diagram_question import DiagramQuestion
from app.models.investment_target import InvestmentTarget
from app.models.portfolio import Portfolio as PortfolioModel
from app.models.position import Position
from app.services.import_auvp import import_auvp_user_doc

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "auth_me.json"


@pytest.fixture
async def session(session_maker) -> AsyncSession:
    async with session_maker() as s:
        yield s


async def _seed_portfolio(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    user_id = uuid.uuid4()
    p = PortfolioModel(
        id=uuid.uuid4(), user_id=user_id, name="Principal", is_default=True
    )
    session.add(p)
    await session.flush()
    return user_id, p.id


async def test_import_creates_expected_row_counts(session: AsyncSession) -> None:
    user_id, portfolio_id = await _seed_portfolio(session)
    with FIXTURE.open("r", encoding="utf-8") as f:
        doc = json.load(f)

    await import_auvp_user_doc(session, user_id, portfolio_id, doc)
    await session.commit()

    positions = (
        await session.execute(select(Position).where(Position.user_id == user_id))
    ).scalars().all()
    targets = (
        await session.execute(select(InvestmentTarget).where(InvestmentTarget.user_id == user_id))
    ).scalars().all()
    questions = (
        await session.execute(select(DiagramQuestion).where(DiagramQuestion.user_id == user_id))
    ).scalars().all()

    assert len(positions) == 19
    assert len(targets) == 7
    # 11 cerrado + 6 imobiliarios = 17 questions
    assert len(questions) == 17


async def test_import_translates_rf_amount_from_value(session: AsyncSession) -> None:
    """Backend stores RF as amount=1, value=<brl>.
    Our Position stores amount=<brl> with no current_price."""
    user_id, portfolio_id = await _seed_portfolio(session)
    with FIXTURE.open("r", encoding="utf-8") as f:
        doc = json.load(f)

    await import_auvp_user_doc(session, user_id, portfolio_id, doc)
    await session.commit()

    lci = (
        await session.execute(
            select(Position).where(
                Position.user_id == user_id, Position.name == "LCI INTER 90,00"
            )
        )
    ).scalar_one()
    assert lci.asset_type == "rendafixa"
    assert lci.amount == 1074.0
    assert lci.current_price is None


async def test_import_preserves_diagram_responses(session: AsyncSession) -> None:
    user_id, portfolio_id = await _seed_portfolio(session)
    with FIXTURE.open("r", encoding="utf-8") as f:
        doc = json.load(f)

    await import_auvp_user_doc(session, user_id, portfolio_id, doc)
    await session.commit()

    wege3 = (
        await session.execute(
            select(Position).where(Position.user_id == user_id, Position.name == "WEGE3")
        )
    ).scalar_one()
    assert wege3.strength == 11
    assert wege3.diagram_responses is not None
    assert len(wege3.diagram_responses) == 11
