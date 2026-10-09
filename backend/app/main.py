"""Application factory and resource lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.conductores import router as conductor_router
from app.api.driver_reports import router as driver_report_router
from app.api.health import router as health_router
from app.api.metrics import router as metrics_router
from app.api.pedidos import router as order_router
from app.api.preferencias import router as preferencias_router
from app.api.vehiculos import router as vehicle_router
from app.core.config import Settings
from app.db.session import build_audit_engine, build_engine, session_factory
from app.monitoring.database import instrument_engine
from app.monitoring.http import MetricsMiddleware
from app.monitoring.metrics import Metrics
from app.monitoring.probe import build_probe_engine
from app.services.auditoria import AuditoriaService
from app.services.autenticacion import AutenticacionService
from app.services.autorizacion import AutorizacionService


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()

    metrics = Metrics()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = None
        audit_engine = None
        probe_engine = None
        try:
            engine = build_engine(config) if config.database_url else None
            audit_engine = build_audit_engine(config) if config.database_url else None
            probe_engine = build_probe_engine(config)
            app.state.probe_engine = probe_engine
            for db_engine, name in ((engine, "business"), (audit_engine, "audit")):
                if db_engine is not None:
                    instrument_engine(db_engine, metrics, name)
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
            if probe_engine is not None:
                probe_engine.dispose()
            if audit_engine is not None:
                audit_engine.dispose()
            if engine is not None:
                engine.dispose()

    app = FastAPI(title="EcoLogística Lima API", version="0.1.0", lifespan=lifespan)
    app.state.metrics = metrics
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type"],
    )
    app.add_middleware(MetricsMiddleware, metrics=metrics)
    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(auth_router)
    app.include_router(driver_report_router)
    app.include_router(order_router)
    app.include_router(vehicle_router)
    app.include_router(conductor_router)
    app.include_router(preferencias_router)
    return app
