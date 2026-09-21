from __future__ import annotations

import asyncio
from pathlib import Path

from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401  (registers every table on Base.metadata)
from app.core import db as db_module
from app.core.db import Base
from app.main import app
from app.models import Portfolio


async def test_parallel_first_requests_share_one_default_portfolio(tmp_path: Path) -> None:
    """A new user has no default portfolio yet, and the home page loads
    positions, targets and categories in parallel. Each request used to try to
    create "Principal" itself: one won, the others died on the
    UNIQUE(user_id, name) constraint with a 500. Needs a file-backed DB with a
    real connection pool — the shared in-memory fixture hides the race."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'race.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def session_override():
        async with maker() as session:
            yield session

    app.dependency_overrides[db_module.get_async_session] = session_override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            creds = {"email": "fresh@example.com", "password": "StrongPass!123"}
            await c.post("/api/auth/register", json=creds)
            r = await c.post(
                "/api/auth/jwt/login",
                data={"username": creds["email"], "password": creds["password"]},
            )
            auth = {"Authorization": f"Bearer {r.json()['access_token']}"}

            responses = await asyncio.gather(
                c.get("/api/positions", headers=auth),
                c.get("/api/targets", headers=auth),
                c.get("/api/categories", headers=auth),
                c.get("/api/targets", headers=auth),
                c.get("/api/categories", headers=auth),
            )

        assert [r.status_code for r in responses] == [200] * 5, [r.text for r in responses]
        async with maker() as session:
            defaults = (
                await session.execute(
                    select(func.count()).select_from(Portfolio).where(Portfolio.is_default)
                )
            ).scalar_one()
        assert defaults == 1
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
