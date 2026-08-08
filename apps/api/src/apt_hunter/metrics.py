from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import cast

from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from redis import Redis
from sqlalchemy import func, select
from starlette.middleware.base import BaseHTTPMiddleware

from apt_hunter.config import get_settings
from apt_hunter.db.session import SessionLocal
from apt_hunter.models import OperationJob, Report, Source

router = APIRouter()

HTTP_REQUESTS = Counter(
    "apt_hunter_http_requests_total",
    "HTTP requests handled by the API.",
    ("method", "route", "status"),
)
HTTP_DURATION = Histogram(
    "apt_hunter_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ("method", "route"),
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
HTTP_IN_PROGRESS = Gauge(
    "apt_hunter_http_requests_in_progress",
    "HTTP requests currently in progress.",
)
JOB_COUNT = Gauge(
    "apt_hunter_operation_jobs",
    "Persisted operation jobs by status.",
    ("status",),
)
REPORT_COUNT = Gauge(
    "apt_hunter_reports",
    "Reports by workflow status.",
    ("status",),
)
SOURCE_FAILURES = Gauge(
    "apt_hunter_source_consecutive_failures",
    "Total consecutive failures across enabled sources.",
)
QUEUE_DEPTH = Gauge(
    "apt_hunter_celery_queue_depth",
    "Messages waiting in the default Celery queue.",
)
DEPENDENCY_UP = Gauge(
    "apt_hunter_dependency_up",
    "Whether an operational dependency was reachable during metric collection.",
    ("dependency",),
)

JOB_STATUSES = ("queued", "running", "succeeded", "failed", "canceled")


def _route_label(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return str(path) if path else "unmatched"


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        started = time.perf_counter()
        HTTP_IN_PROGRESS.inc()
        response_status = 500
        try:
            response = await call_next(request)
            response_status = response.status_code
            return response
        finally:
            route = _route_label(request)
            HTTP_IN_PROGRESS.dec()
            HTTP_REQUESTS.labels(request.method, route, str(response_status)).inc()
            HTTP_DURATION.labels(request.method, route).observe(time.perf_counter() - started)


def refresh_operational_metrics() -> None:
    for status in JOB_STATUSES:
        JOB_COUNT.labels(status).set(0)
    SOURCE_FAILURES.set(0)
    try:
        with SessionLocal() as session:
            for job_status, count in session.execute(
                select(OperationJob.status, func.count()).group_by(OperationJob.status)
            ):
                JOB_COUNT.labels(job_status).set(count)
            for report_status, count in session.execute(
                select(Report.status, func.count()).group_by(Report.status)
            ):
                REPORT_COUNT.labels(report_status).set(count)
            failures = session.scalar(
                select(func.coalesce(func.sum(Source.consecutive_failures), 0)).where(
                    Source.enabled.is_(True)
                )
            )
            SOURCE_FAILURES.set(int(failures or 0))
        DEPENDENCY_UP.labels("database").set(1)
    except Exception:
        DEPENDENCY_UP.labels("database").set(0)

    try:
        redis = Redis.from_url(
            get_settings().redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        QUEUE_DEPTH.set(cast(int, redis.llen("celery")))
        DEPENDENCY_UP.labels("redis").set(1)
    except Exception:
        QUEUE_DEPTH.set(0)
        DEPENDENCY_UP.labels("redis").set(0)


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    refresh_operational_metrics()
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
