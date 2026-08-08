from celery import Celery

from apt_hunter.config import get_settings

settings = get_settings()
celery_app = Celery(
    "apt_hunter",
    broker=settings.redis_url,
    backend=settings.redis_url,
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


@celery_app.task(name="apt_hunter.system.ping")  # type: ignore[untyped-decorator]
def ping() -> dict[str, str]:
    return {"status": "ok"}
