"""Async SQLAlchemy engine and session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings

settings = get_settings()

# SQLite needs check_same_thread off for async. For hosted Postgres (Neon),
# asyncpg takes ssl via connect_args, not a URL param.
if settings.is_sqlite:
    _connect_args = {"check_same_thread": False}
else:
    _connect_args = {"ssl": True} if settings.require_ssl else {}

engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    future=True,
    connect_args=_connect_args,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a session, always closes it."""
    async with SessionLocal() as session:
        yield session