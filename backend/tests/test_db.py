import os

import pytest

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.core.db import Base, get_async_session_maker


async def test_session_maker_yields_working_session() -> None:
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        # Simple round-trip to verify the session is alive
        from sqlalchemy import text

        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_base_is_declarative_base() -> None:
    assert hasattr(Base, "metadata")
    assert hasattr(Base, "registry")
