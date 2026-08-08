import os
from datetime import UTC, datetime
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apt_hunter.db.session import get_db
from apt_hunter.models import Report, Source
from apt_hunter.schemas.source import (
    SourceCreate,
    SourceRead,
    SourceType,
    SourceUpdate,
    TaskQueued,
    _validate_connector,
)
from apt_hunter.services.jobs import create_job, dispatch_job

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


def _source_read(source: Source, report_count: int = 0) -> SourceRead:
    credential_configured = bool(source.secret_ref and os.getenv(source.secret_ref))
    return SourceRead.model_validate(source).model_copy(
        update={
            "report_count": report_count,
            "credential_configured": credential_configured,
        }
    )


def _get_source_or_404(session: Session, source_id: UUID) -> Source:
    source = session.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return source


@router.get("", response_model=list[SourceRead])
def list_sources(session: DbSession) -> list[SourceRead]:
    statement = (
        select(Source, func.count(Report.id))
        .outerjoin(Report, Report.source_id == Source.id)
        .group_by(Source.id)
        .order_by(Source.created_at.desc())
    )
    rows = session.execute(statement).all()
    return [_source_read(source, int(report_count)) for source, report_count in rows]


@router.post("", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def create_source(payload: SourceCreate, session: DbSession) -> SourceRead:
    source = Source(
        type=payload.type,
        name=payload.name.strip(),
        url=str(payload.url) if payload.url else None,
        enabled=payload.enabled,
        poll_interval_minutes=payload.poll_interval_minutes,
        health_status="pending" if payload.enabled else "disabled",
        next_poll_at=datetime.now(UTC) if payload.enabled else None,
        config=payload.config,
        secret_ref=payload.secret_ref,
    )
    session.add(source)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A source with the same name or URL already exists",
        ) from exc
    session.refresh(source)
    return _source_read(source)


@router.patch("/{source_id}", response_model=SourceRead)
def update_source(
    source_id: UUID,
    payload: SourceUpdate,
    session: DbSession,
) -> SourceRead:
    source = _get_source_or_404(session, source_id)
    changes = payload.model_dump(exclude_unset=True)
    if "url" in changes and changes["url"] is not None:
        changes["url"] = str(changes["url"])

    next_config = changes.get("config", source.config)
    next_secret_ref = changes.get("secret_ref", source.secret_ref)
    _validate_connector(
        cast(SourceType, source.type),
        payload.url if "url" in changes else source.url,
        next_config if isinstance(next_config, dict) else {},
        next_secret_ref if isinstance(next_secret_ref, str) else None,
    )

    was_enabled = source.enabled
    for field, value in changes.items():
        setattr(source, field, value)

    if source.enabled and not was_enabled:
        source.health_status = "pending"
        source.next_poll_at = datetime.now(UTC)
    elif not source.enabled:
        source.health_status = "disabled"
        source.next_poll_at = None

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A source with the same name or URL already exists",
        ) from exc
    session.refresh(source)
    report_count = session.scalar(
        select(func.count(Report.id)).where(Report.source_id == source.id)
    )
    return _source_read(source, int(report_count or 0))


@router.post(
    "/{source_id}/poll",
    response_model=TaskQueued,
    status_code=status.HTTP_202_ACCEPTED,
)
def queue_source_poll(source_id: UUID, session: DbSession) -> TaskQueued:
    source = _get_source_or_404(session, source_id)
    job = create_job(
        session,
        job_type="source_poll",
        subject_type="source",
        subject_id=source.id,
        payload={"source_name": source.name},
    )
    session.commit()
    session.refresh(job)
    dispatch_job(job)
    return TaskQueued(task_id=job.task_id, source_id=source.id)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(
    source_id: UUID,
    session: DbSession,
) -> Response:
    source = _get_source_or_404(session, source_id)
    report_count = session.scalar(
        select(func.count(Report.id)).where(Report.source_id == source.id)
    )
    if report_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Disable sources with collected reports instead of deleting them",
        )
    session.delete(source)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
