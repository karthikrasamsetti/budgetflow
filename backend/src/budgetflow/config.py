"""Application configuration, loaded from environment / .env (Pydantic settings)."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _strip_query_key(url: str, key: str) -> str:
    """Remove a single ?key=... / &key=... param from a URL, tidily."""
    import re

    url = re.sub(rf"([?&]){key}=[^&]*&", r"\1", url)  # key in the middle
    url = re.sub(rf"[?&]{key}=[^&]*$", "", url)  # key at the end
    return url


class Settings(BaseSettings):
    """All runtime config. Every field is overridable via env var or .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Core ---
    app_name: str = "BudgetFlow"
    environment: str = "development"
    # SQLite default lets the app boot with zero external services for local dev.
    # In prod, set DATABASE_URL to a postgresql+asyncpg:// URL.
    database_url: str = "sqlite+aiosqlite:///./budgetflow.db"

    # --- Auth / JWT ---
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    # --- Rate limiting ---
    auth_rate_limit: str = "5/minute"  # per-IP, applied to sensitive auth routes

    # --- AI providers ---
    default_ai_provider: str = "groq"
    groq_api_key: str | None = Field(default=None)
    groq_model: str = "llama-3.1-8b-instant"
    gemini_api_key: str | None = Field(default=None)
    gemini_model: str = "gemini-1.5-flash"
    hf_api_key: str | None = Field(default=None)
    hf_model: str = "meta-llama/Meta-Llama-3-8B-Instruct"

    # --- CORS ---
    cors_origins: list[str] = ["http://localhost:5173"]

    @field_validator("database_url")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        # Render (and many hosts) provide 'postgres://' or 'postgresql://' URLs.
        # The app runs async SQLAlchemy, which needs the asyncpg driver form.
        # Alembic re-derives its own sync URL from this in migrations/env.py.
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://") :]
        if v.startswith("postgresql://"):
            v = "postgresql+asyncpg://" + v[len("postgresql://") :]
        return v

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def async_database_url(self) -> str:
        """URL for the async app engine (asyncpg).

        asyncpg does not accept libpq's '?sslmode=...' query param; it uses a
        'ssl' connect arg instead (see db.py). Strip sslmode here so the URL
        parses, and db.py enables SSL via connect_args when it was requested.
        """
        url = self.database_url
        if "sslmode=" in url and "+asyncpg" in url:
            url = _strip_query_key(url, "sslmode")
        return url

    @property
    def require_ssl(self) -> bool:
        """True when the original URL asked for SSL (Neon and most hosted PG)."""
        return "sslmode=require" in self.database_url

    @property
    def sync_database_url(self) -> str:
        """URL for Alembic's sync engine (psycopg2), which DOES use sslmode."""
        return self.database_url.replace("+asyncpg", "+psycopg2").replace("+aiosqlite", "")


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
