# BudgetFlow — Backend

FastAPI + SQLAlchemy (async) + Postgres backend for BudgetFlow. This is **Phase 0** of the [implementation plan](../IMPLEMENTATION_PLAN.md): foundation only — auth, config, full schema, the AI provider factory, and CI. Feature endpoints (transactions, budgets, chat) land in later phases.

## What's here

- **Auth** — register / login / refresh, bcrypt hashing, JWT access + refresh tokens, per-IP rate limiting, password reset.
- **Full DB schema** — all 11 tables from the plan (core + AI observability), with an Alembic baseline migration.
- **AI provider factory** — Groq / Gemini / HuggingFace behind one interface, switchable via `.env` or per-request; every call flows through a logging wrapper that writes one `ai_logs` row.
- **`GET /ai/providers`** — lists providers with configured/default flags (for the UI switcher).
- **`GET /health`** — liveness check.
- **Tooling** — ruff, pytest, pre-commit, Docker + compose, GitHub Actions CI.

## Quick start (local, SQLite — zero external services)

```bash
cd backend
uv venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
cp .env.example .env                # optional; SQLite defaults work as-is
uvicorn budgetflow.main:app --reload
```

Open http://localhost:8000/docs for the interactive API. On SQLite, tables are created and system categories seeded automatically on startup.

## Run with Postgres (production parity)

```bash
docker compose up --build           # from repo root
```

This starts Postgres, runs `alembic upgrade head`, then the API on :8000.

## Migrations (Alembic)

Alembic owns the schema in Postgres. After changing a model:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

The baseline (`migrations/versions/*_baseline_schema.py`) creates every table.

## AI providers

Set any of these in `.env` to enable a provider (free tiers first):

```
DEFAULT_AI_PROVIDER=groq
GROQ_API_KEY=...        GROQ_MODEL=llama-3.1-8b-instant
GEMINI_API_KEY=...      GEMINI_MODEL=gemini-1.5-flash
HF_API_KEY=...          HF_MODEL=meta-llama/Meta-Llama-3-8B-Instruct
```

`GET /ai/providers` reports which are configured. Unconfigured providers are listed but flagged `configured: false`.

## Tests, lint, format

```bash
pytest -q                 # 17 tests: auth flows + AI factory/logging
ruff check .              # lint
ruff format .             # format
pre-commit install        # run hooks on every commit
```

CI (`.github/workflows/ci.yml`) runs lint + format check + tests on every push and PR.

## Layout

```
src/budgetflow/
├── main.py          # app factory: CORS, rate limiter, routers, health, lifespan
├── config.py        # Pydantic settings (all config via .env)
├── db.py            # async engine / session / Base
├── models/          # SQLAlchemy models (core + ai)
├── schemas/         # Pydantic request/response
├── api/             # thin routers (auth, ai)
├── services/        # business logic (auth_service)
├── security/        # hashing, jwt, rate limit, deps
├── ai/              # factory, providers/, logging wrapper, base
└── seed.py          # system categories
```

## Notes

- **Money** is `Numeric(12,2)` everywhere — never float.
- **Soft delete** columns exist on business rows; queries filter them in later phases.
- `bcrypt` is pinned `<4.1` and `fastapi` `<0.116` for known-good compatibility.
