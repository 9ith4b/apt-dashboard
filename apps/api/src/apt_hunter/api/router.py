from fastapi import APIRouter

from apt_hunter.api.routes.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["health"])
