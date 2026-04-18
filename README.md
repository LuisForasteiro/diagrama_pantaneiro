# Diagrama Pantaneiro

Rastreador de carteira e assistente de rebalanceamento inspirado no "Diagrama do Cerrado" da AUVP. Define-se uma carteira-alvo (X% por classe) e o app sugere como alocar cada aporte para aproximar a posição atual do alvo, sem deixar nenhuma classe ultrapassá-lo.

O nome é uma referência ao original — mesma metodologia, outro bioma. Reimplementação, não fork.

## Funcionalidades

- **Múltiplas carteiras** por conta, com posições/alvos/histórico isolados (header `X-Portfolio-Id`).
- **Sete classes de ativos:** ações nacionais/internacionais, FIIs, REITs, cripto, renda fixa BR/internacional.
- **Pontuação por diagrama** (força = `2 × sim − N`) para ações/FIIs/REITs; força manual para cripto e RF.
- **Algoritmo de aporte em 3 estágios:** alocação entre classes → dentro da classe → quantização em unidades.
- **Dados de mercado:** Yahoo Finance (ações/REITs), Brapi (autocomplete BR), CoinGecko (cripto), Tesouro Direto (RF pública), AwesomeAPI (USD-BRL).
- **Extras:** autocomplete de tickers, histórico de aportes, presets de alvo, toggle de privacidade para screenshots.
- **Auth** via `fastapi-users` (JWT).

## Stack

**Backend:** Python 3.12, FastAPI, SQLAlchemy 2.x (async), SQLite + Alembic, Pydantic v2, httpx, yfinance.
**Frontend:** SvelteKit 5 (runes), TypeScript, Tailwind, Vite.
**Testes:** pytest (125+ testes) e Vitest.
**Deploy:** Docker Compose.

## Início rápido

```bash
git clone https://github.com/LucasGazula/diagrama_pantaneiro.git
cd diagrama_pantaneiro
cp .env.example .env
# edite .env e defina um JWT_SECRET forte (32+ bytes):
# python -c "import secrets; print(secrets.token_urlsafe(64))"

docker compose up --build
```

- Frontend: http://localhost:8080
- API docs: http://localhost:8000/docs

## Desenvolvimento local

```bash
# Backend (requer uv — https://github.com/astral-sh/uv)
cd backend && uv sync && uv run alembic upgrade head
JWT_SECRET=dev uv run uvicorn app.main:app --reload

# Frontend (Node 22+)
cd frontend && npm install && npm run dev

# Testes
cd backend && uv run pytest
cd frontend && npm test
```

## Variáveis de ambiente

| Variável       | Obrigatória | Descrição                                              |
| -------------- | ----------- | ------------------------------------------------------ |
| `JWT_SECRET`   | sim         | HMAC para assinar JWT (32+ bytes).                     |
| `DATABASE_URL` | não         | Default: SQLite no volume Docker.                      |
| `BRAPI_TOKEN`  | não         | Melhora cotação de ações BR se definido.               |
| `TIMEZONE`     | não         | Default: `America/Sao_Paulo`.                          |

## Algoritmo

`compute_suggestions()` roda em três estágios:

1. **Entre classes.** Calcula o gap de cada classe até o alvo e distribui o aporte proporcionalmente aos gaps, **limitado ao gap de cada uma**. Sobras (se todos os gaps já fecharam) vão para os pesos-alvo.
2. **Dentro da classe.** Divide entre ativos elegíveis ponderando por força → valor atual → partes iguais (nessa ordem de fallback).
3. **Quantização.** Converte em unidades inteiras, com frações para ações internacionais e REITs. Um absorvedor de resíduo aloca o arredondamento restante.

Elegibilidade: classes de diagrama exigem `strength > 0` (zero é julgamento neutro intencional); classes de força manual incluem `strength ≥ 0`; `strength < 0` é sempre excluído.

Detalhes em `backend/app/services/algorithm.py` e regressões em `backend/tests/services/test_algorithm_multi_class.py`.

## Escopo e limitações

Projeto pessoal, self-host, recortes conscientes:

- Auth básica — sem confirmação de email nem recuperação de senha.
- Sem rate limiting / audit log.
- Cotações de ações BR/FIIs via yfinance por padrão (Brapi só com token).
- Renda fixa privada é manual (sem fonte pública de preço).
- SQLite single-instance (migração para Postgres é direta pela stack async).

## Licença

MIT
