from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apt_hunter.db.session import get_db
from apt_hunter.models import Report, Source
from apt_hunter.schemas.source import SourceCreate, SourceRead, SourceUpdate, TaskQueued
from apt_hunter.tasks.rss import poll_source

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


def _source_read(source: Source, report_count: int = 0) -> SourceRead:
    return SourceRead.model_validate(source).model_copy(update={"report_count": report_count})


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
        url=str(payload.url),
        enabled=payload.enabled,
        poll_interval_minutes=payload.poll_interval_minutes,
        health_status="pending" if payload.enabled else "disabled",
        next_poll_at=datetime.now(UTC) if payload.enabled else None,
        config={},
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
    if source.type != "rss":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Only RSS sources can be polled in M1",
        )
    task = poll_source.delay(str(source.id))
    return TaskQueued(task_id=str(task.id), source_id=source.id)


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
