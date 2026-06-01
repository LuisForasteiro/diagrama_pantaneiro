"""add categories table + positions.category_id (hierarchical metas)

Revision ID: f5b1d2630491
Revises: e4a0c2d51389
Create Date: 2026-06-01 10:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from fastapi_users_db_sqlalchemy.generics import GUID


revision: str = "f5b1d2630491"
down_revision: Union[str, Sequence[str], None] = "e4a0c2d51389"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("portfolio_id", GUID(), nullable=False),
        sa.Column("parent_id", GUID(), nullable=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("weight_pct", sa.Float(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_categories_user_id", "categories", ["user_id"])
    op.create_index("ix_categories_portfolio_id", "categories", ["portfolio_id"])
    op.create_index("ix_categories_parent_id", "categories", ["parent_id"])

    with op.batch_alter_table("positions") as batch:
        batch.add_column(sa.Column("category_id", GUID(), nullable=True))
        batch.create_foreign_key(
            "fk_positions_category_id",
            "categories",
            ["category_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index("ix_positions_category_id", "positions", ["category_id"])


def downgrade() -> None:
    op.drop_index("ix_positions_category_id", table_name="positions")
    with op.batch_alter_table("positions") as batch:
        batch.drop_constraint("fk_positions_category_id", type_="foreignkey")
        batch.drop_column("category_id")
    op.drop_index("ix_categories_parent_id", table_name="categories")
    op.drop_index("ix_categories_portfolio_id", table_name="categories")
    op.drop_index("ix_categories_user_id", table_name="categories")
    op.drop_table("categories")
