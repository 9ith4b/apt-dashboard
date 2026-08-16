from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from apt_hunter.db.session import get_db
from apt_hunter.models import Report, ReportAnalysis, Source
from apt_hunter.schemas.report import (
    AnalysisRead,
    ReportCollectionSummary,
    ReportDetail,
    ReportSummary,
    ReportTaskQueued,
)
from apt_hunter.services.automation import APT_RELEVANT_CLASSIFICATIONS
from apt_hunter.services.jobs import create_job, dispatch_job

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


def _summary(report: Report, source: Source, analysis: ReportAnalysis | None) -> ReportSummary:
    return ReportSummary(
        id=report.id,
        source_id=report.source_id,
        source_name=source.name,
        title=report.title,
        canonical_url=report.canonical_url,
        language=report.language,
        summary=report.normalized_text,
        relevance_score=report.relevance_score,
        relevance_reasons=report.relevance_reasons,
        status=report.status,
        published_at=report.published_at,
        created_at=report.created_at,
        extraction_status=analysis.extraction_status if analysis else None,
        review_status=analysis.review_status if analysis else None,
        confidence_auto=analysis.confidence_auto if analysis else None,
        ai_classification=analysis.ai_classification if analysis else None,
        ai_relevance_score=analysis.ai_relevance_score if analysis else None,
    )


def _analysis_read(analysis: ReportAnalysis) -> AnalysisRead:
    return AnalysisRead.model_validate(analysis, from_attributes=True)


def _report_row(session: Session, report_id: UUID) -> tuple[Report, Source, ReportAnalysis | None]:
    row = session.execute(
        select(Report, Source, ReportAnalysis)
        .join(Source, Source.id == Report.source_id)
        .outerjoin(ReportAnalysis, ReportAnalysis.report_id == Report.id)
        .where(Report.id == report_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return row._tuple()


@router.get("", response_model=list[ReportSummary])
def list_reports(
    session: DbSession,
    source_id: UUID | None = None,
    report_status: Literal["candidate", "filtered", "approved", "rejected"] | None = None,
    scope: Literal["apt", "raw", "excluded"] = "raw",
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ReportSummary]:
    statement = (
        select(Report, Source, ReportAnalysis)
        .join(Source, Source.id == Report.source_id)
        .outerjoin(ReportAnalysis, ReportAnalysis.report_id == Report.id)
    )
    if source_id is not None:
        statement = statement.where(Report.source_id == source_id)
    if report_status is not None:
        statement = statement.where(Report.status == report_status)
    if scope == "apt":
        statement = statement.where(
            Report.status == "approved",
            or_(
                ReportAnalysis.ai_classification.in_(APT_RELEVANT_CLASSIFICATIONS),
                ReportAnalysis.reviewed_by.not_in(["ai-automation"]),
            ),
        )
    elif scope == "excluded":
        statement = statement.where(Report.status.in_(["filtered", "rejected"]))
    statement = statement.order_by(Report.published_at.desc().nullslast()).limit(limit)
    return [
        _summary(report, source, analysis)
        for report, source, analysis in session.execute(statement)
    ]


@router.get("/summary", response_model=ReportCollectionSummary)
def report_collection_summary(session: DbSession) -> ReportCollectionSummary:
    apt_filter = (
        Report.status == "approved",
        or_(
            ReportAnalysis.ai_classification.in_(APT_RELEVANT_CLASSIFICATIONS),
            ReportAnalysis.reviewed_by.not_in(["ai-automation"]),
        ),
    )
    return ReportCollectionSummary(
        total=int(session.scalar(select(func.count()).select_from(Report)) or 0),
        apt=int(
            session.scalar(
                select(func.count())
                .select_from(Report)
                .outerjoin(ReportAnalysis, ReportAnalysis.report_id == Report.id)
                .where(*apt_filter)
            )
            or 0
        ),
        pending=int(
            session.scalar(
                select(func.count()).select_from(Report).where(Report.status == "candidate")
            )
            or 0
        ),
        excluded=int(
            session.scalar(
                select(func.count())
                .select_from(Report)
                .where(Report.status.in_(["filtered", "rejected"]))
            )
            or 0
        ),
        extraction_failed=int(
            session.scalar(
                select(func.count())
                .select_from(ReportAnalysis)
                .where(ReportAnalysis.extraction_status == "failed")
            )
            or 0
        ),
    )


@router.get("/{report_id}", response_model=ReportDetail)
def get_report(report_id: UUID, session: DbSession) -> ReportDetail:
    report, source, analysis = _report_row(session, report_id)
    return ReportDetail(
        **_summary(report, source, analysis).model_dump(),
        analysis=_analysis_read(analysis) if analysis else None,
    )


@router.post(
    "/{report_id}/enrich",
    response_model=ReportTaskQueued,
    status_code=status.HTTP_202_ACCEPTED,
)
def queue_report_enrichment(report_id: UUID, session: DbSession) -> ReportTaskQueued:
    report = session.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if report.status == "filtered":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Filtered reports cannot be enriched until promoted to a candidate",
        )
    analysis = session.get(ReportAnalysis, report_id)
    if analysis is None:
        analysis = ReportAnalysis(report_id=report_id)
        session.add(analysis)
    else:
        analysis.extraction_status = "queued"
        analysis.extraction_error = None
        analysis.review_status = "pending"
        analysis.reviewed_at = None
        analysis.reviewed_by = None
        analysis.version += 1
    report.status = "candidate"
    job = create_job(
        session,
        job_type="report_enrichment",
        subject_type="report",
        subject_id=report.id,
        payload={"report_title": report.title},
    )
    session.commit()
    session.refresh(job)
    dispatch_job(job)
    return ReportTaskQueued(task_id=job.task_id, report_id=report_id)
