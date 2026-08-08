from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from apt_hunter.api.routes.reports import _summary
from apt_hunter.db.session import get_db
from apt_hunter.models import EventReport, Report, ReportAnalysis, Source, ThreatEvent
from apt_hunter.schemas.event import EventDiamond, ThreatEventDetail, ThreatEventSummary
from apt_hunter.schemas.report import DiamondEntity

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


def _entities(
    reviewed: list[dict[str, object]] | None,
    extracted: list[dict[str, object]],
) -> list[dict[str, object]]:
    return reviewed if reviewed is not None else extracted


def _merge_entities(groups: list[list[dict[str, object]]]) -> list[DiamondEntity]:
    merged: dict[tuple[str, str], DiamondEntity] = {}
    for group in groups:
        for raw_entity in group:
            entity = DiamondEntity.model_validate(raw_entity)
            key = (entity.type.casefold(), entity.name.casefold())
            current = merged.get(key)
            if current is None or entity.confidence > current.confidence:
                merged[key] = entity
    return sorted(merged.values(), key=lambda item: (-item.confidence, item.name.casefold()))


def _diamond(analyses: list[ReportAnalysis]) -> EventDiamond:
    return EventDiamond(
        actors=_merge_entities(
            [_entities(analysis.reviewed_actors, analysis.actors) for analysis in analyses]
        ),
        capabilities=_merge_entities(
            [
                _entities(analysis.reviewed_capabilities, analysis.capabilities)
                for analysis in analyses
            ]
        ),
        infrastructure=_merge_entities(
            [
                _entities(analysis.reviewed_infrastructure, analysis.infrastructure)
                for analysis in analyses
            ]
        ),
        victims=_merge_entities(
            [_entities(analysis.reviewed_victims, analysis.victims) for analysis in analyses]
        ),
    )


def _event_summary(event: ThreatEvent, analyses: list[ReportAnalysis]) -> ThreatEventSummary:
    diamond = _diamond(analyses)
    return ThreatEventSummary(
        id=event.id,
        title=event.title,
        summary=event.summary,
        status=event.status,
        confidence_auto=event.confidence_auto,
        confidence_analyst=event.confidence_analyst,
        first_seen=event.first_seen,
        last_seen=event.last_seen,
        report_count=len(analyses),
        actor_names=[entity.name for entity in diamond.actors],
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


@router.get("", response_model=list[ThreatEventSummary])
def list_threat_events(
    session: DbSession,
    limit: int = Query(default=100, ge=1, le=200),
) -> list[ThreatEventSummary]:
    events = list(
        session.scalars(
            select(ThreatEvent)
            .order_by(ThreatEvent.first_seen.desc().nullslast(), ThreatEvent.created_at.desc())
            .limit(limit)
        )
    )
    if not events:
        return []

    analyses_by_event: dict[UUID, list[ReportAnalysis]] = {event.id: [] for event in events}
    rows = session.execute(
        select(EventReport.event_id, ReportAnalysis)
        .join(ReportAnalysis, ReportAnalysis.report_id == EventReport.report_id)
        .where(EventReport.event_id.in_([event.id for event in events]))
    )
    for event_id, analysis in rows:
        analyses_by_event[event_id].append(analysis)
    return [_event_summary(event, analyses_by_event[event.id]) for event in events]


@router.get("/{event_id}", response_model=ThreatEventDetail)
def get_threat_event(event_id: UUID, session: DbSession) -> ThreatEventDetail:
    event = session.get(ThreatEvent, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    rows = list(
        session.execute(
            select(Report, Source, ReportAnalysis)
            .join(EventReport, EventReport.report_id == Report.id)
            .join(Source, Source.id == Report.source_id)
            .join(ReportAnalysis, ReportAnalysis.report_id == Report.id)
            .where(EventReport.event_id == event_id)
            .order_by(Report.published_at.desc().nullslast())
        )
    )
    analyses = [analysis for _, _, analysis in rows]
    summary = _event_summary(event, analyses)
    return ThreatEventDetail(
        **summary.model_dump(),
        diamond=_diamond(analyses),
        reports=[_summary(report, source, analysis) for report, source, analysis in rows],
    )
