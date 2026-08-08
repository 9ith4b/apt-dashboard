from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from apt_hunter.db.session import get_db
from apt_hunter.models import Observable, Report, ThreatActor, ThreatActorAlias, ThreatEvent
from apt_hunter.schemas.search import SearchResponse, SearchResultRead

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


def _score(query: str, title: str, subtitle: str) -> int:
    needle = query.casefold()
    title_value = title.casefold()
    if title_value == needle:
        return 100
    if title_value.startswith(needle):
        return 90
    if needle in title_value:
        return 80
    return 60 if needle in subtitle.casefold() else 50


@router.get("", response_model=SearchResponse)
def global_search(
    session: DbSession,
    q: str = Query(min_length=2, max_length=200),
    limit: int = Query(default=20, ge=1, le=50),
) -> SearchResponse:
    query = q.strip()
    pattern = f"%{query}%"
    results: list[SearchResultRead] = []

    for actor in session.scalars(
        select(ThreatActor)
        .outerjoin(ThreatActorAlias, ThreatActorAlias.actor_id == ThreatActor.id)
        .where(
            or_(
                ThreatActor.canonical_name.ilike(pattern),
                ThreatActor.description.ilike(pattern),
                ThreatActorAlias.alias.ilike(pattern),
            )
        )
        .distinct()
        .limit(limit)
    ):
        results.append(
            SearchResultRead(
                kind="actor",
                id=actor.id,
                title=actor.canonical_name,
                subtitle=actor.description or actor.origin_country or "攻击组织",
                url=f"/actors?actor={actor.id}",
                score=_score(query, actor.canonical_name, actor.description),
            )
        )
    for event in session.scalars(
        select(ThreatEvent)
        .where(
            ThreatEvent.superseded_by_id.is_(None),
            or_(ThreatEvent.title.ilike(pattern), ThreatEvent.summary.ilike(pattern)),
        )
        .limit(limit)
    ):
        results.append(
            SearchResultRead(
                kind="event",
                id=event.id,
                title=event.title,
                subtitle=event.summary,
                url=f"/events?event={event.id}",
                score=_score(query, event.title, event.summary),
            )
        )
    for observable in session.scalars(
        select(Observable).where(Observable.value_normalized.ilike(pattern)).limit(limit)
    ):
        results.append(
            SearchResultRead(
                kind="observable",
                id=observable.id,
                title=observable.value_normalized,
                subtitle=f"Observable · {observable.type}",
                url=f"/hunt?observable={observable.id}",
                score=_score(query, observable.value_normalized, observable.type),
            )
        )
    for report in session.scalars(
        select(Report)
        .where(or_(Report.title.ilike(pattern), Report.normalized_text.ilike(pattern)))
        .limit(limit)
    ):
        results.append(
            SearchResultRead(
                kind="report",
                id=report.id,
                title=report.title,
                subtitle=report.normalized_text,
                url=f"/feed?report={report.id}",
                score=_score(query, report.title, report.normalized_text),
            )
        )
    ordered = sorted(results, key=lambda item: (-item.score, item.title.casefold()))[:limit]
    return SearchResponse(query=query, total=len(ordered), results=ordered)
