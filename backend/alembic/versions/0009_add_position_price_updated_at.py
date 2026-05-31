"""add price_updated_at to positions (staleness display)

Revision ID: e4a0c2d51389
Revises: d3f9b1c40278
Create Date: 2026-05-31 12:30:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4a0c2d51389"
down_revision: Union[str, Sequence[str], None] = "d3f9b1c40278"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("positions") as batch:
        batch.add_column(
            sa.Column("price_updated_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("positions") as batch:
        batch.drop_column("price_updated_at")
