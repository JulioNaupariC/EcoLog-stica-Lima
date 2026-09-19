"""Application factory and resource lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.core.config import Settings
from app.db.session import build_audit_engine, build_engine, session_factory
from app.services.auditoria import AuditoriaService
from app.services.autenticacion import AutenticacionService
from app.services.autorizacion import AutorizacionService


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = None
        audit_engine = None
        try:
            engine = build_engine(config) if config.database_url else None
            audit_engine = build_audit_engine(config) if config.database_url else None
            business_factory = session_factory(engine) if engine else None
            audit_factory = session_factory(audit_engine) if audit_engine else None
            app.state.engine = engine
            app.state.audit_engine = audit_engine
            app.state.session_factory = business_factory
            app.state.audit_session_factory = audit_factory
            app.state.settings = config
            audit_service = AuditoriaService(audit_factory) if audit_factory else None
            app.state.authentication_service = (
                AutenticacionService(
                    business_factory,
                    audit_service,
                    ttl_minutes=config.session_ttl_minutes,
                )
                if business_factory and audit_service
                else None
            )
            app.state.authorization_service = (
                AutorizacionService(audit_service) if audit_service else None
            )
            yield
        finally:
            if audit_engine is not None:
                audit_engine.dispose()
            if engine is not None:
                engine.dispose()

    app = FastAPI(title="EcoLogística Lima API", version="0.1.0", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(auth_router)
    return app
