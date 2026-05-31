"""Source-of-truth list of default ETF diagram questions.

The same list is duplicated in alembic/versions/0006_seed_etf_diagram_questions.py
(migrations should not import app code so they survive future refactors).
If you change either, update both.

Stable `external_id`s (etf-01..etf-07) are the dedup key — re-runs of the
seed (migration or runtime hook) skip questions that already exist for the
user. Users can freely edit `question_text` or `criterias` via the
`/api/diagram-questions` endpoints without losing the dedup guarantee.
"""

from __future__ import annotations

ETF_DIAGRAM_TYPE = "diagrama-etfs"

ETF_QUESTIONS: tuple[dict[str, str | int], ...] = (
    {
        "external_id": "etf-01",
        "criterias": "liquidez",
        "question_text": "O ETF negocia mais de R$ 1M (ou US$ 1M) por dia em média?",
        "display_order": 0,
    },
    {
        "external_id": "etf-02",
        "criterias": "tamanho",
        "question_text": "O patrimônio sob gestão (AUM) supera R$ 100M (ou US$ 100M)?",
        "display_order": 1,
    },
    {
        "external_id": "etf-03",
        "criterias": "custo",
        "question_text": "A taxa de administração (TER) é inferior a 0,5% ao ano?",
        "display_order": 2,
    },
    {
        "external_id": "etf-04",
        "criterias": "replicacao",
        "question_text": "A réplica é física (carrega os ativos), não sintética (via swaps)?",
        "display_order": 3,
    },
    {
        "external_id": "etf-05",
        "criterias": "rastreamento",
        "question_text": "O tracking error em relação ao índice de referência fica abaixo de 0,5%?",
        "display_order": 4,
    },
    {
        "external_id": "etf-06",
        "criterias": "diversificacao",
        "question_text": "O ETF tem ao menos 30 ativos diferentes na composição?",
        "display_order": 5,
    },
    {
        "external_id": "etf-07",
        "criterias": "gestora",
        "question_text": "A gestora é uma das grandes/reconhecidas (BlackRock, Vanguard, Itaú, etc.)?",
        "display_order": 6,
    },
)
