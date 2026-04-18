import os

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from sqlalchemy.ext.asyncio import create_async_engine

from app.core.db import Base
from app.models.user import User


async def test_user_table_has_expected_columns() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    assert User.__tablename__ == "users"
    cols = {c.name for c in User.__table__.columns}
    assert {"id", "email", "hashed_password", "is_active", "is_superuser", "is_verified"} <= cols
