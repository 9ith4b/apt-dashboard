from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apt_hunter import __version__
from apt_hunter.api.router import api_router
from apt_hunter.config import get_settings
from apt_hunter.metrics import MetricsMiddleware
from apt_hunter.metrics import router as metrics_router
from apt_hunter.security import SecurityMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url=None,
    )
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=[
            "Content-Type",
            "X-CSRF-Token",
            "X-Request-ID",
            "Idempotency-Key",
        ],
    )
    app.include_router(api_router, prefix=settings.api_prefix)
    app.include_router(metrics_router)
    return app


app = create_app()
