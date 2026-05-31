"""add ticker_catalog table (local autocomplete cache)

Revision ID: d3f9b1c40278
Revises: c2e8a3b41056
Create Date: 2026-05-31 12:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from fastapi_users_db_sqlalchemy.generics import GUID


revision: str = "d3f9b1c40278"
down_revision: Union[str, Sequence[str], None] = "c2e8a3b41056"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ticker_catalog",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("symbol", sa.String(length=48), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "symbol", name="uq_ticker_source_symbol"),
    )
    op.create_index("ix_ticker_catalog_symbol", "ticker_catalog", ["symbol"])
    op.create_index("ix_ticker_catalog_source", "ticker_catalog", ["source"])


def downgrade() -> None:
    op.drop_index("ix_ticker_catalog_source", table_name="ticker_catalog")
    op.drop_index("ix_ticker_catalog_symbol", table_name="ticker_catalog")
    op.drop_table("ticker_catalog")
