from celery import Celery

from apt_hunter.config import get_settings

settings = get_settings()
celery_app = Celery(
    "apt_hunter",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["apt_hunter.tasks.rss", "apt_hunter.tasks.analysis"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
celery_app.conf.beat_schedule = {
    "poll-due-rss-sources": {
        "task": "apt_hunter.sources.poll_due",
        "schedule": 60.0,
    },
    "queue-pending-report-enrichment": {
        "task": "apt_hunter.reports.queue_pending",
        "schedule": 60.0,
    },
}


@celery_app.task(name="apt_hunter.system.ping")  # type: ignore[untyped-decorator]
def ping() -> dict[str, str]:
    return {"status": "ok"}
