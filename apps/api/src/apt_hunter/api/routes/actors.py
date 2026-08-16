import csv
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from io import StringIO
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apt_hunter.db.session import get_db
from apt_hunter.models import EventActor, ThreatActor, ThreatActorAlias, ThreatEvent
from apt_hunter.schemas.actor import (
    ActorEventRead,
    ActorTimelineBucket,
    ActorTrackingRead,
    ActorTrackingSummaryRead,
    ThreatActorDetail,
    ThreatActorSummary,
)
from apt_hunter.services.actor_normalization import normalize_actor_key
from apt_hunter.services.actor_tracking import Bucket, build_summary, build_tracking

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
ActorEventRow = tuple[EventActor, ThreatEvent]


def _date_bounds(
    date_from: date | None,
    date_to: date | None,
) -> tuple[datetime | None, datetime | None]:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="date_from must be on or before date_to",
        )
    start = datetime.combine(date_from, time.min, tzinfo=UTC) if date_from else None
    end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=UTC) if date_to else None
    return start, end


def _filtered_actor_ids(
    session: Session,
    date_from: date | None,
    date_to: date | None,
    limit: int,
) -> list[UUID]:
    start, end = _date_bounds(date_from, date_to)
    observed_at = func.coalesce(ThreatEvent.first_seen, ThreatEvent.created_at)
    statement = (
        select(EventActor.actor_id)
        .join(ThreatEvent, ThreatEvent.id == EventActor.event_id)
        .where(
            ThreatEvent.status == "confirmed",
            ThreatEvent.superseded_by_id.is_(None),
        )
    )
    if start is not None:
        statement = statement.where(observed_at >= start)
    if end is not None:
        statement = statement.where(observed_at < end)
    statement = (
        statement.group_by(EventActor.actor_id).order_by(func.max(observed_at).desc()).limit(limit)
    )
    return list(session.scalars(statement))


def _event_rows(
    session: Session,
    actor_ids: list[UUID],
    date_from: date | None,
    date_to: date | None,
) -> dict[UUID, list[ActorEventRow]]:
    if not actor_ids:
        return {}
    start, end = _date_bounds(date_from, date_to)
    observed_at = func.coalesce(ThreatEvent.first_seen, ThreatEvent.created_at)
    statement = (
        select(EventActor, ThreatEvent)
        .join(ThreatEvent, ThreatEvent.id == EventActor.event_id)
        .where(
            EventActor.actor_id.in_(actor_ids),
            ThreatEvent.status == "confirmed",
            ThreatEvent.superseded_by_id.is_(None),
        )
    )
    if start is not None:
        statement = statement.where(observed_at >= start)
    if end is not None:
        statement = statement.where(observed_at < end)
    statement = statement.order_by(observed_at.desc())
    grouped: dict[UUID, list[ActorEventRow]] = defaultdict(list)
    for event_actor, event in session.execute(statement):
        grouped[event_actor.actor_id].append((event_actor, event))
    return grouped


def _aliases(session: Session, actor_ids: list[UUID]) -> dict[UUID, list[str]]:
    grouped: dict[UUID, list[str]] = defaultdict(list)
    if not actor_ids:
        return grouped
    rows = session.execute(
        select(ThreatActorAlias.actor_id, ThreatActorAlias.alias)
        .where(ThreatActorAlias.actor_id.in_(actor_ids))
        .order_by(ThreatActorAlias.alias)
    )
    for actor_id, alias in rows:
        grouped[actor_id].append(alias)
    return grouped


def _observed_at(event: ThreatEvent) -> datetime:
    return event.first_seen or event.created_at


def _summary(
    actor: ThreatActor,
    aliases: list[str],
    rows: list[ActorEventRow],
) -> ThreatActorSummary:
    canonical_key = normalize_actor_key(actor.canonical_name)
    display_aliases = [alias for alias in aliases if normalize_actor_key(alias) != canonical_key]
    observed = [_observed_at(event) for _, event in rows]
    latest = rows[0][1] if rows else None
    return ThreatActorSummary(
        id=actor.id,
        canonical_name=actor.canonical_name,
        aliases=display_aliases,
        origin_country=actor.origin_country,
        event_count=len(rows),
        first_seen=min(observed) if observed else None,
        last_seen=max(observed) if observed else None,
        latest_event_id=latest.id if latest else None,
        latest_event_title=latest.title if latest else None,
    )


def _timeline(
    rows: list[ActorEventRow],
    granularity: Literal["month", "year"],
) -> list[ActorTimelineBucket]:
    buckets: dict[str, int] = defaultdict(int)
    for _, event in rows:
        observed = _observed_at(event)
        key = observed.strftime("%Y") if granularity == "year" else observed.strftime("%Y-%m")
        buckets[key] += 1
    return [
        ActorTimelineBucket(
            key=key,
            label=(f"{key}年" if granularity == "year" else f"{key[:4]}年{key[5:]}月"),
            event_count=buckets[key],
        )
        for key in sorted(buckets, reverse=True)
    ]


def _tracking_result(
    session: Session,
    actor_id: UUID,
    date_from: date | None,
    date_to: date | None,
    bucket: Bucket,
) -> ActorTrackingRead:
    actor = session.get(ThreatActor, actor_id)
    if actor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Actor not found")
    rows = _event_rows(session, [actor_id], None, None).get(actor_id, [])
    try:
        return build_tracking(session, actor, rows, date_from, date_to, bucket)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


@router.get("", response_model=list[ThreatActorSummary])
def list_threat_actors(
    session: DbSession,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=100, ge=1, le=200),
) -> list[ThreatActorSummary]:
    actor_ids = _filtered_actor_ids(session, date_from, date_to, limit)
    if not actor_ids:
        return []
    actors = {
        actor.id: actor
        for actor in session.scalars(select(ThreatActor).where(ThreatActor.id.in_(actor_ids)))
    }
    event_rows = _event_rows(session, actor_ids, date_from, date_to)
    aliases = _aliases(session, actor_ids)
    return [
        _summary(actors[actor_id], aliases[actor_id], event_rows[actor_id])
        for actor_id in actor_ids
        if actor_id in actors
    ]


@router.get("/{actor_id}/tracking", response_model=ActorTrackingRead)
def get_actor_tracking(
    actor_id: UUID,
    session: DbSession,
    date_from: date | None = None,
    date_to: date | None = None,
    bucket: Bucket = "auto",
) -> ActorTrackingRead:
    return _tracking_result(session, actor_id, date_from, date_to, bucket)


@router.post("/{actor_id}/tracking/summary", response_model=ActorTrackingSummaryRead)
def generate_actor_tracking_summary(
    actor_id: UUID,
    session: DbSession,
    date_from: date | None = None,
    date_to: date | None = None,
    bucket: Bucket = "auto",
) -> ActorTrackingSummaryRead:
    tracking = _tracking_result(session, actor_id, date_from, date_to, bucket)
    return build_summary(session, tracking)


@router.get("/{actor_id}/tracking/export")
def export_actor_tracking(
    actor_id: UUID,
    session: DbSession,
    date_from: date | None = None,
    date_to: date | None = None,
    bucket: Bucket = "auto",
    export_format: Literal["json", "csv"] = Query(default="json", alias="format"),
) -> Response:
    tracking = _tracking_result(session, actor_id, date_from, date_to, bucket)
    filename = f"actor-tracking-{actor_id}.{export_format}"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if export_format == "json":
        return JSONResponse(content=tracking.model_dump(mode="json"), headers=headers)

    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "record_type",
            "category",
            "value",
            "event_id",
            "title",
            "first_seen",
            "confidence",
        ],
    )
    writer.writeheader()
    for event in tracking.events:
        writer.writerow(
            {
                "record_type": "event",
                "event_id": event.id,
                "title": event.title,
                "first_seen": event.first_seen.isoformat() if event.first_seen else "",
                "confidence": event.confidence if event.confidence is not None else "",
            }
        )
    for change in tracking.changes:
        for value in change.new_values:
            writer.writerow({"record_type": "new", "category": change.category, "value": value})
        for value in change.disappeared_values:
            writer.writerow(
                {
                    "record_type": "disappeared",
                    "category": change.category,
                    "value": value,
                }
            )
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers=headers,
    )


@router.get("/{actor_id}", response_model=ThreatActorDetail)
def get_threat_actor(
    actor_id: UUID,
    session: DbSession,
    date_from: date | None = None,
    date_to: date | None = None,
    granularity: Literal["month", "year"] = "month",
) -> ThreatActorDetail:
    actor = session.get(ThreatActor, actor_id)
    if actor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Actor not found")
    rows = _event_rows(session, [actor_id], date_from, date_to).get(actor_id, [])
    aliases = _aliases(session, [actor_id]).get(actor_id, [])
    summary = _summary(actor, aliases, rows)
    return ThreatActorDetail(
        **summary.model_dump(),
        description=actor.description,
        events=[
            ActorEventRead(
                id=event.id,
                title=event.title,
                summary=event.summary,
                status=event.status,
                confidence=event_actor.confidence,
                first_seen=event.first_seen,
                last_seen=event.last_seen,
                reported_name=event_actor.reported_name,
            )
            for event_actor, event in rows
        ],
        timeline=_timeline(rows, granularity),
    )
