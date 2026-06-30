"""Source-of-truth list of default diagram questions for all three banks.

Historically only the ETF bank lived here; the cerrado (ações) and
imobiliários (FIIs/REITs) banks were seeded exclusively from the AUVP
fixture (tests/fixtures/auth_me.json) on first login. That fixture is NOT
shipped in the prod Docker image, so self-host users ended up with the ETF
bank only and an empty ações/imobiliários checklist. Promoting all three
banks to real defaults removes that test-fixture dependency.

The ETF list is also duplicated in
alembic/versions/0006_seed_etf_diagram_questions.py (migrations should not
import app code so they survive future refactors). If you change either,
update both.

Stable `external_id`s are the dedup key — re-runs of the seed (migration or
runtime hook) skip questions that already exist for the user, and the AUVP
fixture import dedups against them too. The cerrado/imobiliários ids reuse
the original AUVP `_id`s so a user who DID import the fixture sees no
duplicates. Users can freely edit `question_text`/`criterias` via the
`/api/diagram-questions` endpoints without losing the dedup guarantee.
"""

from __future__ import annotations

ETF_DIAGRAM_TYPE = "diagrama-etfs"
CERRADO_DIAGRAM_TYPE = "diagrama-do-cerrado"
IMOB_DIAGRAM_TYPE = "investimentos-imobiliarios"

QuestionDict = dict[str, str | int]

# ── ações nacionais + internacionais (Diagrama do Cerrado) ──
CERRADO_QUESTIONS: tuple[QuestionDict, ...] = (
    {
        "external_id": "67b7f52d3b601fcda83a6f50",
        "criterias": "ROE",
        "question_text": "ROE historicamente maior que 5%? (Considere anos anteriores).",
        "display_order": 0,
    },
    {
        "external_id": "67b7f52d3b601fcda83a6f51",
        "criterias": "CAGR",
        "question_text": (
            "Tem um crescimento de receitas (ou lucro) superior a 5% nos últimos 5 anos?"
        ),
        "display_order": 1,
    },
    {
        "external_id": "67b7f52d3b601fcda83a6f52",
        "criterias": "DIVIDENDOS",
        "question_text": "A empresa tem um histórico de pagamento de dividendos?",
        "display_order": 2,
    },
    {
        "external_id": "67b7f52d3b601fcda83a6f53",
        "criterias": "TECNOLOGIA E PESQUISA",
        "question_text": (
            "A empresa investe amplamente em pesquisa e inovação? "
            "Setor obsoleto = SEMPRE NÃO"
        ),
        "display_order": 3,
    },
    {
        "external_id": "67b7f52d3b601fcda83a6f54",
        "criterias": "TEMPO DE MERCADO",
        "question_text": "Tem mais de 30 anos de mercado? (Fundação)",
        "display_order": 4,
    },
    {
        "external_id": "67b7f52d3b601fcda83a6f55",
        "criterias": "VANTAGENS COMPETITIVAS",
        "question_text": (
            "É líder nacional ou mundial no setor em que atua? "
            "(Só considera se for LÍDER, primeira colocada)"
        ),
        "display_order": 5,
    },
    {
        "external_id": "67b7f52d3b601fcda83a6f56",
        "criterias": "PERENIDADE",
        "question_text": "O setor em que a empresa atua tem mais de 100 anos?",
        "display_order": 6,
    },
    {
        "external_id": "67b7f52d3b601fcda83a6f57",
        "criterias": "TAMANHO",
        "question_text": "A empresa é uma BLUE CHIP?",
        "display_order": 7,
    },
    {
        "external_id": "67b7f52d3b601fcda83a6f58",
        "criterias": "GOVERNANÇA",
        "question_text": "A empresa tem uma boa gestão? Histórico de corrupção = SEMPRE NÃO",
        "display_order": 8,
    },
    {
        "external_id": "67b7f52d3b601fcda83a6f59",
        "criterias": "INDEPENDÊNCIA",
        "question_text": "É livre de controle ESTATAL ou concentração em cliente único?",
        "display_order": 9,
    },
    {
        "external_id": "67b7f52d3b601fcda83a6f5a",
        "criterias": "POUCO ENDIVIDADA",
        "question_text": "Dív. Líquida/EBITDA é menor que 2 nos últimos 5 anos?",
        "display_order": 10,
    },
)

# ── FIIs + FiAgros + Fi-Infras + REITs (Investimentos Imobiliários) ──
# Banco fundamentalista único compartilhado pela classe `fundos_imobiliarios`
# (que engloba FII de tijolo/papel/FOF, FiAgro e Fi-Infra) e `reits`. As duas
# primeiras perguntas (originais do diagrama AUVP) foram reescritas para fazerem
# sentido também em fundos de crédito (papel/FiAgro/Fi-Infra), sem trocar o
# `external_id` — assim a dedup e as respostas já gravadas continuam válidas.
IMOB_QUESTIONS: tuple[QuestionDict, ...] = (
    {
        "external_id": "67bd3bceee6fea8789b7c03e",
        "criterias": "LOCALIZAÇÃO",
        "question_text": (
            "Os ativos do fundo estão bem posicionados? (imóveis em boas "
            "localizações/regiões nobres nos fundos de tijolo; ou exposição a "
            "bons setores e devedores no papel, FiAgro e Fi-Infra)"
        ),
        "display_order": 0,
    },
    {
        "external_id": "67bd3bceee6fea8789b7c03f",
        "criterias": "MANUTENÇÃO",
        "question_text": (
            "Os ativos exigem pouca manutenção / têm baixo risco operacional? "
            "(imóveis novos e padronizados no tijolo; carteira de crédito "
            "pulverizada e bem garantida no papel, FiAgro e Fi-Infra)"
        ),
        "display_order": 1,
    },
    {
        "external_id": "67bd3bceee6fea8789b7c040",
        "criterias": "P/VP",
        "question_text": (
            "O fundo está negociado abaixo do P/VP 1? "
            "(Acima de 1,5 eu descarto o investimento em qualquer hipótese)"
        ),
        "display_order": 2,
    },
    {
        "external_id": "67bd3bceee6fea8789b7c041",
        "criterias": "DIVIDENDOS",
        "question_text": "Distribui dividendos há mais de 4 anos consistentemente?",
        "display_order": 3,
    },
    {
        "external_id": "67bd3bceee6fea8789b7c042",
        "criterias": "DIVERSIFICAÇÃO",
        "question_text": (
            "Não é dependente de um único inquilino, imóvel ou devedor/emissor?"
        ),
        "display_order": 4,
    },
    {
        "external_id": "67bd3bceee6fea8789b7c043",
        "criterias": "YIELD",
        "question_text": (
            "O Yield está dentro ou acima da média para fundos do mesmo tipo?"
        ),
        "display_order": 5,
    },
    {
        "external_id": "imob-07",
        "criterias": "LIQUIDEZ",
        "question_text": (
            "O fundo tem boa liquidez? (volume financeiro médio diário relevante "
            "e uma base ampla de cotistas)"
        ),
        "display_order": 6,
    },
    {
        "external_id": "imob-08",
        "criterias": "PATRIMÔNIO",
        "question_text": (
            "O patrimônio líquido do fundo supera ~R$ 500 milhões? (escala que "
            "dilui custos e reduz risco de fechamento/baixa liquidez)"
        ),
        "display_order": 7,
    },
    {
        "external_id": "imob-09",
        "criterias": "GESTÃO",
        "question_text": (
            "A gestora é experiente e reconhecida, com bom histórico e relatórios "
            "transparentes (boa governança)?"
        ),
        "display_order": 8,
    },
    {
        "external_id": "imob-10",
        "criterias": "VACÂNCIA/INADIMPLÊNCIA",
        "question_text": (
            "A vacância (nos fundos de tijolo) ou a inadimplência da carteira de "
            "crédito (papel, FiAgro e Fi-Infra) está baixa e sob controle?"
        ),
        "display_order": 9,
    },
    {
        "external_id": "imob-11",
        "criterias": "QUALIDADE DA CARTEIRA",
        "question_text": (
            "Os ativos têm boa qualidade? (inquilinos sólidos e contratos longos "
            "no tijolo; bons ratings, garantias reais e baixo LTV nos "
            "CRIs/CRAs/debêntures)"
        ),
        "display_order": 10,
    },
    {
        "external_id": "imob-12",
        "criterias": "ALAVANCAGEM",
        "question_text": (
            "O endividamento/alavancagem do fundo está sob controle, sem "
            "comprometer as distribuições futuras?"
        ),
        "display_order": 11,
    },
)

# ── ETFs nacionais + internacionais (Diagrama ETFs) ──
ETF_QUESTIONS: tuple[QuestionDict, ...] = (
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
    {
        "external_id": "etf-08",
        "criterias": "histórico",
        "question_text": "O ETF tem track record relevante (mais de ~5 anos de existência)?",
        "display_order": 7,
    },
    {
        "external_id": "etf-09",
        "criterias": "índice",
        "question_text": (
            "O índice de referência é consolidado e de um provedor reconhecido "
            "(S&P, MSCI, FTSE, Bloomberg, etc.)?"
        ),
        "display_order": 8,
    },
    {
        "external_id": "etf-10",
        "criterias": "spread",
        "question_text": (
            "O ETF negocia com spread estreito e próximo ao valor patrimonial "
            "(iNAV), sem prêmio/deságio relevante?"
        ),
        "display_order": 9,
    },
    {
        "external_id": "etf-11",
        "criterias": "tributação",
        "question_text": (
            "A estrutura é eficiente em tributação para o investidor? (ex.: ETF "
            "nacional, ou internacional domiciliado na Irlanda em vez dos EUA)"
        ),
        "display_order": 10,
    },
)

# (diagram_type, questions) pairs — iterated by the runtime backfill hook in
# api/positions.py so every user gets all three default banks regardless of
# whether the AUVP fixture was ever present.
DEFAULT_QUESTION_BANKS: tuple[tuple[str, tuple[QuestionDict, ...]], ...] = (
    (CERRADO_DIAGRAM_TYPE, CERRADO_QUESTIONS),
    (IMOB_DIAGRAM_TYPE, IMOB_QUESTIONS),
    (ETF_DIAGRAM_TYPE, ETF_QUESTIONS),
)
