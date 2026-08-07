"""Application configuration, loaded from environment / .env (Pydantic settings)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
