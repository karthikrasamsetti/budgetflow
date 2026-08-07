"""Shared test fixtures: isolated in-memory DB + HTTP client."""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from budgetflow.db import Base, get_db
from budgetflow.main import create_app
from budgetflow.seed import seed_system_categories


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def client(engine, session_factory):
    # Seed system categories once for the test DB.
    async with session_factory() as s:
        await seed_system_categories(s)

    app = create_app(use_lifespan=False)

    # Disable per-IP rate limiting in tests: every request originates from the
    # same 127.0.0.1, so limits would bleed across test functions otherwise.
    from budgetflow.security.rate_limit import limiter

    limiter.enabled = False

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
