"""expand imobiliarios + etf diagram question banks

Data-only migration: no schema changes. For every existing user it
  * inserts the 6 new `investimentos-imobiliarios` questions (imob-07..imob-12)
    so the bank covers FIIs de tijolo/papel, FiAgros, Fi-Infras and REITs;
  * inserts the 4 new `diagrama-etfs` questions (etf-08..etf-11);
  * rewrites the text of the two original imobiliarios questions
    (external_id 67bd3bce...c03e / ...c03f) so they also make sense for credit
    funds (papel/FiAgro/Fi-Infra) — same external_id, so no dedup/responses break.

Keyed by `external_id` so re-runs are no-ops. Source lists duplicated from
app/services/default_diagram_questions.py (migrations avoid importing app code).
The runtime hook in api/positions.py uses the same defaults to backfill any
user whose seed was missed.

Revision ID: b8c2e1f4a730
Revises: f5b1d2630491
Create Date: 2026-06-26 18:30:00.000000
"""
from __future__ import annotations

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c2e1f4a730"
down_revision: Union[str, Sequence[str], None] = "f5b1d2630491"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (external_id, diagram_type, criterias, question_text, display_order)
_NEW_QUESTIONS = (
    (
        "imob-07",
        "investimentos-imobiliarios",
        "LIQUIDEZ",
        "O fundo tem boa liquidez? (volume financeiro médio diário relevante "
        "e uma base ampla de cotistas)",
        6,
    ),
    (
        "imob-08",
        "investimentos-imobiliarios",
        "PATRIMÔNIO",
        "O patrimônio líquido do fundo supera ~R$ 500 milhões? (escala que "
        "dilui custos e reduz risco de fechamento/baixa liquidez)",
        7,
    ),
    (
        "imob-09",
        "investimentos-imobiliarios",
        "GESTÃO",
        "A gestora é experiente e reconhecida, com bom histórico e relatórios "
        "transparentes (boa governança)?",
        8,
    ),
    (
        "imob-10",
        "investimentos-imobiliarios",
        "VACÂNCIA/INADIMPLÊNCIA",
        "A vacância (nos fundos de tijolo) ou a inadimplência da carteira de "
        "crédito (papel, FiAgro e Fi-Infra) está baixa e sob controle?",
        9,
    ),
    (
        "imob-11",
        "investimentos-imobiliarios",
        "QUALIDADE DA CARTEIRA",
        "Os ativos têm boa qualidade? (inquilinos sólidos e contratos longos "
        "no tijolo; bons ratings, garantias reais e baixo LTV nos "
        "CRIs/CRAs/debêntures)",
        10,
    ),
    (
        "imob-12",
        "investimentos-imobiliarios",
        "ALAVANCAGEM",
        "O endividamento/alavancagem do fundo está sob controle, sem "
        "comprometer as distribuições futuras?",
        11,
    ),
    (
        "etf-08",
        "diagrama-etfs",
        "histórico",
        "O ETF tem track record relevante (mais de ~5 anos de existência)?",
        7,
    ),
    (
        "etf-09",
        "diagrama-etfs",
        "índice",
        "O índice de referência é consolidado e de um provedor reconhecido "
        "(S&P, MSCI, FTSE, Bloomberg, etc.)?",
        8,
    ),
    (
        "etf-10",
        "diagrama-etfs",
        "spread",
        "O ETF negocia com spread estreito e próximo ao valor patrimonial "
        "(iNAV), sem prêmio/deságio relevante?",
        9,
    ),
    (
        "etf-11",
        "diagrama-etfs",
        "tributação",
        "A estrutura é eficiente em tributação para o investidor? (ex.: ETF "
        "nacional, ou internacional domiciliado na Irlanda em vez dos EUA)",
        10,
    ),
)

# (external_id, new question_text) — rewrite of the two original imob questions.
_REWORDED = (
    (
        "67bd3bceee6fea8789b7c03e",
        "Os ativos do fundo estão bem posicionados? (imóveis em boas "
        "localizações/regiões nobres nos fundos de tijolo; ou exposição a "
        "bons setores e devedores no papel, FiAgro e Fi-Infra)",
    ),
    (
        "67bd3bceee6fea8789b7c03f",
        "Os ativos exigem pouca manutenção / têm baixo risco operacional? "
        "(imóveis novos e padronizados no tijolo; carteira de crédito "
        "pulverizada e bem garantida no papel, FiAgro e Fi-Infra)",
    ),
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
        "WHERE user_id = :uid AND diagram_type = :dt AND external_id = :ext"
    )
    insert_sql = sa.text(
        "INSERT INTO diagram_questions "
        "(id, user_id, diagram_type, criterias, question_text, display_order, external_id) "
        "VALUES (:id, :uid, :dt, :crit, :text, :ord, :ext)"
    )
    update_sql = sa.text(
        "UPDATE diagram_questions SET question_text = :text "
        "WHERE user_id = :uid AND external_id = :ext"
    )

    for uid in user_ids:
        for ext, dt, crit, text, ord_ in _NEW_QUESTIONS:
            already = conn.execute(
                check_sql, {"uid": uid, "dt": dt, "ext": ext}
            ).first()
            if already is not None:
                continue
            conn.execute(
                insert_sql,
                {
                    "id": uuid.uuid4().hex,
                    "uid": uid,
                    "dt": dt,
                    "crit": crit,
                    "text": text,
                    "ord": ord_,
                    "ext": ext,
                },
            )
        for ext, text in _REWORDED:
            conn.execute(update_sql, {"uid": uid, "ext": ext, "text": text})


def downgrade() -> None:
    op.execute(
        "DELETE FROM diagram_questions WHERE external_id IN ("
        "'imob-07','imob-08','imob-09','imob-10','imob-11','imob-12',"
        "'etf-08','etf-09','etf-10','etf-11')"
    )
