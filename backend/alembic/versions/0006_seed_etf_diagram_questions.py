"""seed default ETF diagram questions for existing users

Data-only migration: no schema changes. Inserts the 7 default questions of
`diagram_type='diagrama-etfs'` for every existing user, keyed by
`external_id='etf-01'..'etf-07'` so re-runs are no-ops.

Source list duplicated from app/services/default_diagram_questions.py
(migrations avoid importing app code so they survive future refactors).
The runtime hook in api/positions.py uses the same list to backfill any
user whose seed was missed.

Revision ID: a7f1c0d9b210
Revises: 9c3b5d72f104
Create Date: 2026-05-21 12:00:00.000000
"""
from __future__ import annotations

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7f1c0d9b210"
down_revision: Union[str, Sequence[str], None] = "9c3b5d72f104"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_ETF_QUESTIONS = (
    ("etf-01", "liquidez", "O ETF negocia mais de R$ 1M (ou US$ 1M) por dia em média?", 0),
    ("etf-02", "tamanho", "O patrimônio sob gestão (AUM) supera R$ 100M (ou US$ 100M)?", 1),
    ("etf-03", "custo", "A taxa de administração (TER) é inferior a 0,5% ao ano?", 2),
    ("etf-04", "replicacao", "A réplica é física (carrega os ativos), não sintética (via swaps)?", 3),
    ("etf-05", "rastreamento", "O tracking error em relação ao índice de referência fica abaixo de 0,5%?", 4),
    ("etf-06", "diversificacao", "O ETF tem ao menos 30 ativos diferentes na composição?", 5),
    ("etf-07", "gestora", "A gestora é uma das grandes/reconhecidas (BlackRock, Vanguard, Itaú, etc.)?", 6),
)


def upgrade() -> None:
    conn = op.get_bind()
    user_ids = [
        str(row[0]) for row in conn.execute(sa.text("SELECT id FROM users")).fetchall()
    ]
    if not user_ids:
        return

    check_sql = sa.text(
        "SELECT 1 FROM diagram_questions "
        "WHERE user_id = :uid AND diagram_type = 'diagrama-etfs' AND external_id = :ext"
    )
    insert_sql = sa.text(
        "INSERT INTO diagram_questions "
        "(id, user_id, diagram_type, criterias, question_text, display_order, external_id) "
        "VALUES (:id, :uid, 'diagrama-etfs', :crit, :text, :ord, :ext)"
    )

    for uid in user_ids:
        for ext, crit, text, ord_ in _ETF_QUESTIONS:
            already = conn.execute(check_sql, {"uid": uid, "ext": ext}).first()
            if already is not None:
                continue
            conn.execute(
                insert_sql,
                {
                    "id": str(uuid.uuid4()),
                    "uid": uid,
                    "crit": crit,
                    "text": text,
                    "ord": ord_,
                    "ext": ext,
                },
            )


def downgrade() -> None:
    op.execute(
        "DELETE FROM diagram_questions "
        "WHERE diagram_type = 'diagrama-etfs' "
        "AND external_id IN ('etf-01','etf-02','etf-03','etf-04','etf-05','etf-06','etf-07')"
    )
