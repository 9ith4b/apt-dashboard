from typing import Any
from uuid import UUID

from sqlalchemy import exists, select

from apt_hunter.config import get_settings
from apt_hunter.db.session import SessionLocal
from apt_hunter.models import Report, ReportAnalysis
from apt_hunter.services.analysis import analyze_report
from apt_hunter.services.jobs import (
    mark_job_failed,
    mark_job_retrying,
    mark_job_running,
    mark_job_succeeded,
    queue_job,
)
from apt_hunter.worker.celery_app import celery_app


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="apt_hunter.reports.enrich",
    max_retries=3,
)
def enrich_report(self: Any, report_id: str, job_id: str | None = None) -> dict[str, str | int]:
    resolved_job_id = UUID(job_id) if job_id else None
    if resolved_job_id:
        mark_job_running(resolved_job_id)
    try:
        result = analyze_report(UUID(report_id))
        if (
            result.get("automation_status") == "fallback"
            and self.request.retries < self.max_retries
        ):
            raise RuntimeError("AI分析已降级，后台将自动重试")
    except Exception as error:
        if self.request.retries < self.max_retries:
            if resolved_job_id:
                mark_job_retrying(resolved_job_id, error)
            countdown = min(300, 30 * (2**self.request.retries))
            raise self.retry(exc=error, countdown=countdown) from error
        if resolved_job_id:
            mark_job_failed(resolved_job_id, error)
        raise
    if resolved_job_id:
        mark_job_succeeded(resolved_job_id, dict(result))
    return result


@celery_app.task(name="apt_hunter.reports.queue_pending")  # type: ignore[untyped-decorator]
def queue_pending_reports() -> dict[str, int]:
    settings = get_settings()
    with SessionLocal.begin() as session:
        statement = (
            select(Report.id)
            .where(
                Report.status == "candidate",
                ~exists().where(ReportAnalysis.report_id == Report.id),
            )
            .order_by(Report.published_at.asc().nullsfirst())
            .limit(settings.enrichment_scheduler_batch_size)
            .with_for_update(skip_locked=True)
        )
        report_ids = list(session.scalars(statement).all())
        session.add_all([ReportAnalysis(report_id=report_id) for report_id in report_ids])

    for report_id in report_ids:
        queue_job(
            job_type="report_enrichment",
            subject_type="report",
            subject_id=report_id,
        )
    return {"queued": len(report_ids)}
