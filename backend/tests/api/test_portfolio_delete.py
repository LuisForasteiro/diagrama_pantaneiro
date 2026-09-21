from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy import func, select

from app.models import AporteEvent, Category, InvestmentTarget, Position
from app.schemas.target import ALL_CLASS_TYPES


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post(
        "/api/auth/register",
        json={"email": email, "password": "StrongPass!123"},
    )
    r = await client.post(
        "/api/auth/jwt/login",
        data={"username": email, "password": "StrongPass!123"},
    )
    return r.json()["access_token"]


async def test_delete_portfolio_removes_its_data(client: AsyncClient, session_maker) -> None:
    """SQLite doesn't enforce the schema's ON DELETE CASCADE (foreign_keys is
    off), so deleting a portfolio used to leave its positions, targets,
    categories and aportes behind as unreachable orphans."""
    token = await _register_and_login(client, "delete-pf@example.com")
    auth = {"Authorization": f"Bearer {token}"}
    await client.get("/api/positions", headers=auth)  # seed the default portfolio
    r = await client.post("/api/portfolios", json={"name": "Temporaria"}, headers=auth)
    assert r.status_code == 201
    doomed = r.json()["id"]
    scoped = {**auth, "X-Portfolio-Id": doomed}

    r = await client.post(
        "/api/positions",
        json={"name": "PETR4", "assetType": "acoes_nacionais", "amount": 10,
              "currentPrice": 30.0, "strength": 5},
        headers=scoped,
    )
    assert r.status_code == 201
    targets = [
        {"assetType": t, "targetPercentage": 100 if t == "acoes_nacionais" else 0}
        for t in ALL_CLASS_TYPES
    ]
    r = await client.put("/api/targets", json={"targets": targets}, headers=scoped)
    assert r.status_code == 200
    r = await client.put(
        "/api/categories",
        json={"groups": [{"name": "Brasil", "weightPct": 100,
                          "children": [{"name": "Acoes", "weightPct": 100}]}]},
        headers=scoped,
    )
    assert r.status_code == 200
    r = await client.post("/api/aportes", json={"value": 1000}, headers=scoped)
    assert r.status_code in (200, 201), r.text

    r = await client.delete(f"/api/portfolios/{doomed}", headers=auth)
    assert r.status_code == 204

    pid = uuid.UUID(doomed)
    async with session_maker() as session:
        for model in (Position, InvestmentTarget, Category, AporteEvent):
            left = (
                await session.execute(
                    select(func.count()).select_from(model).where(model.portfolio_id == pid)
                )
            ).scalar_one()
            assert left == 0, f"{model.__tablename__}: {left} orphan row(s)"
