from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from apt_hunter.db.session import get_db
from apt_hunter.models import Report
from apt_hunter.schemas.report import ReportRead

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[ReportRead])
def list_reports(
    session: DbSession,
    source_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Report]:
    statement = select(Report)
    if source_id is not None:
        statement = statement.where(Report.source_id == source_id)
    statement = statement.order_by(Report.published_at.desc().nullslast()).limit(limit)
    return list(session.scalars(statement).all())
