"""Application factory and resource lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router
from app.core.config import Settings
from app.db.session import build_engine, session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = build_engine(config) if config.database_url else None
        app.state.engine = engine
        app.state.session_factory = session_factory(engine) if engine else None
        try:
            yield
        finally:
            if engine is not None:
                engine.dispose()

    app = FastAPI(title="EcoLogística Lima API", version="0.1.0", lifespan=lifespan)
    app.include_router(router)
    return app
