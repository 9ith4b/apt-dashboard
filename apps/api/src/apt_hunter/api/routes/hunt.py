from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.orm import Session

from apt_hunter.db.session import get_db
from apt_hunter.models import (
    EventObservable,
    Evidence,
    Indicator,
    IndicatorEvidence,
    Observable,
    ObservableEnrichment,
    Report,
    ReportObservable,
    Source,
    ThreatEvent,
)
from apt_hunter.schemas.hunt import (
    IndicatorRead,
    IndicatorSummary,
    IndicatorUpdate,
    ObservableDetail,
    ObservableEnrichmentRead,
    ObservableEventAppearance,
    ObservablePromote,
    ObservableReportAppearance,
    ObservableSummary,
)

observables_router = APIRouter()
indicators_router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


def _indicator_summary(indicator: Indicator | None) -> IndicatorSummary | None:
    if indicator is None:
        return None
    return IndicatorSummary(
        id=indicator.id,
        purpose=indicator.purpose,
        valid_from=indicator.valid_from,
        valid_until=indicator.valid_until,
        confidence=indicator.confidence,
        severity=indicator.severity,
        revoked=indicator.revoked,
        reviewed_by=indicator.reviewed_by,
        version=indicator.version,
    )


def _observable_summaries(
    session: Session,
    observables: list[Observable],
) -> list[ObservableSummary]:
    if not observables:
        return []
    observable_ids = [observable.id for observable in observables]
    report_counts = {
        observable_id: int(count)
        for observable_id, count in session.execute(
            select(ReportObservable.observable_id, func.count())
            .where(ReportObservable.observable_id.in_(observable_ids))
            .group_by(ReportObservable.observable_id)
        )
    }
    event_counts = {
        observable_id: int(count)
        for observable_id, count in session.execute(
            select(EventObservable.observable_id, func.count())
            .where(EventObservable.observable_id.in_(observable_ids))
            .group_by(EventObservable.observable_id)
        )
    }
    indicators = {
        indicator.observable_id: indicator
        for indicator in session.scalars(
            select(Indicator).where(Indicator.observable_id.in_(observable_ids))
        )
    }
    ai_contexts = {
        enrichment.observable_id: enrichment
        for enrichment in session.scalars(
            select(ObservableEnrichment).where(
                ObservableEnrichment.observable_id.in_(observable_ids),
                ObservableEnrichment.provider == "ai-context",
            )
        )
    }
    return [
        ObservableSummary(
            id=observable.id,
            type=observable.type,
            value_original=observable.value_original,
            value_normalized=observable.value_normalized,
            scope=observable.scope,
            validation_status=observable.validation_status,
            first_seen=observable.first_seen,
            last_seen=observable.last_seen,
            report_count=report_counts.get(observable.id, 0),
            event_count=event_counts.get(observable.id, 0),
            evidence_count=report_counts.get(observable.id, 0),
            ai_disposition=(ai_contexts[observable.id].result or {}).get("disposition")
            if observable.id in ai_contexts
            else None,
            ai_role=(ai_contexts[observable.id].result or {}).get("role")
            if observable.id in ai_contexts
            else None,
            ai_confidence=(ai_contexts[observable.id].result or {}).get("confidence")
            if observable.id in ai_contexts
            else None,
            ai_decision_reason=(ai_contexts[observable.id].result or {}).get("decision_reason")
            if observable.id in ai_contexts
            else None,
            ai_decided_at=ai_contexts[observable.id].queried_at
            if observable.id in ai_contexts
            else None,
            indicator=_indicator_summary(indicators.get(observable.id)),
        )
        for observable in observables
    ]


def _indicator_pattern(observable: Observable) -> str:
    field = {
        "domain": "domain-name:value",
        "ipv4": "ipv4-addr:value",
        "ipv6": "ipv6-addr:value",
        "url": "url:value",
        "email": "email-addr:value",
        "md5": "file:hashes.MD5",
        "sha1": "file:hashes.'SHA-1'",
        "sha256": "file:hashes.'SHA-256'",
    }.get(observable.type, "artifact:payload_bin")
    escaped = observable.value_normalized.replace("\\", "\\\\").replace("'", "\\'")
    return f"[{field} = '{escaped}']"


def _indicator_read(
    session: Session,
    indicator: Indicator,
    observable: Observable,
) -> IndicatorRead:
    evidence_ids = list(
        session.scalars(
            select(IndicatorEvidence.evidence_id)
            .where(IndicatorEvidence.indicator_id == indicator.id)
            .order_by(IndicatorEvidence.created_at)
        )
    )
    return IndicatorRead(
        **_indicator_summary(indicator).model_dump(),  # type: ignore[union-attr]
        observable_id=observable.id,
        observable_type=observable.type,
        value_normalized=observable.value_normalized,
        pattern=indicator.pattern,
        reviewed_at=indicator.reviewed_at,
        evidence_ids=evidence_ids,
    )


@observables_router.get("", response_model=list[ObservableSummary])
def list_observables(
    session: DbSession,
    q: str | None = Query(default=None, max_length=1000),
    observable_type: str | None = Query(default=None, max_length=32),
    values: Annotated[list[str] | None, Query()] = None,
    limit: int = Query(default=100, ge=1, le=200),
) -> list[ObservableSummary]:
    statement = select(Observable)
    if q:
        statement = statement.where(
            func.lower(Observable.value_normalized).contains(q.strip().casefold())
        )
    if observable_type:
        statement = statement.where(Observable.type == observable_type)
    if values:
        normalized_values = {value.strip().casefold() for value in values if value.strip()}
        statement = statement.where(func.lower(Observable.value_normalized).in_(normalized_values))
    observables = list(
        session.scalars(statement.order_by(Observable.last_seen.desc().nullslast()).limit(limit))
    )
    return _observable_summaries(session, observables)


@observables_router.get("/count", response_model=int)
def count_observables(
    session: DbSession,
    q: str | None = Query(default=None, max_length=1000),
    observable_type: str | None = Query(default=None, max_length=32),
) -> int:
    statement = select(func.count()).select_from(Observable)
    if q:
        statement = statement.where(
            func.lower(Observable.value_normalized).contains(q.strip().casefold())
        )
    if observable_type:
        statement = statement.where(Observable.type == observable_type)
    return int(session.scalar(statement) or 0)


@observables_router.get("/{observable_id}", response_model=ObservableDetail)
def get_observable(observable_id: UUID, session: DbSession) -> ObservableDetail:
    observable = session.get(Observable, observable_id)
    if observable is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Observable not found")
    summary = _observable_summaries(session, [observable])[0]
    report_rows = list(
        session.execute(
            select(ReportObservable, Report, Source, Evidence)
            .join(Report, Report.id == ReportObservable.report_id)
            .join(Source, Source.id == Report.source_id)
            .join(Evidence, Evidence.id == ReportObservable.evidence_id)
            .where(ReportObservable.observable_id == observable_id)
            .order_by(Report.published_at.desc().nullslast())
        )
    )
    event_rows = list(
        session.execute(
            select(EventObservable, ThreatEvent, Evidence)
            .join(ThreatEvent, ThreatEvent.id == EventObservable.event_id)
            .join(Evidence, Evidence.id == EventObservable.evidence_id)
            .where(EventObservable.observable_id == observable_id)
            .order_by(ThreatEvent.first_seen.desc().nullslast())
        )
    )
    enrichments = list(
        session.scalars(
            select(ObservableEnrichment)
            .where(ObservableEnrichment.observable_id == observable_id)
            .order_by(ObservableEnrichment.queried_at.desc())
        )
    )
    return ObservableDetail(
        **summary.model_dump(),
        reports=[
            ObservableReportAppearance(
                report_id=report.id,
                report_title=report.title,
                source_name=source.name,
                published_at=report.published_at,
                confidence=report_observable.confidence,
                evidence_id=evidence.id,
                evidence=evidence.quote,
            )
            for report_observable, report, source, evidence in report_rows
        ],
        events=[
            ObservableEventAppearance(
                event_id=event.id,
                event_title=event.title,
                first_seen=event.first_seen,
                confidence=event_observable.confidence,
                evidence_id=evidence.id,
                evidence=evidence.quote,
            )
            for event_observable, event, evidence in event_rows
        ],
        enrichments=[
            ObservableEnrichmentRead(
                id=enrichment.id,
                provider=enrichment.provider,
                status=enrichment.status,
                queried_at=enrichment.queried_at,
                expires_at=enrichment.expires_at,
                result=enrichment.result,
                error=enrichment.error,
            )
            for enrichment in enrichments
        ],
    )


@observables_router.post(
    "/{observable_id}/enrich",
    response_model=ObservableEnrichmentRead,
)
def enrich_observable(observable_id: UUID, session: DbSession) -> ObservableEnrichmentRead:
    observable = session.get(Observable, observable_id)
    if observable is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Observable not found")
    now = datetime.now(UTC)
    result: dict[str, object] = {
        "scope": observable.scope,
        "validation_status": observable.validation_status,
        "report_count": session.scalar(
            select(func.count()).where(ReportObservable.observable_id == observable_id)
        )
        or 0,
        "event_count": session.scalar(
            select(func.count()).where(EventObservable.observable_id == observable_id)
        )
        or 0,
        "first_seen": observable.first_seen.isoformat() if observable.first_seen else None,
        "last_seen": observable.last_seen.isoformat() if observable.last_seen else None,
        "external_provider_used": False,
    }
    values = {
        "observable_id": observable_id,
        "provider": "local-context",
        "status": "completed",
        "queried_at": now,
        "expires_at": now + timedelta(hours=24),
        "result": result,
        "error": None,
    }
    if session.get_bind().dialect.name == "postgresql":
        session.execute(
            postgresql_insert(ObservableEnrichment)
            .values(**values)
            .on_conflict_do_update(
                constraint="uq_observable_enrichments_observable_provider",
                set_={key: value for key, value in values.items() if key != "observable_id"},
            )
        )
    else:
        enrichment = session.scalar(
            select(ObservableEnrichment).where(
                ObservableEnrichment.observable_id == observable_id,
                ObservableEnrichment.provider == "local-context",
            )
        )
        if enrichment is None:
            enrichment = ObservableEnrichment(**values)
            session.add(enrichment)
        else:
            for key, value in values.items():
                setattr(enrichment, key, value)
    session.commit()
    enrichment = session.scalar(
        select(ObservableEnrichment).where(
            ObservableEnrichment.observable_id == observable_id,
            ObservableEnrichment.provider == "local-context",
        )
    )
    if enrichment is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Enrichment result was not persisted",
        )
    return ObservableEnrichmentRead.model_validate(enrichment, from_attributes=True)


@observables_router.post("/{observable_id}/promote", response_model=IndicatorRead)
def promote_observable(
    observable_id: UUID,
    payload: ObservablePromote,
    session: DbSession,
) -> IndicatorRead:
    if payload.valid_until <= payload.valid_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="valid_until must be after valid_from",
        )
    observable = session.scalar(
        select(Observable).where(Observable.id == observable_id).with_for_update()
    )
    if observable is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Observable not found")
    if session.scalar(select(Indicator).where(Indicator.observable_id == observable_id)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Observable already has an Indicator",
        )
    requested_evidence = set(payload.evidence_ids)
    allowed_evidence = set(
        session.scalars(
            select(ReportObservable.evidence_id).where(
                ReportObservable.observable_id == observable_id,
                ReportObservable.evidence_id.in_(requested_evidence),
            )
        )
    )
    if allowed_evidence != requested_evidence:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Every evidence_id must support this Observable",
        )
    now = datetime.now(UTC)
    indicator = Indicator(
        observable_id=observable_id,
        purpose=payload.purpose,
        pattern=_indicator_pattern(observable),
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
        confidence=payload.confidence,
        severity=payload.severity,
        reviewed_at=now,
        reviewed_by=payload.reviewed_by,
    )
    session.add(indicator)
    session.flush()
    session.add_all(
        IndicatorEvidence(indicator_id=indicator.id, evidence_id=evidence_id)
        for evidence_id in requested_evidence
    )
    session.commit()
    return _indicator_read(session, indicator, observable)


@indicators_router.get("", response_model=list[IndicatorRead])
def list_indicators(
    session: DbSession,
    q: str | None = Query(default=None, max_length=1000),
    observable_type: str | None = Query(default=None, max_length=32),
    revoked: bool | None = None,
    limit: int = Query(default=100, ge=1, le=200),
) -> list[IndicatorRead]:
    statement = select(Indicator, Observable).join(
        Observable, Observable.id == Indicator.observable_id
    )
    if q:
        statement = statement.where(
            func.lower(Observable.value_normalized).contains(q.strip().casefold())
        )
    if observable_type:
        statement = statement.where(Observable.type == observable_type)
    if revoked is not None:
        statement = statement.where(Indicator.revoked == revoked)
    rows = list(
        session.execute(
            statement.order_by(Indicator.valid_until.desc(), Indicator.created_at.desc()).limit(
                limit
            )
        )
    )
    evidence_by_indicator: dict[UUID, list[UUID]] = defaultdict(list)
    if rows:
        indicator_ids = [indicator.id for indicator, _ in rows]
        for indicator_id, evidence_id in session.execute(
            select(IndicatorEvidence.indicator_id, IndicatorEvidence.evidence_id).where(
                IndicatorEvidence.indicator_id.in_(indicator_ids)
            )
        ):
            evidence_by_indicator[indicator_id].append(evidence_id)
    return [
        IndicatorRead(
            **_indicator_summary(indicator).model_dump(),  # type: ignore[union-attr]
            observable_id=observable.id,
            observable_type=observable.type,
            value_normalized=observable.value_normalized,
            pattern=indicator.pattern,
            reviewed_at=indicator.reviewed_at,
            evidence_ids=evidence_by_indicator[indicator.id],
        )
        for indicator, observable in rows
    ]


@indicators_router.get("/count", response_model=int)
def count_indicators(
    session: DbSession,
    q: str | None = Query(default=None, max_length=1000),
    observable_type: str | None = Query(default=None, max_length=32),
    revoked: bool | None = None,
) -> int:
    statement = (
        select(func.count())
        .select_from(Indicator)
        .join(Observable, Observable.id == Indicator.observable_id)
    )
    if q:
        statement = statement.where(
            func.lower(Observable.value_normalized).contains(q.strip().casefold())
        )
    if observable_type:
        statement = statement.where(Observable.type == observable_type)
    if revoked is not None:
        statement = statement.where(Indicator.revoked == revoked)
    return int(session.scalar(statement) or 0)


@indicators_router.patch("/{indicator_id}", response_model=IndicatorRead)
def update_indicator(
    indicator_id: UUID,
    payload: IndicatorUpdate,
    session: DbSession,
) -> IndicatorRead:
    indicator = session.scalar(
        select(Indicator).where(Indicator.id == indicator_id).with_for_update()
    )
    if indicator is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Indicator not found")
    if indicator.version != payload.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Indicator changed; reload before updating",
        )
    if payload.valid_until is not None and payload.valid_until <= indicator.valid_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="valid_until must be after valid_from",
        )
    for field in ("purpose", "valid_until", "confidence", "severity", "revoked"):
        value = getattr(payload, field)
        if value is not None:
            setattr(indicator, field, value)
    indicator.reviewed_by = payload.corrected_by
    indicator.reviewed_at = datetime.now(UTC)
    indicator.version += 1
    session.commit()
    observable = session.get(Observable, indicator.observable_id)
    if observable is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Indicator Observable is missing",
        )
    return _indicator_read(session, indicator, observable)
