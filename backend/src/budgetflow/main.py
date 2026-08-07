"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .api import ai as ai_routes
from .api import auth as auth_routes
from .config import get_settings
from .db import Base, SessionLocal, engine
from .security.rate_limit import limiter
from .seed import seed_system_categories

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: create tables + seed on SQLite so the app runs with no
    # external services. In production, Alembic owns the schema (see migrations/).
    if settings.is_sqlite:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        await seed_system_categories(db)
    yield


def create_app(*, use_lifespan: bool = True) -> FastAPI:
    # Tests manage their own schema/seeding and pass use_lifespan=False.
    app = FastAPI(title=settings.app_name, lifespan=lifespan if use_lifespan else None)

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_routes.router)
    app.include_router(ai_routes.router)

    @app.get("/health", tags=["meta"])
    async def health():
        return {"status": "ok", "app": settings.app_name, "env": settings.environment}

    return app


app = create_app()
