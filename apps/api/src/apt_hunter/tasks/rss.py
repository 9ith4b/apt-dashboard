from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select

from apt_hunter.config import get_settings
from apt_hunter.db.session import SessionLocal
from apt_hunter.models import Source
from apt_hunter.services.collector import collect_rss_source
from apt_hunter.services.jobs import (
    mark_job_failed,
    mark_job_running,
    mark_job_succeeded,
    queue_job,
)
from apt_hunter.worker.celery_app import celery_app


@celery_app.task(name="apt_hunter.sources.poll")  # type: ignore[untyped-decorator]
def poll_source(source_id: str, job_id: str | None = None) -> dict[str, str | int | bool]:
    resolved_job_id = UUID(job_id) if job_id else None
    if resolved_job_id:
        mark_job_running(resolved_job_id)
    try:
        result = collect_rss_source(UUID(source_id)).as_dict()
    except Exception as error:
        if resolved_job_id:
            mark_job_failed(resolved_job_id, error)
        raise
    if resolved_job_id:
        mark_job_succeeded(resolved_job_id, dict(result))
    return result


@celery_app.task(name="apt_hunter.sources.poll_due")  # type: ignore[untyped-decorator]
def poll_due_sources() -> dict[str, int]:
    settings = get_settings()
    now = datetime.now(UTC)
    with SessionLocal.begin() as session:
        statement = (
            select(Source)
            .where(
                Source.enabled.is_(True),
                Source.type == "rss",
                or_(Source.next_poll_at.is_(None), Source.next_poll_at <= now),
            )
            .order_by(Source.next_poll_at.asc().nullsfirst())
            .limit(settings.rss_scheduler_batch_size)
            .with_for_update(skip_locked=True)
        )
        sources = list(session.scalars(statement).all())
        source_ids = [source.id for source in sources]
        for source in sources:
            source.next_poll_at = now + timedelta(minutes=source.poll_interval_minutes)

    for source_id in source_ids:
        queue_job(
            job_type="source_poll",
            subject_type="source",
            subject_id=source_id,
        )
    return {"queued": len(source_ids)}
