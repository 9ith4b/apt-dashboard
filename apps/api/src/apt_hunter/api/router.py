from fastapi import APIRouter

from apt_hunter.api.routes.actors import router as actors_router
from apt_hunter.api.routes.events import router as events_router
from apt_hunter.api.routes.health import router as health_router
from apt_hunter.api.routes.reports import router as reports_router
from apt_hunter.api.routes.reviews import router as reviews_router
from apt_hunter.api.routes.sources import router as sources_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(sources_router, prefix="/sources", tags=["sources"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_router.include_router(reviews_router, prefix="/reviews", tags=["reviews"])
api_router.include_router(events_router, prefix="/events", tags=["events"])
api_router.include_router(actors_router, prefix="/actors", tags=["actors"])
