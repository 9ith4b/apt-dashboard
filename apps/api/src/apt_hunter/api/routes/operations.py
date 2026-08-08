from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from apt_hunter.db.session import get_db
from apt_hunter.models import OperationJob
from apt_hunter.schemas.operations import OperationJobRead
from apt_hunter.services.jobs import create_job, dispatch_job
from apt_hunter.worker.celery_app import celery_app

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


def _job_or_404(session: Session, job_id: UUID) -> OperationJob:
    job = session.get(OperationJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.get("", response_model=list[OperationJobRead])
def list_jobs(
    session: DbSession,
    job_status: Literal["queued", "running", "succeeded", "failed", "canceled"] | None = None,
    limit: int = Query(default=100, ge=1, le=200),
) -> list[OperationJobRead]:
    statement = select(OperationJob)
    if job_status is not None:
        statement = statement.where(OperationJob.status == job_status)
    jobs = session.scalars(statement.order_by(OperationJob.created_at.desc()).limit(limit))
    return [OperationJobRead.model_validate(job, from_attributes=True) for job in jobs]


@router.get("/{job_id}", response_model=OperationJobRead)
def get_job(job_id: UUID, session: DbSession) -> OperationJobRead:
    return OperationJobRead.model_validate(_job_or_404(session, job_id), from_attributes=True)


@router.post(
    "/{job_id}/retry", response_model=OperationJobRead, status_code=status.HTTP_202_ACCEPTED
)
def retry_job(job_id: UUID, session: DbSession) -> OperationJobRead:
    original = _job_or_404(session, job_id)
    if original.status not in {"failed", "canceled"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed or canceled jobs can be retried",
        )
    job = create_job(
        session,
        job_type=original.job_type,
        subject_type=original.subject_type,
        subject_id=original.subject_id,
        payload=original.payload,
        requested_by="analyst",
        parent_job_id=original.id,
        attempt=original.attempt + 1,
    )
    session.commit()
    session.refresh(job)
    dispatch_job(job)
    return OperationJobRead.model_validate(job, from_attributes=True)


@router.post("/{job_id}/cancel", response_model=OperationJobRead)
def cancel_job(
    job_id: UUID,
    session: DbSession,
    expected_version: int = Query(ge=1),
) -> OperationJobRead:
    job = _job_or_404(session, job_id)
    if job.version != expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This job changed in another session; reload before canceling",
        )
    if job.status not in {"queued", "running"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only queued or running jobs can be canceled",
        )
    celery_app.control.revoke(job.task_id, terminate=False)
    job.status = "canceled"
    job.finished_at = datetime.now(UTC)
    job.version += 1
    session.commit()
    session.refresh(job)
    return OperationJobRead.model_validate(job, from_attributes=True)
