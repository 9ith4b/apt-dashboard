from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from apt_hunter.api.routes.reports import _analysis_read, _report_row, _summary
from apt_hunter.db.session import get_db
from apt_hunter.models import Report, ReportAnalysis, Source
from apt_hunter.schemas.report import ReportDetail, ReportSummary, ReviewDecision

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


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

    updated_report_id = session.scalar(
        update(ReportAnalysis)
        .where(
            ReportAnalysis.report_id == report_id,
            ReportAnalysis.version == payload.expected_version,
            ReportAnalysis.extraction_status == "ready",
        )
        .values(
            review_status=payload.decision,
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
    session.commit()

    report, source, refreshed = _report_row(session, report_id)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return ReportDetail(
        **_summary(report, source, refreshed).model_dump(),
        analysis=_analysis_read(refreshed),
    )
