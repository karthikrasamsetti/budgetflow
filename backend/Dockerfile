FROM python:3.12-slim

# uv for fast, reproducible installs (matches local workflow).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install deps first for layer caching.
COPY pyproject.toml ./
RUN uv pip install --system --no-cache .

COPY . .

ENV PYTHONPATH=/app/src
EXPOSE 8000

# Render/Compose sets PORT; default to 8000 locally.
# Run migrations first, then start the server. sh -c interprets the && correctly.
CMD ["sh", "-c", "alembic upgrade head && uvicorn budgetflow.main:app --host 0.0.0.0 --port ${PORT:-8000}"]