"""Importing this package registers every model on ``Base.metadata``.

Centralizing the imports means ``Base.metadata.create_all`` (tests) and Alembic
autogenerate always see the full schema, regardless of which module the caller
imported first.

``user`` is imported first on purpose: it pulls in ``fastapi_users.db``, which
must be fully initialized before ``fastapi_users_db_sqlalchemy.generics`` (used
by the other models) to avoid a partial-import error.
"""

from app.models.user import User
from app.models.aporte_allocation import AporteAllocation
from app.models.aporte_event import AporteEvent
from app.models.category import Category
from app.models.diagram_question import DiagramQuestion
from app.models.investment_target import InvestmentTarget
from app.models.portfolio import Portfolio
from app.models.position import Position
from app.models.target_preset import TargetPreset
from app.models.ticker_catalog import TickerCatalog

__all__ = [
    "AporteAllocation",
    "AporteEvent",
    "Category",
    "DiagramQuestion",
    "InvestmentTarget",
    "Portfolio",
    "Position",
    "TargetPreset",
    "TickerCatalog",
    "User",
]
