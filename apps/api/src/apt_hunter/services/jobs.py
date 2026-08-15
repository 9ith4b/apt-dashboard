from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from apt_hunter.db.session import SessionLocal
from apt_hunter.models import OperationJob


def create_job(
    session: Session,
    *,
    job_type: str,
    subject_type: str,
    subject_id: UUID,
    payload: dict[str, object] | None = None,
    requested_by: str = "analyst",
    parent_job_id: UUID | None = None,
    attempt: int = 1,
) -> OperationJob:
    job = OperationJob(
        task_id="pending",
        job_type=job_type,
        subject_type=subject_type,
        subject_id=subject_id,
        payload=payload or {},
        requested_by=requested_by,
        parent_job_id=parent_job_id,
        attempt=attempt,
    )
    session.add(job)
    session.flush()
    job.task_id = str(job.id)
    return job


def mark_job_running(job_id: UUID) -> None:
    with SessionLocal.begin() as session:
        job = session.get(OperationJob, job_id)
        if job is None or job.status == "canceled":
            return
        job.status = "running"
        job.progress = 10
        job.started_at = datetime.now(UTC)
        job.error = None
        job.version += 1


def mark_job_succeeded(job_id: UUID, result: Mapping[str, object]) -> None:
    with SessionLocal.begin() as session:
        job = session.get(OperationJob, job_id)
        if job is None or job.status == "canceled":
            return
        job.status = "succeeded"
        job.progress = 100
        job.result = dict(result)
        job.finished_at = datetime.now(UTC)
        job.version += 1


def mark_job_failed(job_id: UUID, error: Exception) -> None:
    with SessionLocal.begin() as session:
        job = session.get(OperationJob, job_id)
        if job is None or job.status == "canceled":
            return
        job.status = "failed"
        job.error = str(error)[:4000]
        job.finished_at = datetime.now(UTC)
        job.version += 1


def mark_job_retrying(job_id: UUID, error: Exception) -> None:
    with SessionLocal.begin() as session:
        job = session.get(OperationJob, job_id)
        if job is None or job.status == "canceled":
            return
        job.status = "queued"
        job.progress = 0
        job.error = f"自动重试：{str(error)[:3800]}"
        job.attempt += 1
        job.started_at = None
        job.finished_at = None
        job.version += 1


def dispatch_job(job: OperationJob) -> None:
    if job.job_type == "source_poll":
        from apt_hunter.tasks.rss import poll_source

        poll_source.apply_async(
            args=[str(job.subject_id), str(job.id)],
            task_id=job.task_id,
        )
        return
    if job.job_type == "report_enrichment":
        from apt_hunter.tasks.analysis import enrich_report

        enrich_report.apply_async(
            args=[str(job.subject_id), str(job.id)],
            task_id=job.task_id,
        )
        return
    if job.job_type == "campaign_clustering":
        from apt_hunter.tasks.analysis import cluster_campaign_event

        cluster_campaign_event.apply_async(
            args=[str(job.subject_id), str(job.id)],
            task_id=job.task_id,
        )
        return
    raise ValueError(f"Unsupported job type: {job.job_type}")


def queue_job(
    *,
    job_type: str,
    subject_type: str,
    subject_id: UUID,
    payload: dict[str, object] | None = None,
    requested_by: str = "scheduler",
) -> UUID:
    with SessionLocal() as session:
        job = create_job(
            session,
            job_type=job_type,
            subject_type=subject_type,
            subject_id=subject_id,
            payload=payload,
            requested_by=requested_by,
        )
        session.commit()
        session.refresh(job)
        dispatch_job(job)
        return job.id
