from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apt_hunter.api.routes.reports import _summary
from apt_hunter.db.session import get_db
from apt_hunter.models import (
    AttackTechnique,
    EventMergeCandidate,
    EventObservable,
    EventReport,
    EventTechnique,
    Evidence,
    Observable,
    Report,
    ReportAnalysis,
    Source,
    ThreatEvent,
)
from apt_hunter.schemas.event import (
    EventDiamond,
    EventMergeCandidateRead,
    EventMergeDecision,
    EventMergeUndo,
    EventObservableRead,
    EventTechniqueRead,
    MergeEventRef,
    ThreatEventDetail,
    ThreatEventSummary,
)
from apt_hunter.schemas.report import DiamondEntity
from apt_hunter.services.event_clustering import (
    decide_merge_candidate,
    undo_merge_candidate,
)

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


def _event_summary(
    event: ThreatEvent,
    analyses: list[ReportAnalysis],
    observable_count: int,
    technique_ids: list[str],
) -> ThreatEventSummary:
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
        observable_count=observable_count,
        technique_ids=technique_ids,
        superseded_by_id=event.superseded_by_id,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def _merge_candidate_reads(
    session: Session,
    candidates: list[EventMergeCandidate],
) -> list[EventMergeCandidateRead]:
    event_ids = {
        event_id
        for candidate in candidates
        for event_id in (candidate.source_event_id, candidate.target_event_id)
    }
    events = {
        event.id: event
        for event in session.scalars(select(ThreatEvent).where(ThreatEvent.id.in_(event_ids)))
    }
    report_counts = {
        event_id: int(count)
        for event_id, count in session.execute(
            select(EventReport.event_id, func.count())
            .where(EventReport.event_id.in_(event_ids))
            .group_by(EventReport.event_id)
        )
    }

    def event_ref(event_id: UUID) -> MergeEventRef:
        event = events[event_id]
        return MergeEventRef(
            id=event.id,
            title=event.title,
            first_seen=event.first_seen,
            report_count=report_counts.get(event.id, 0),
        )

    return [
        EventMergeCandidateRead(
            id=candidate.id,
            source_event=event_ref(candidate.source_event_id),
            target_event=event_ref(candidate.target_event_id),
            score=candidate.score,
            features=candidate.features,
            status=candidate.status,
            decision_reason=candidate.decision_reason,
            moved_report_ids=candidate.moved_report_ids,
            reviewed_at=candidate.reviewed_at,
            version=candidate.version,
            created_at=candidate.created_at,
        )
        for candidate in candidates
        if candidate.source_event_id in events and candidate.target_event_id in events
    ]


@router.get("", response_model=list[ThreatEventSummary])
def list_threat_events(
    session: DbSession,
    limit: int = Query(default=100, ge=1, le=200),
) -> list[ThreatEventSummary]:
    events = list(
        session.scalars(
            select(ThreatEvent)
            .where(ThreatEvent.superseded_by_id.is_(None))
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
    event_ids = [event.id for event in events]
    observable_counts = {
        event_id: int(count)
        for event_id, count in session.execute(
            select(EventObservable.event_id, func.count())
            .where(EventObservable.event_id.in_(event_ids))
            .group_by(EventObservable.event_id)
        )
    }
    techniques_by_event: dict[UUID, list[str]] = {event_id: [] for event_id in event_ids}
    technique_rows = session.execute(
        select(EventTechnique.event_id, EventTechnique.technique_id)
        .where(EventTechnique.event_id.in_(event_ids))
        .order_by(EventTechnique.technique_id)
    )
    for event_id, technique_id in technique_rows:
        techniques_by_event[event_id].append(technique_id)
    return [
        _event_summary(
            event,
            analyses_by_event[event.id],
            int(observable_counts.get(event.id, 0)),
            techniques_by_event[event.id],
        )
        for event in events
    ]


@router.get("/merge-candidates", response_model=list[EventMergeCandidateRead])
def list_merge_candidates(
    session: DbSession,
    candidate_status: Literal["pending", "approved", "rejected", "undone"] = "pending",
    limit: int = Query(default=100, ge=1, le=200),
) -> list[EventMergeCandidateRead]:
    candidates = list(
        session.scalars(
            select(EventMergeCandidate)
            .where(EventMergeCandidate.status == candidate_status)
            .order_by(EventMergeCandidate.score.desc(), EventMergeCandidate.created_at.asc())
            .limit(limit)
        )
    )
    return _merge_candidate_reads(session, candidates)


@router.post(
    "/merge-candidates/{candidate_id}/decision",
    response_model=EventMergeCandidateRead,
)
def decide_event_merge(
    candidate_id: UUID,
    payload: EventMergeDecision,
    session: DbSession,
) -> EventMergeCandidateRead:
    try:
        candidate = decide_merge_candidate(
            session,
            candidate_id,
            decision=payload.decision,
            reason=payload.reason,
            expected_version=payload.expected_version,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    session.commit()
    refreshed = session.get(EventMergeCandidate, candidate.id)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return _merge_candidate_reads(session, [refreshed])[0]


@router.post(
    "/merge-candidates/{candidate_id}/undo",
    response_model=EventMergeCandidateRead,
)
def undo_event_merge(
    candidate_id: UUID,
    payload: EventMergeUndo,
    session: DbSession,
) -> EventMergeCandidateRead:
    try:
        candidate = undo_merge_candidate(
            session,
            candidate_id,
            expected_version=payload.expected_version,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    session.commit()
    refreshed = session.get(EventMergeCandidate, candidate.id)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return _merge_candidate_reads(session, [refreshed])[0]


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
    observable_rows = list(
        session.execute(
            select(EventObservable, Observable, Evidence)
            .join(Observable, Observable.id == EventObservable.observable_id)
            .join(Evidence, Evidence.id == EventObservable.evidence_id)
            .where(EventObservable.event_id == event_id)
            .order_by(Observable.type, Observable.value_normalized)
        )
    )
    technique_rows = list(
        session.execute(
            select(EventTechnique, AttackTechnique, Evidence)
            .join(AttackTechnique, AttackTechnique.technique_id == EventTechnique.technique_id)
            .join(Evidence, Evidence.id == EventTechnique.evidence_id)
            .where(EventTechnique.event_id == event_id)
            .order_by(EventTechnique.technique_id)
        )
    )
    summary = _event_summary(
        event,
        analyses,
        len(observable_rows),
        [technique.technique_id for _, technique, _ in technique_rows],
    )
    return ThreatEventDetail(
        **summary.model_dump(),
        diamond=_diamond(analyses),
        reports=[_summary(report, source, analysis) for report, source, analysis in rows],
        observables=[
            EventObservableRead(
                id=observable.id,
                type=observable.type,
                value_original=observable.value_original,
                value_normalized=observable.value_normalized,
                scope=observable.scope,
                confidence=event_observable.confidence,
                evidence_id=evidence.id,
                evidence=evidence.quote,
                first_seen=observable.first_seen,
                last_seen=observable.last_seen,
            )
            for event_observable, observable, evidence in observable_rows
        ],
        attack_techniques=[
            EventTechniqueRead(
                technique_id=technique.technique_id,
                name=technique.name,
                tactic=technique.tactic,
                confidence=event_technique.confidence,
                evidence_id=evidence.id,
                evidence=evidence.quote,
            )
            for event_technique, technique, evidence in technique_rows
        ],
    )
