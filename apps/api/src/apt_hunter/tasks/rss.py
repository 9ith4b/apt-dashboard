from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select

from apt_hunter.config import get_settings
from apt_hunter.db.session import SessionLocal
from apt_hunter.models import Source
from apt_hunter.services.collector import collect_rss_source
from apt_hunter.worker.celery_app import celery_app


@celery_app.task(name="apt_hunter.sources.poll")  # type: ignore[untyped-decorator]
def poll_source(source_id: str) -> dict[str, str | int | bool]:
    return collect_rss_source(UUID(source_id)).as_dict()


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
        poll_source.delay(str(source_id))
    return {"queued": len(source_ids)}
