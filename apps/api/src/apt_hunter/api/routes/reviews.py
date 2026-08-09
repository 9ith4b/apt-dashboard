from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from apt_hunter.api.routes.reports import _analysis_read, _report_row, _summary
from apt_hunter.db.session import get_db
from apt_hunter.models import (
    AnalysisRevision,
    AutomationException,
    EventReport,
    Report,
    ReportAnalysis,
    Source,
    ThreatEvent,
)
from apt_hunter.schemas.report import (
    AnalysisRevisionRead,
    DiamondEntity,
    ReportDetail,
    ReportSummary,
    ReviewDecision,
)
from apt_hunter.services.actor_normalization import sync_event_actors_from_reports
from apt_hunter.services.event_clustering import generate_merge_candidates
from apt_hunter.services.knowledge import sync_event_knowledge
from apt_hunter.services.watch_rules import evaluate_event_rules

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


def _entity_payload(
    requested: list[DiamondEntity] | None,
    reviewed: list[dict[str, object]] | None,
    extracted: list[dict[str, object]],
) -> list[dict[str, object]]:
    if requested is not None:
        return [entity.model_dump() for entity in requested]
    return reviewed if reviewed is not None else extracted


@router.get("", response_model=list[ReportSummary])
def list_review_queue(
    session: DbSession,
    review_status: Literal["pending", "approved", "rejected"] = "pending",
    limit: int = Query(default=100, ge=1, le=200),
) -> list[ReportSummary]:
    statement = (
        select(Report, Source, ReportAnalysis)
        .join(Source, Source.id == Report.source_id)
        .join(ReportAnalysis, ReportAnalysis.report_id == Report.id)
        .where(ReportAnalysis.review_status == review_status)
        .order_by(ReportAnalysis.updated_at.asc())
        .limit(limit)
    )
    return [
        _summary(report, source, analysis)
        for report, source, analysis in session.execute(statement)
    ]


@router.get("/{report_id}/revisions", response_model=list[AnalysisRevisionRead])
def list_review_revisions(
    report_id: UUID,
    session: DbSession,
) -> list[AnalysisRevisionRead]:
    revisions = session.scalars(
        select(AnalysisRevision)
        .where(AnalysisRevision.report_id == report_id)
        .order_by(AnalysisRevision.review_version.desc())
    )
    return [
        AnalysisRevisionRead.model_validate(revision, from_attributes=True)
        for revision in revisions
    ]


@router.post("/{report_id}/decision", response_model=ReportDetail)
def decide_review(
    report_id: UUID,
    payload: ReviewDecision,
    session: DbSession,
) -> ReportDetail:
    analysis = session.get(ReportAnalysis, report_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    if analysis.extraction_status != "ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The article must finish enrichment before it can be reviewed",
        )
    if analysis.review_status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This report already has a review decision",
        )

    actors = _entity_payload(payload.actors, analysis.reviewed_actors, analysis.actors)
    capabilities = _entity_payload(
        payload.capabilities,
        analysis.reviewed_capabilities,
        analysis.capabilities,
    )
    infrastructure = _entity_payload(
        payload.infrastructure,
        analysis.reviewed_infrastructure,
        analysis.infrastructure,
    )
    victims = _entity_payload(payload.victims, analysis.reviewed_victims, analysis.victims)
    review_version = payload.expected_version + 1

    updated_report_id = session.scalar(
        update(ReportAnalysis)
        .where(
            ReportAnalysis.report_id == report_id,
            ReportAnalysis.version == payload.expected_version,
            ReportAnalysis.extraction_status == "ready",
            ReportAnalysis.review_status == "pending",
        )
        .values(
            review_status=payload.decision,
            reviewed_actors=actors,
            reviewed_capabilities=capabilities,
            reviewed_infrastructure=infrastructure,
            reviewed_victims=victims,
            analyst_note=payload.analyst_note,
            reviewed_at=datetime.now(UTC),
            reviewed_by=payload.reviewed_by,
            version=ReportAnalysis.version + 1,
        )
        .returning(ReportAnalysis.report_id)
    )
    if updated_report_id is None:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This review changed in another session; reload before deciding",
        )
    report = session.get(Report, report_id)
    if report is None:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    report.status = payload.decision
    session.execute(
        update(AutomationException)
        .where(
            AutomationException.report_id == report_id,
            AutomationException.status == "open",
        )
        .values(
            status="resolved",
            resolved_by=payload.reviewed_by,
            resolved_at=datetime.now(UTC),
        )
    )

    snapshot: dict[str, object] = {
        "actors": actors,
        "capabilities": capabilities,
        "infrastructure": infrastructure,
        "victims": victims,
        "confidence_analyst": payload.confidence_analyst,
    }
    session.add(
        AnalysisRevision(
            report_id=report_id,
            review_version=review_version,
            decision=payload.decision,
            snapshot=snapshot,
            analyst_note=payload.analyst_note,
            reviewed_by=payload.reviewed_by,
        )
    )

    if payload.decision == "approved":
        event_link = session.scalar(select(EventReport).where(EventReport.report_id == report_id))
        event = session.get(ThreatEvent, event_link.event_id) if event_link else None
        observed_at = report.published_at or report.created_at
        event_title = payload.event_title or report.title
        event_summary = report.normalized_text.strip() or analysis.content_text[:1000]
        if event is None:
            event = ThreatEvent(
                title=event_title,
                summary=event_summary,
                status="confirmed",
                confidence_auto=analysis.confidence_auto,
                confidence_analyst=payload.confidence_analyst,
                first_seen=observed_at,
                last_seen=observed_at,
            )
            session.add(event)
            session.flush()
            session.add(
                EventReport(
                    event_id=event.id,
                    report_id=report_id,
                    evidence_role="primary",
                )
            )
        else:
            event.title = event_title
            event.summary = event_summary
            event.status = "confirmed"
            event.confidence_auto = analysis.confidence_auto
            event.confidence_analyst = payload.confidence_analyst
            event.first_seen = observed_at
            event.last_seen = observed_at
            event.version += 1
        sync_event_actors_from_reports(session, event.id)
        sync_event_knowledge(session, event.id)
        generate_merge_candidates(session, event.id)
        evaluate_event_rules(session, event.id)
    session.commit()

    report, source, refreshed = _report_row(session, report_id)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return ReportDetail(
        **_summary(report, source, refreshed).model_dump(),
        analysis=_analysis_read(refreshed),
    )
