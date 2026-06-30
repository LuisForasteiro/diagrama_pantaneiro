"""add tradable flag to positions (still-buyable / receives aportes)

Schema-only migration: adds a NOT NULL BOOLEAN column defaulting to true.
``tradable = false`` means the position is no longer buyable (e.g. a Tesouro
title the Treasury pulled from sale, or a ticker the user no longer adds to):
the rebalancing algorithm stops suggesting it, but it still counts in the
portfolio total (the user still owns it). Server default 1 so every existing
position stays buyable after the upgrade.

Revision ID: 9c4d7e2a1b30
Revises: b8c2e1f4a730
Create Date: 2026-06-29 11:10:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9c4d7e2a1b30"
down_revision: Union[str, Sequence[str], None] = "b8c2e1f4a730"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("positions") as batch:
        batch.add_column(
            sa.Column(
                "tradable",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("positions") as batch:
        batch.drop_column("tradable")
