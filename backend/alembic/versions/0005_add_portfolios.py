"""add portfolios (multi-portfolio per user)

Creates the portfolios table, adds portfolio_id FKs to the three
portfolio-scoped tables (positions, investment_targets, aporte_events),
and backfills a "Principal" portfolio for every existing user so that
pre-existing data remains reachable through the new model.

Note: diagram_questions and target_presets intentionally remain user-scoped
(they are shared libraries across portfolios).

Revision ID: 9c3b5d72f104
Revises: 8f2c4a91e03d
Create Date: 2026-04-17 12:00:00.000000
"""
from __future__ import annotations

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import fastapi_users_db_sqlalchemy


revision: str = "9c3b5d72f104"
down_revision: Union[str, Sequence[str], None] = "8f2c4a91e03d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


GUID = fastapi_users_db_sqlalchemy.generics.GUID


def upgrade() -> None:
    # 1. portfolios table
    op.create_table(
        "portfolios",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_portfolio_user_name"),
    )
    op.create_index(
        op.f("ix_portfolios_user_id"), "portfolios", ["user_id"], unique=False
    )

    # 2. Add nullable portfolio_id column to each scoped table (SQLite needs batch
    # mode for constraint-bearing ALTERs).
    with op.batch_alter_table("positions") as batch:
        batch.add_column(
            sa.Column(
                "portfolio_id",
                sa.Uuid(),
                sa.ForeignKey(
                    "portfolios.id",
                    ondelete="CASCADE",
                    name="fk_positions_portfolio_id",
                ),
                nullable=True,
            )
        )
    op.create_index(
        op.f("ix_positions_portfolio_id"),
        "positions",
        ["portfolio_id"],
        unique=False,
    )

    with op.batch_alter_table("investment_targets") as batch:
        batch.add_column(
            sa.Column(
                "portfolio_id",
                sa.Uuid(),
                sa.ForeignKey(
                    "portfolios.id",
                    ondelete="CASCADE",
                    name="fk_investment_targets_portfolio_id",
                ),
                nullable=True,
            )
        )
    op.create_index(
        op.f("ix_investment_targets_portfolio_id"),
        "investment_targets",
        ["portfolio_id"],
        unique=False,
    )

    with op.batch_alter_table("aporte_events") as batch:
        batch.add_column(
            sa.Column(
                "portfolio_id",
                sa.Uuid(),
                sa.ForeignKey(
                    "portfolios.id",
                    ondelete="CASCADE",
                    name="fk_aporte_events_portfolio_id",
                ),
                nullable=True,
            )
        )
    op.create_index(
        op.f("ix_aporte_events_portfolio_id"),
        "aporte_events",
        ["portfolio_id"],
        unique=False,
    )

    # 3. Backfill: one "Principal" portfolio per existing user, then repoint rows.
    conn = op.get_bind()
    user_ids: set[str] = set()
    for table in ("positions", "investment_targets", "aporte_events"):
        rows = conn.execute(
            sa.text(f"SELECT DISTINCT user_id FROM {table} WHERE user_id IS NOT NULL")
        ).fetchall()
        user_ids.update(str(r[0]) for r in rows)
    # Also include users with no data yet, so a second portfolio can be created
    # via /api/portfolios later without another migration.
    for row in conn.execute(sa.text("SELECT id FROM users")).fetchall():
        user_ids.add(str(row[0]))

    insert_portfolio = sa.text(
        "INSERT INTO portfolios (id, user_id, name, is_default, created_at) "
        "VALUES (:id, :uid, 'Principal', 1, CURRENT_TIMESTAMP)"
    )
    update_sql = {
        t: sa.text(f"UPDATE {t} SET portfolio_id = :pid WHERE user_id = :uid")
        for t in ("positions", "investment_targets", "aporte_events")
    }

    for uid in user_ids:
        pid = str(uuid.uuid4())
        conn.execute(insert_portfolio, {"id": pid, "uid": uid})
        for stmt in update_sql.values():
            conn.execute(stmt, {"pid": pid, "uid": uid})

    # 4. Flip portfolio_id to NOT NULL + swap InvestmentTarget uniqueness.
    with op.batch_alter_table("positions") as batch:
        batch.alter_column("portfolio_id", existing_type=sa.Uuid(), nullable=False)

    with op.batch_alter_table("investment_targets") as batch:
        batch.drop_constraint("uq_target_user_type", type_="unique")
        batch.alter_column("portfolio_id", existing_type=sa.Uuid(), nullable=False)
        batch.create_unique_constraint(
            "uq_target_portfolio_type", ["portfolio_id", "asset_type"]
        )

    with op.batch_alter_table("aporte_events") as batch:
        batch.alter_column("portfolio_id", existing_type=sa.Uuid(), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("aporte_events") as batch:
        batch.drop_column("portfolio_id")
    op.drop_index(
        op.f("ix_aporte_events_portfolio_id"), table_name="aporte_events"
    )

    with op.batch_alter_table("investment_targets") as batch:
        batch.drop_constraint("uq_target_portfolio_type", type_="unique")
        batch.drop_column("portfolio_id")
        batch.create_unique_constraint(
            "uq_target_user_type", ["user_id", "asset_type"]
        )
    op.drop_index(
        op.f("ix_investment_targets_portfolio_id"),
        table_name="investment_targets",
    )

    with op.batch_alter_table("positions") as batch:
        batch.drop_column("portfolio_id")
    op.drop_index(op.f("ix_positions_portfolio_id"), table_name="positions")

    op.drop_index(op.f("ix_portfolios_user_id"), table_name="portfolios")
    op.drop_table("portfolios")
