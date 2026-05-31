"""add effective_class to positions (semantic override)

Schema-only migration: adds a nullable VARCHAR(48) column. NULL means
"no override — algorithm and UI use asset_type as before". When set, the
portfolio_loader emits Asset.type = effective_class, so the algorithm,
metas, donut, and region breakdown all treat the position as the new
class. Price routing (market_data/registry.py) keeps using asset_type.

Revision ID: c2e8a3b41056
Revises: a7f1c0d9b210
Create Date: 2026-05-21 14:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2e8a3b41056"
down_revision: Union[str, Sequence[str], None] = "a7f1c0d9b210"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("positions") as batch:
        batch.add_column(
            sa.Column("effective_class", sa.String(length=48), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("positions") as batch:
        batch.drop_column("effective_class")
