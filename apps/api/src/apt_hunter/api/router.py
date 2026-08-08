from fastapi import APIRouter

from apt_hunter.api.routes.actors import router as actors_router
from apt_hunter.api.routes.auth import audit_router
from apt_hunter.api.routes.auth import router as auth_router
from apt_hunter.api.routes.campaigns import router as campaigns_router
from apt_hunter.api.routes.events import router as events_router
from apt_hunter.api.routes.health import router as health_router
from apt_hunter.api.routes.hunt import indicators_router, observables_router
from apt_hunter.api.routes.notifications import router as notifications_router
from apt_hunter.api.routes.operations import router as operations_router
from apt_hunter.api.routes.reports import router as reports_router
from apt_hunter.api.routes.reviews import router as reviews_router
from apt_hunter.api.routes.search import router as search_router
from apt_hunter.api.routes.sources import router as sources_router
from apt_hunter.api.routes.watch_rules import router as watch_rules_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(audit_router, prefix="/audit-logs", tags=["audit"])
api_router.include_router(sources_router, prefix="/sources", tags=["sources"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_router.include_router(reviews_router, prefix="/reviews", tags=["reviews"])
api_router.include_router(events_router, prefix="/events", tags=["events"])
api_router.include_router(actors_router, prefix="/actors", tags=["actors"])
api_router.include_router(campaigns_router, prefix="/campaigns", tags=["campaigns"])
api_router.include_router(observables_router, prefix="/observables", tags=["observables"])
api_router.include_router(indicators_router, prefix="/indicators", tags=["indicators"])
api_router.include_router(watch_rules_router, prefix="/watch-rules", tags=["watch-rules"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
api_router.include_router(search_router, prefix="/search", tags=["search"])
api_router.include_router(operations_router, prefix="/operations/jobs", tags=["operations"])
