"""FastAPI entrypoint."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_config
from .routes import providers as providers_routes
from .routes import settings as settings_routes
from .routes import vqe as vqe_routes
from .telemetry import configure_telemetry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def create_app() -> FastAPI:
    cfg = get_config()
    configure_telemetry()

    app = FastAPI(title="VQE Telemetry API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[cfg.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(settings_routes.router)
    app.include_router(providers_routes.router)
    app.include_router(vqe_routes.router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
