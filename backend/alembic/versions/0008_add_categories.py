"""add categories (2-level macro grouping) + positions.category_id

Creates the user-defined category tree (per portfolio, 2 levels) and a
nullable FK from positions. ON DELETE SET NULL keeps positions when a
category is removed (they become "sem categoria").

Revision ID: f4b1c8e36d92
Revises: c2e8a3b41056
Create Date: 2026-05-29 17:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import fastapi_users_db_sqlalchemy


revision: str = "f4b1c8e36d92"
down_revision: Union[str, Sequence[str], None] = "c2e8a3b41056"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GUID = fastapi_users_db_sqlalchemy.generics.GUID


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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_categories_user_id"), "categories", ["user_id"])
    op.create_index(op.f("ix_categories_portfolio_id"), "categories", ["portfolio_id"])
    op.create_index(op.f("ix_categories_parent_id"), "categories", ["parent_id"])

    with op.batch_alter_table("positions") as batch:
        batch.add_column(
            sa.Column(
                "category_id",
                GUID(),
                sa.ForeignKey(
                    "categories.id",
                    ondelete="SET NULL",
                    name="fk_positions_category_id",
                ),
                nullable=True,
            )
        )
    op.create_index(
        op.f("ix_positions_category_id"), "positions", ["category_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_positions_category_id"), table_name="positions")
    with op.batch_alter_table("positions") as batch:
        batch.drop_column("category_id")
    op.drop_index(op.f("ix_categories_parent_id"), table_name="categories")
    op.drop_index(op.f("ix_categories_portfolio_id"), table_name="categories")
    op.drop_index(op.f("ix_categories_user_id"), table_name="categories")
    op.drop_table("categories")
