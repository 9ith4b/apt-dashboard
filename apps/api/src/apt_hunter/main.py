from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apt_hunter.api.router import api_router
from apt_hunter.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key"],
    )
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
